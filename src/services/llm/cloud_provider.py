"""
Cloud LLM Provider
==================

Handles all cloud API LLM calls (OpenAI, DeepSeek, Anthropic, etc.)
Provides both complete() and stream() methods.
"""

import os
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
from lightrag.llm.openai import openai_complete_if_cache

from .exceptions import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .utils import sanitize_url


async def complete(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    binding: str = "openai",
    **kwargs,
) -> str:
    """
    Complete a prompt using cloud API providers.

    Supports OpenAI-compatible APIs and Anthropic.

    Args:
        prompt: The user prompt
        system_prompt: System prompt for context
        model: Model name
        api_key: API key
        base_url: Base URL for the API
        binding: Provider binding type (openai, anthropic)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Returns:
        str: The LLM response
    """
    binding_lower = (binding or "openai").lower()

    if binding_lower in ["anthropic", "claude"]:
        return await _anthropic_complete(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    # Default to OpenAI-compatible endpoint
    return await _openai_complete(
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )


async def stream(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    binding: str = "openai",
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Stream a response from cloud API providers.

    Args:
        prompt: The user prompt (ignored if messages provided)
        system_prompt: System prompt for context
        model: Model name
        api_key: API key
        base_url: Base URL for the API
        binding: Provider binding type (openai, anthropic)
        messages: Pre-built messages array (optional, overrides prompt/system_prompt)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Yields:
        str: Response chunks
    """
    binding_lower = (binding or "openai").lower()

    if binding_lower in ["anthropic", "claude"]:
        async for chunk in _anthropic_stream(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            base_url=base_url,
            messages=messages,
            **kwargs,
        ):
            yield chunk
    else:
        async for chunk in _openai_stream(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            base_url=base_url,
            messages=messages,
            **kwargs,
        ):
            yield chunk


async def _openai_complete(
    model: str,
    prompt: str,
    system_prompt: str,
    api_key: Optional[str],
    base_url: Optional[str],
    **kwargs,
) -> str:
    """OpenAI-compatible completion."""
    # Sanitize URL
    if base_url:
        base_url = sanitize_url(base_url, model)

    try:
        # Try using lightrag's openai_complete_if_cache first (has caching)
        response = await openai_complete_if_cache(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
        if response:
            return response
    except Exception:
        pass  # Fall through to direct call

    # Fallback: Direct aiohttp call
    if base_url:
        url = base_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        timeout = aiohttp.ClientTimeout(total=120)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if "choices" in result and result["choices"]:
                            msg = result["choices"][0].get("message", {})
                            content = msg.get("content", "")
                            if not content:
                                content = (
                                    msg.get("reasoning_content")
                                    or msg.get("reasoning")
                                    or msg.get("thought")
                                    or ""
                                )
                            return content
                    else:
                        error_text = await resp.text()

                        # Map HTTP status codes to specific exceptions
                        if resp.status == 401:
                            raise LLMAuthenticationError(
                                f"OpenAI authentication failed: {error_text}"
                            )
                        elif resp.status == 429:
                            raise LLMRateLimitError(
                                f"OpenAI rate limit exceeded: {error_text}", provider="openai"
                            )
                        elif resp.status >= 500:
                            raise LLMAPIError(
                                f"OpenAI server error: {error_text}",
                                status_code=resp.status,
                                provider="openai",
                            )
                        else:
                            raise LLMAPIError(
                                f"OpenAI API error: {resp.status} - {error_text}",
                                status_code=resp.status,
                                provider="openai",
                            )
        except aiohttp.ClientError as e:
            # Catch network/timeout errors and wrap them
            raise LLMTimeoutError(f"Connection failed: {str(e)}")

    raise LLMAPIError("Cloud completion failed: no valid configuration")


async def _openai_stream(
    model: str,
    prompt: str,
    system_prompt: str,
    api_key: Optional[str],
    base_url: Optional[str],
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """OpenAI-compatible streaming."""
    import json

    # Sanitize URL
    if base_url:
        base_url = sanitize_url(base_url, model)

    url = (base_url or "https://api.openai.com/v1").rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Build messages
    if messages:
        msg_list = messages
    else:
        msg_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    data = {
        "model": model,
        "messages": msg_list,
        "temperature": kwargs.get("temperature", 0.7),
        "stream": True,
    }
    if kwargs.get("max_tokens"):
        data["max_tokens"] = kwargs["max_tokens"]

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status != 200:
                error_text = await resp.text()

                # Map HTTP status codes to specific exceptions
                if resp.status == 401:
                    raise LLMAuthenticationError(
                        f"OpenAI stream authentication failed: {error_text}"
                    )
                elif resp.status == 429:
                    raise LLMRateLimitError(
                        f"OpenAI stream rate limit exceeded: {error_text}", provider="openai"
                    )
                elif resp.status >= 500:
                    raise LLMAPIError(
                        f"OpenAI stream server error: {error_text}",
                        status_code=resp.status,
                        provider="openai",
                    )
                else:
                    raise LLMAPIError(
                        f"OpenAI stream error: {resp.status} - {error_text}",
                        status_code=resp.status,
                        provider="openai",
                    )

            async for line in resp.content:
                line_str = line.decode("utf-8").strip()
                if not line_str or not line_str.startswith("data:"):
                    continue

                data_str = line_str[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    chunk_data = json.loads(data_str)
                    if "choices" in chunk_data and chunk_data["choices"]:
                        delta = chunk_data["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue


async def _anthropic_complete(
    model: str,
    prompt: str,
    system_prompt: str,
    api_key: Optional[str],
    base_url: Optional[str],
    **kwargs,
) -> str:
    """Anthropic (Claude) API completion."""
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key is missing.")

    if not base_url:
        url = "https://api.anthropic.com/v1/messages"
    else:
        url = base_url.rstrip("/")
        if not url.endswith("/messages"):
            url += "/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    data = {
        "model": model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": kwargs.get("max_tokens", 4096),
        "temperature": kwargs.get("temperature", 0.7),
    }

    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()

                # Map HTTP status codes to specific exceptions
                if response.status == 401:
                    raise LLMAuthenticationError(f"Anthropic authentication failed: {error_text}")
                elif response.status == 429:
                    raise LLMRateLimitError(
                        f"Anthropic rate limit exceeded: {error_text}", provider="anthropic"
                    )
                elif response.status >= 500:
                    raise LLMAPIError(
                        f"Anthropic server error: {error_text}",
                        status_code=response.status,
                        provider="anthropic",
                    )
                else:
                    raise LLMAPIError(
                        f"Anthropic API error: {response.status} - {error_text}",
                        status_code=response.status,
                        provider="anthropic",
                    )

            result = await response.json()
            return result["content"][0]["text"]


async def _anthropic_stream(
    model: str,
    prompt: str,
    system_prompt: str,
    api_key: Optional[str],
    base_url: Optional[str],
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Anthropic (Claude) API streaming."""
    import json

    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key is missing.")

    if not base_url:
        url = "https://api.anthropic.com/v1/messages"
    else:
        url = base_url.rstrip("/")
        if not url.endswith("/messages"):
            url += "/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Build messages
    if messages:
        # Filter out system messages for Anthropic
        msg_list = [m for m in messages if m.get("role") != "system"]
        system_content = next(
            (m["content"] for m in messages if m.get("role") == "system"),
            system_prompt,
        )
    else:
        msg_list = [{"role": "user", "content": prompt}]
        system_content = system_prompt

    data = {
        "model": model,
        "system": system_content,
        "messages": msg_list,
        "max_tokens": kwargs.get("max_tokens", 4096),
        "temperature": kwargs.get("temperature", 0.7),
        "stream": True,
    }

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()

                # Map HTTP status codes to specific exceptions
                if response.status == 401:
                    raise LLMAuthenticationError(
                        f"Anthropic stream authentication failed: {error_text}"
                    )
                elif response.status == 429:
                    raise LLMRateLimitError(
                        f"Anthropic stream rate limit exceeded: {error_text}", provider="anthropic"
                    )
                elif response.status >= 500:
                    raise LLMAPIError(
                        f"Anthropic stream server error: {error_text}",
                        status_code=response.status,
                        provider="anthropic",
                    )
                else:
                    raise LLMAPIError(
                        f"Anthropic stream error: {response.status} - {error_text}",
                        status_code=response.status,
                        provider="anthropic",
                    )

            async for line in response.content:
                line_str = line.decode("utf-8").strip()
                if not line_str or not line_str.startswith("data:"):
                    continue

                data_str = line_str[5:].strip()
                if not data_str:
                    continue

                try:
                    chunk_data = json.loads(data_str)
                    event_type = chunk_data.get("type")
                    if event_type == "content_block_delta":
                        delta = chunk_data.get("delta", {})
                        text = delta.get("text")
                        if text:
                            yield text
                except json.JSONDecodeError:
                    continue


async def fetch_models(
    base_url: str,
    api_key: Optional[str] = None,
    binding: str = "openai",
) -> List[str]:
    """
    Fetch available models from cloud provider.

    Args:
        base_url: API endpoint URL
        api_key: API key
        binding: Provider type (openai, anthropic)

    Returns:
        List of available model names
    """
    binding = binding.lower()
    base_url = base_url.rstrip("/")

    headers = {}
    if api_key:
        if binding in ["anthropic", "claude"]:
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            url = f"{base_url}/models"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "data" in data and isinstance(data["data"], list):
                        return [
                            m.get("id") or m.get("name")
                            for m in data["data"]
                            if m.get("id") or m.get("name")
                        ]
                    elif isinstance(data, list):
                        return [
                            m.get("id") or m.get("name") if isinstance(m, dict) else str(m)
                            for m in data
                        ]
            return []
        except Exception as e:
            print(f"Error fetching models from {base_url}: {e}")
            return []


__all__ = [
    "complete",
    "stream",
    "fetch_models",
]
