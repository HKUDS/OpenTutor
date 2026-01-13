"""
LLM Service
===========

Unified LLM service for all DeepTutor modules.

Architecture:
    Agents (ChatAgent, GuideAgent, etc.)
              ↓
         BaseAgent.call_llm() / stream_llm()
              ↓
         LLM Factory (complete / stream)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
CloudProvider      LocalProvider
(cloud_provider)   (local_provider)

Usage:
    # Simple completion
    from src.services.llm import complete, stream
    response = await complete("Hello!", system_prompt="You are helpful.")

    # Streaming
    async for chunk in stream("Hello!", system_prompt="You are helpful."):
        print(chunk, end="")

    # Configuration
    from src.services.llm import get_llm_config, LLMConfig
    config = get_llm_config()

    # Provider management
    from src.services.llm import provider_manager, LLMProvider
    providers = provider_manager.list_providers()

    # URL utilities for local LLM servers
    from src.services.llm import sanitize_url, is_local_llm_server

    # Mode information
    from src.services.llm import LLMMode, get_llm_mode, get_mode_info
"""

# Also expose the providers for direct access if needed
from . import cloud_provider, local_provider
from .client import LLMClient, get_llm_client, reset_llm_client
from .config import (
    LLMConfig,
    get_llm_config,
    get_token_limit_kwargs,
    uses_max_completion_tokens,
)
from .factory import (
    API_PROVIDER_PRESETS,
    LOCAL_PROVIDER_PRESETS,
    LLMMode,
    complete,
    fetch_models,
    get_effective_config,
    get_llm_mode,
    get_mode_info,
    get_provider_presets,
    stream,
)
from .provider import (
    LLMProvider,
    LLMProviderManager,
    ProviderType,
    provider_manager,
)
from .utils import is_local_llm_server, sanitize_url

__all__ = [
    # Client (legacy, prefer factory functions)
    "LLMClient",
    "get_llm_client",
    "reset_llm_client",
    # Config
    "LLMConfig",
    "get_llm_config",
    "uses_max_completion_tokens",
    "get_token_limit_kwargs",
    # Factory (main API)
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
    # Providers
    "cloud_provider",
    "local_provider",
    # Provider Management
    "ProviderType",
    "LLMProvider",
    "LLMProviderManager",
    "provider_manager",
    # Utils
    "sanitize_url",
    "is_local_llm_server",
]
