"""
LLM Factory - Central Hub for LLM Calls
=======================================

This module serves as the central hub for all LLM calls in DeepTutor.
It provides a unified interface for agents to call LLMs, routing requests
to the appropriate provider (cloud or local) based on configuration.

Architecture:
    Agents (ChatAgent, GuideAgent, etc.)
              ↓
         BaseAgent.call_llm() / stream_llm()
              ↓
         LLM Factory (this module)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
CloudProvider      LocalProvider
(cloud_provider)   (local_provider)
              ↓                   ↓
OpenAI/DeepSeek/etc    LM Studio/Ollama/etc

Deployment Modes (LLM_MODE env var):
- api: Only use cloud API providers
- local: Only use local/self-hosted LLM servers
- hybrid: Use whatever is active (default)

Retry Mechanism:
- Automatic retry with exponential backoff for transient errors
- Configurable max_retries, retry_delay, and exponential_backoff
- Only retries on retriable errors (timeout, rate limit, server errors)
"""

import asyncio
from enum import Enum
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from . import cloud_provider, local_provider
from .config import get_llm_config
from .exceptions import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .provider import provider_manager
from .utils import is_local_llm_server

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_EXPONENTIAL_BACKOFF = True


def _is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.

    Retriable errors:
    - Timeout errors
    - Rate limit errors (429)
    - Server errors (5xx)

    Non-retriable errors:
    - Authentication errors (401)
    - Bad request (400)
    - Not found (404)

    Args:
        error: The exception to check

    Returns:
        True if the error is retriable
    """
    if isinstance(error, LLMTimeoutError):
        return True
    if isinstance(error, LLMRateLimitError):
        return True
    if isinstance(error, LLMAuthenticationError):
        return False  # Don't retry auth errors

    if isinstance(error, LLMAPIError):
        status_code = error.status_code
        if status_code:
            # Retry on server errors (5xx) and rate limits (429)
            if status_code >= 500 or status_code == 429:
                return True
            # Don't retry on client errors (4xx except 429)
            if 400 <= status_code < 500:
                return False
        return True  # Retry by default for unknown API errors

    # For other exceptions (network errors, etc.), retry
    return True


async def _execute_with_retry(
    func,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    exponential_backoff: bool = DEFAULT_EXPONENTIAL_BACKOFF,
    **kwargs,
):
    """
    Execute a function with retry logic.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        exponential_backoff: Whether to use exponential backoff
        **kwargs: Arguments to pass to the function

    Returns:
        Result from the function

    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    delay = retry_delay

    for attempt in range(max_retries + 1):
        try:
            return await func(**kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry
            if attempt >= max_retries or not _is_retriable_error(e):
                raise

            # Calculate delay for next attempt
            if exponential_backoff:
                current_delay = delay * (2**attempt)
            else:
                current_delay = delay

            # Special handling for rate limit errors with retry_after
            if isinstance(e, LLMRateLimitError) and e.retry_after:
                current_delay = max(current_delay, e.retry_after)

            # Wait before retrying
            await asyncio.sleep(current_delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception


class LLMMode(str, Enum):
    """LLM deployment mode."""

    API = "api"  # Cloud API only
    LOCAL = "local"  # Local/self-hosted only
    HYBRID = "hybrid"  # Both, use active provider


def get_llm_mode() -> LLMMode:
    """
    Get the current LLM deployment mode from environment.

    Returns:
        LLMMode: Current deployment mode (defaults to hybrid)
    """
    mode = os.getenv("LLM_MODE", "hybrid").lower()
    if mode == "api":
        return LLMMode.API
    elif mode == "local":
        return LLMMode.LOCAL
    return LLMMode.HYBRID


def _should_use_local(base_url: Optional[str]) -> bool:
    """
    Determine if we should use the local provider based on URL and mode.

    Args:
        base_url: The base URL to check

    Returns:
        True if local provider should be used
    """
    mode = get_llm_mode()

    if mode == LLMMode.API:
        return False
    elif mode == LLMMode.LOCAL:
        return True
    else:  # HYBRID
        return is_local_llm_server(base_url) if base_url else False


def get_mode_info() -> Dict[str, Any]:
    """
    Get information about the current LLM configuration mode.

    Returns:
        Dict containing:
        - mode: Current deployment mode
        - active_provider: Active provider info (if any)
        - env_configured: Whether env vars are properly configured
        - effective_source: Which config source is being used
    """
    mode = get_llm_mode()
    active_provider = provider_manager.get_active_provider()

    try:
        env_config = get_llm_config()
        env_configured = bool(env_config.model and (env_config.base_url or env_config.api_key))
    except ValueError:
        env_config = None
        env_configured = False

    # Determine effective source
    effective_source = "env"
    if active_provider:
        provider_is_local = active_provider.provider_type == "local"
        if mode == LLMMode.HYBRID:
            effective_source = "provider"
        elif mode == LLMMode.API and not provider_is_local:
            effective_source = "provider"
        elif mode == LLMMode.LOCAL and provider_is_local:
            effective_source = "provider"

    return {
        "mode": mode.value,
        "active_provider": (
            {
                "name": active_provider.name,
                "model": active_provider.model,
                "provider_type": active_provider.provider_type,
                "binding": active_provider.binding,
            }
            if active_provider
            else None
        ),
        "env_configured": env_configured,
        "effective_source": effective_source,
    }


async def complete(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    binding: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    exponential_backoff: bool = DEFAULT_EXPONENTIAL_BACKOFF,
    **kwargs,
) -> str:
    """
    Unified LLM completion function with automatic retry.

    Routes to cloud_provider or local_provider based on configuration.
    Includes automatic retry with exponential backoff for transient errors.

    Args:
        prompt: The user prompt
        system_prompt: System prompt for context
        model: Model name (optional, uses effective config if not provided)
        api_key: API key (optional)
        base_url: Base URL for the API (optional)
        api_version: API version for Azure OpenAI (optional)
        binding: Provider binding type (optional)
        messages: Pre-built messages array (optional)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        exponential_backoff: Whether to use exponential backoff (default: True)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Returns:
        str: The LLM response
    """
    # Get config if parameters not provided
    if not model or not base_url:
        config = get_llm_config()
        model = model or config.model
        api_key = api_key if api_key is not None else config.api_key
        base_url = base_url or config.base_url
        api_version = api_version or config.api_version
        binding = binding or config.binding or "openai"

    # Determine which provider to use
    use_local = _should_use_local(base_url)

    # Define the actual completion function
    async def _do_complete(**call_kwargs):
        if use_local:
            return await local_provider.complete(**call_kwargs)
        else:
            return await cloud_provider.complete(**call_kwargs)

    # Build call kwargs
    call_kwargs = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "messages": messages,
        **kwargs,
    }

    # Add cloud-specific kwargs if not local
    if not use_local:
        call_kwargs["api_version"] = api_version
        call_kwargs["binding"] = binding or "openai"

    # Execute with retry
    return await _execute_with_retry(
        _do_complete,
        max_retries=max_retries,
        retry_delay=retry_delay,
        exponential_backoff=exponential_backoff,
        **call_kwargs,
    )


async def stream(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    binding: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    exponential_backoff: bool = DEFAULT_EXPONENTIAL_BACKOFF,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Unified LLM streaming function with automatic retry.

    Routes to cloud_provider or local_provider based on configuration.
    Includes automatic retry with exponential backoff for connection errors.

    Note: Retry only applies to initial connection errors. Once streaming
    starts, errors during streaming will not be automatically retried.

    Args:
        prompt: The user prompt
        system_prompt: System prompt for context
        model: Model name (optional, uses effective config if not provided)
        api_key: API key (optional)
        base_url: Base URL for the API (optional)
        api_version: API version for Azure OpenAI (optional)
        binding: Provider binding type (optional)
        messages: Pre-built messages array (optional)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)
        exponential_backoff: Whether to use exponential backoff (default: True)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Yields:
        str: Response chunks
    """
    # Get config if parameters not provided
    if not model or not base_url:
        config = get_llm_config()
        model = model or config.model
        api_key = api_key if api_key is not None else config.api_key
        base_url = base_url or config.base_url
        api_version = api_version or config.api_version
        binding = binding or config.binding or "openai"

    # Determine which provider to use
    use_local = _should_use_local(base_url)

    # Build call kwargs
    call_kwargs = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "messages": messages,
        **kwargs,
    }

    # Add cloud-specific kwargs if not local
    if not use_local:
        call_kwargs["api_version"] = api_version
        call_kwargs["binding"] = binding or "openai"

    # Retry logic for streaming (retry on connection errors)
    last_exception = None
    delay = retry_delay

    for attempt in range(max_retries + 1):
        try:
            # Route to appropriate provider
            if use_local:
                async for chunk in local_provider.stream(**call_kwargs):
                    yield chunk
            else:
                async for chunk in cloud_provider.stream(**call_kwargs):
                    yield chunk
            # If we get here, streaming completed successfully
            return
        except Exception as e:
            last_exception = e

            # Check if we should retry
            if attempt >= max_retries or not _is_retriable_error(e):
                raise

            # Calculate delay for next attempt
            if exponential_backoff:
                current_delay = delay * (2**attempt)
            else:
                current_delay = delay

            # Special handling for rate limit errors with retry_after
            if isinstance(e, LLMRateLimitError) and e.retry_after:
                current_delay = max(current_delay, e.retry_after)

            # Wait before retrying
            await asyncio.sleep(current_delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception


async def fetch_models(
    binding: str,
    base_url: str,
    api_key: Optional[str] = None,
) -> List[str]:
    """
    Fetch available models from the provider.

    Routes to cloud_provider or local_provider based on URL.

    Args:
        binding: Provider type (openai, ollama, etc.)
        base_url: API endpoint URL
        api_key: API key (optional for local providers)

    Returns:
        List of available model names
    """
    if is_local_llm_server(base_url):
        return await local_provider.fetch_models(base_url, api_key)
    else:
        return await cloud_provider.fetch_models(base_url, api_key, binding)


# API Provider Presets
API_PROVIDER_PRESETS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "requires_key": True,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "requires_key": True,
        "binding": "anthropic",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "requires_key": True,
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "models": [],  # Dynamic
    },
}

# Local Provider Presets
LOCAL_PROVIDER_PRESETS = {
    "ollama": {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "requires_key": False,
        "default_key": "ollama",
    },
    "lm_studio": {
        "name": "LM Studio",
        "base_url": "http://localhost:1234/v1",
        "requires_key": False,
        "default_key": "lm-studio",
    },
    "vllm": {
        "name": "vLLM",
        "base_url": "http://localhost:8000/v1",
        "requires_key": False,
        "default_key": "vllm",
    },
    "llama_cpp": {
        "name": "llama.cpp",
        "base_url": "http://localhost:8080/v1",
        "requires_key": False,
        "default_key": "llama-cpp",
    },
}


def get_provider_presets() -> Dict[str, Any]:
    """
    Get all provider presets for frontend display.
    """
    return {
        "api": API_PROVIDER_PRESETS,
        "local": LOCAL_PROVIDER_PRESETS,
    }


__all__ = [
    "LLMMode",
    "get_llm_mode",
    "get_mode_info",
    "complete",
    "stream",
    "fetch_models",
    "get_provider_presets",
    "API_PROVIDER_PRESETS",
    "LOCAL_PROVIDER_PRESETS",
    # Retry configuration defaults
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_EXPONENTIAL_BACKOFF",
]
