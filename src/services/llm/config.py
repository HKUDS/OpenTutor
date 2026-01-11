# -*- coding: utf-8 -*-
"""
LLM Configuration
=================

Configuration management for LLM services.

Supports multiple deployment modes:
- api: Cloud API providers only (OpenAI, Anthropic, etc.)
- local: Local/self-hosted LLM servers only (Ollama, LM Studio, etc.)
- hybrid: Both API and local, uses active provider (default)
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Literal, Optional

from dotenv import load_dotenv

from .exceptions import LLMConfigError

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / "DeepTutor.env", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)

# LLM deployment modes
LLM_MODE_API = "api"
LLM_MODE_LOCAL = "local"
LLM_MODE_HYBRID = "hybrid"


@dataclass
class LLMConfig:
    """LLM configuration dataclass."""

    model: str
    api_key: str
    base_url: Optional[str] = None
    binding: str = "openai"
    api_version: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    provider_type: Literal["api", "local"] = "api"  # Track if this is API or local config


def _strip_value(value: Optional[str]) -> Optional[str]:
    """Remove leading/trailing whitespace and quotes from string."""
    if value is None:
        return None
    return value.strip().strip("\"'")


def _get_llm_mode_str() -> str:
    """
    Get the current LLM deployment mode from environment (internal use).

    For external use, import get_llm_mode from factory.py which returns LLMMode enum.

    Returns:
        str: 'api', 'local', or 'hybrid' (default)
    """
    return os.getenv("LLM_MODE", LLM_MODE_HYBRID).lower()


def get_llm_config() -> LLMConfig:
    """
    Load LLM configuration from environment variables or provider manager.

    The behavior depends on the LLM_MODE environment variable:
    - hybrid (default): Use active provider if available, else env config
    - api: Only use API providers (active API provider or env config)
    - local: Only use local providers (active local provider or env config)

    Priority:
    1. Active provider from llm_providers.json (if mode compatible)
    2. Environment variables (.env)

    Returns:
        LLMConfig: Configuration dataclass

    Raises:
        ValueError: If required configuration is missing
    """
    mode = _get_llm_mode_str()

    # 1. Try to get active provider from provider manager
    try:
        from .provider import provider_manager

        active_provider = provider_manager.get_active_provider()

        if active_provider:
            provider_is_local = getattr(active_provider, "provider_type", "local") == "local"

            # Check mode compatibility
            use_provider = False
            if mode == LLM_MODE_HYBRID:
                use_provider = True
            elif mode == LLM_MODE_API and not provider_is_local:
                use_provider = True
            elif mode == LLM_MODE_LOCAL and provider_is_local:
                use_provider = True

            if use_provider:
                return LLMConfig(
                    binding=active_provider.binding,
                    model=active_provider.model,
                    api_key=active_provider.api_key,
                    base_url=active_provider.base_url,
                    api_version=getattr(active_provider, "api_version", None),
                    provider_type=getattr(active_provider, "provider_type", "local"),
                )
    except Exception as e:
        print(f"⚠️ Failed to load active provider: {e}")

    # 2. Fallback to environment variables
    binding = _strip_value(os.getenv("LLM_BINDING", "openai"))
    model = _strip_value(os.getenv("LLM_MODEL"))
    api_key = _strip_value(os.getenv("LLM_API_KEY"))
    base_url = _strip_value(os.getenv("LLM_HOST"))
    api_version = _strip_value(os.getenv("LLM_API_VERSION"))

    # Validate required configuration
    if not model:
        raise LLMConfigError(
            "LLM_MODEL not set, please configure it in .env file or activate a provider"
        )

    # Determine provider type from base_url
    from .utils import is_local_llm_server

    provider_type: Literal["api", "local"] = "local" if is_local_llm_server(base_url) else "api"

    # Check if API key is required (not required for local providers)
    requires_key = (
        provider_type == "api" or os.getenv("LLM_API_KEY_REQUIRED", "false").lower() == "true"
    )

    if requires_key and not api_key:
        raise LLMConfigError(
            "LLM_API_KEY not set, please configure it in .env file or activate a provider"
        )
    if not base_url:
        raise LLMConfigError(
            "LLM_HOST not set, please configure it in .env file or activate a provider"
        )

    return LLMConfig(
        binding=binding,
        model=model,
        api_key=api_key or "",
        base_url=base_url,
        api_version=api_version,
        provider_type=provider_type,
    )


def uses_max_completion_tokens(model: str) -> bool:
    """
    Check if the model uses max_completion_tokens instead of max_tokens.

    Newer OpenAI models (o1, o3, gpt-4o, gpt-5.x, etc.) require max_completion_tokens
    while older models use max_tokens.

    Args:
        model: The model name

    Returns:
        True if the model requires max_completion_tokens, False otherwise
    """
    model_lower = model.lower()

    # Models that require max_completion_tokens:
    # - o1, o3 series (reasoning models)
    # - gpt-4o series
    # - gpt-5.x and later
    patterns = [
        r"^o[13]",  # o1, o3 models
        r"^gpt-4o",  # gpt-4o models
        r"^gpt-[5-9]",  # gpt-5.x and later
        r"^gpt-\d{2,}",  # gpt-10+ (future proofing)
    ]

    for pattern in patterns:
        if re.match(pattern, model_lower):
            return True

    return False


def get_token_limit_kwargs(model: str, max_tokens: int) -> dict:
    """
    Get the appropriate token limit parameter for the model.

    Newer OpenAI models (gpt-5.x, o1, o3, gpt-4o) require max_completion_tokens
    instead of max_tokens. This function automatically selects the correct parameter.

    Args:
        model: The model name
        max_tokens: The desired token limit

    Returns:
        Dictionary with either {"max_tokens": value} or {"max_completion_tokens": value}

    Example:
        >>> get_token_limit_kwargs("gpt-4", 4096)
        {"max_tokens": 4096}
        >>> get_token_limit_kwargs("gpt-5.2", 4096)
        {"max_completion_tokens": 4096}
    """
    if uses_max_completion_tokens(model):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


__all__ = [
    "LLMConfig",
    "get_llm_config",
    "uses_max_completion_tokens",
    "get_token_limit_kwargs",
    "LLM_MODE_API",
    "LLM_MODE_LOCAL",
    "LLM_MODE_HYBRID",
]
