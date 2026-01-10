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
- hybrid: Use whatever is active (default)0
"""

from enum import Enum
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from . import cloud_provider, local_provider
from .config import LLMConfig, get_llm_config
from .exceptions import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .provider import provider_manager
from .utils import is_local_llm_server

# --- RETRY CONFIGURATION ---
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_EXPONENTIAL_BACKOFF = True


def _is_retriable_error(error: Exception) -> bool:
    """Determine if we should retry based on the exception type."""
    if isinstance(error, (LLMTimeoutError, LLMRateLimitError)):
        return True
    if isinstance(error, LLMAuthenticationError):
        return False  # Never retry auth errors
    if isinstance(error, LLMAPIError):
        # Retry server errors (5xx)
        if error.status_code and error.status_code >= 500:
            return True
        return False
    # Retry generic IO/Network errors
    return True


async def _execute_with_retry(func, max_retries=DEFAULT_MAX_RETRIES, **kwargs):
    """Executes a function with exponential backoff retry logic."""
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    delay = DEFAULT_RETRY_DELAY
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(**kwargs)
        except Exception as e:
            last_exception = e
            # Don't retry if it's not a retriable error or if it's the last attempt
            if attempt >= max_retries or not _is_retriable_error(e):
                raise

            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)

            if DEFAULT_EXPONENTIAL_BACKOFF:
                delay *= 2

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


def get_effective_config() -> LLMConfig:
    """
    Get the effective LLM configuration based on deployment mode.

    For hybrid mode: Use active provider if available, else env config
    For api mode: Use active API provider or env config
    For local mode: Use active local provider or env config

    Returns:
        LLMConfig: The effective configuration to use
    """
    mode = get_llm_mode()
    active_provider = provider_manager.get_active_provider()
    env_config = get_llm_config()

    # If we have an active provider, check if it matches the mode
    if active_provider:
        provider_is_local = active_provider.provider_type == "local"

        # Check mode compatibility
        if mode == LLMMode.API and provider_is_local:
            # In API mode but active provider is local - use env config
            return env_config
        elif mode == LLMMode.LOCAL and not provider_is_local:
            # In local mode but active provider is API - use env config
            return env_config
        else:
            # Mode matches or hybrid mode - use active provider
            return LLMConfig(
                model=active_provider.model,
                api_key=active_provider.api_key,
                base_url=active_provider.base_url,
                binding=active_provider.binding,
            )

    # No active provider - use env config
    return env_config


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
    env_config = get_llm_config()

    env_configured = bool(env_config.model and (env_config.base_url or env_config.api_key))

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
    binding: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> str:
    """
    Unified LLM completion function.

    Routes to cloud_provider or local_provider based on configuration.

    Args:
        prompt: The user prompt
        system_prompt: System prompt for context
        model: Model name (optional, uses effective config if not provided)
        api_key: API key (optional)
        base_url: Base URL for the API (optional)
        binding: Provider binding type (optional)
        messages: Pre-built messages array (optional)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Returns:
        str: The LLM response
    """
    # Get effective config if parameters not provided
    if not model or not base_url:
        config = get_effective_config()
        model = model or config.model
        api_key = api_key if api_key is not None else config.api_key
        base_url = base_url or config.base_url
        binding = binding or config.binding or "openai"

    # Define the work function
    async def _do_complete(**call_kwargs):
        if _should_use_local(base_url):
            return await local_provider.complete(**call_kwargs)
        else:
            return await cloud_provider.complete(**call_kwargs)

    # Execute with retry
    return await _execute_with_retry(
        _do_complete,
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        base_url=base_url,
        binding=binding or "openai",
        messages=messages,
        **kwargs,
    )


async def stream(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    binding: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Unified LLM streaming function.

    Routes to cloud_provider or local_provider based on configuration.

    Args:
        prompt: The user prompt
        system_prompt: System prompt for context
        model: Model name (optional, uses effective config if not provided)
        api_key: API key (optional)
        base_url: Base URL for the API (optional)
        binding: Provider binding type (optional)
        messages: Pre-built messages array (optional)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Yields:
        str: Response chunks
    """
    # Get effective config if parameters not provided
    if not model or not base_url:
        config = get_effective_config()
        model = model or config.model
        api_key = api_key if api_key is not None else config.api_key
        base_url = base_url or config.base_url
        binding = binding or config.binding or "openai"

    # Route to appropriate provider
    if _should_use_local(base_url):
        async for chunk in local_provider.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            base_url=base_url,
            messages=messages,
            **kwargs,
        ):
            yield chunk
    else:
        async for chunk in cloud_provider.stream(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            api_key=api_key,
            base_url=base_url,
            binding=binding or "openai",
            messages=messages,
            **kwargs,
        ):
            yield chunk


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
    "get_effective_config",
    "get_mode_info",
    "complete",
    "stream",
    "fetch_models",
    "get_provider_presets",
    "API_PROVIDER_PRESETS",
    "LOCAL_PROVIDER_PRESETS",
]
