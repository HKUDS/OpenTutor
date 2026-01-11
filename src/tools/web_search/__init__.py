"""
Web Search Tool - Pluggable search provider architecture

This module provides a unified interface for web search across multiple providers.

Usage:
    from src.tools.web_search import web_search

    # Simple usage (uses config/main.yaml or SEARCH_PROVIDER env var)
    result = web_search("What is AI?")

    # Specify provider
    result = web_search("What is AI?", provider="tavily")

    # With options
    result = web_search(
        query="What is AI?",
        provider="serper",
        output_dir="./cache",
        verbose=True,
        num=20,  # Provider-specific option
    )

Available Providers:
    - perplexity: AI-powered search (default)
    - baidu: Baidu AI Search
    - tavily: Research-focused with optional answers
    - exa: Neural/embeddings search with summaries
    - serper: Google SERP results
    - jina: SERP with full content extraction
"""

from datetime import datetime
import os
from typing import Any

from src.logging import get_logger
from src.services.config import PROJECT_ROOT, load_config_with_main

from ._legacy import SearchProvider
from .consolidation import AnswerConsolidator
from .providers import (
    get_available_providers,
    get_default_provider,
    get_provider,
    list_providers,
)
from .types import Citation, SearchResult, WebSearchResponse
from .utils import save_results

# Module logger
_logger = get_logger("WebSearch", level="INFO")


def _get_web_search_config() -> dict[str, Any]:
    """
    Load web search configuration from config/main.yaml using the standard config loader.

    Returns:
        dict with web_search config from tools.web_search section
    """
    try:
        config = load_config_with_main("main.yaml", PROJECT_ROOT)
        return config.get("tools", {}).get("web_search", {})
    except Exception as e:
        _logger.debug(f"Could not load config: {e}")
    return {}


def web_search(
    query: str,
    output_dir: str | None = None,
    verbose: bool = False,
    provider: str | None = None,
    # Consolidation options (only for SERP providers: serper, jina)
    consolidation: str | None = None,  # none, template, llm
    consolidation_custom_template: str | None = None,  # Custom Jinja2 template
    consolidation_llm_model: str | None = None,  # Model for LLM consolidation
    # Legacy Baidu-specific params (for backward compatibility)
    baidu_model: str = "ernie-4.5-turbo-32k",
    baidu_enable_deep_search: bool = False,
    baidu_search_recency_filter: str = "week",
    **provider_kwargs: Any,
) -> dict[str, Any]:
    """
    Perform web search using configured provider.

    Args:
        query: Search query.
        output_dir: Output directory for saving results (optional).
        verbose: Whether to print detailed information.
        provider: Provider name (perplexity, baidu, tavily, exa, serper, jina).
                  If not specified, uses SEARCH_PROVIDER env var (default: perplexity).
        consolidation: Answer consolidation type ("none", "template", "llm").
                       Only for SERP providers (serper, jina) that return raw results.
                       Template consolidation uses provider-specific templates.
                       AI providers (perplexity, baidu, tavily, exa) already include answers.
        consolidation_custom_template: Custom Jinja2 template string for unsupported providers.
        consolidation_llm_model: LLM model for llm consolidation (default: gpt-4o-mini).
        baidu_model: Model to use for Baidu AI Search (legacy param).
        baidu_enable_deep_search: Enable deep search for Baidu (legacy param).
        baidu_search_recency_filter: Recency filter for Baidu (legacy param).
        **provider_kwargs: Provider-specific options.

    Returns:
        dict: Search results with answer, citations, search_results, etc.

    Raises:
        ImportError: If required module is not installed.
        ValueError: If required environment variable is not set.
        Exception: If API call fails.

    Example:
        >>> result = web_search("What is machine learning?")
        >>> print(result["answer"])
        Machine learning is a subset of artificial intelligence...
        >>> print(result["citations"])
        [{"id": 1, "url": "https://...", "title": "...", ...}]
    """
    # Load config from main.yaml
    config = _get_web_search_config()

    # Check if web_search is enabled (default: True)
    if not config.get("enabled", True):
        _logger.warning("Web search is disabled in config")
        return {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": "Web search is disabled.",
            "citations": [],
            "search_results": [],
            "provider": "disabled",
        }

    # Determine provider: function arg > env var > config > default
    provider_name = (
        provider or os.environ.get("SEARCH_PROVIDER") or config.get("provider") or "perplexity"
    ).lower()

    # Determine consolidation from config if not provided
    if consolidation is None:
        consolidation = config.get("consolidation")

    # Determine custom template from config if not provided
    if consolidation_custom_template is None:
        consolidation_custom_template = config.get("consolidation_template") or None

    # Handle legacy Baidu params
    if provider_name == "baidu":
        provider_kwargs.setdefault("model", baidu_model)
        provider_kwargs.setdefault("enable_deep_search", baidu_enable_deep_search)
        provider_kwargs.setdefault("search_recency_filter", baidu_search_recency_filter)

    # Get provider instance
    search_provider = get_provider(provider_name)

    _logger.progress(f"[{search_provider.name}] Searching: {query[:50]}...")

    # Execute search
    try:
        response = search_provider.search(query, **provider_kwargs)
        _logger.success(f"[{search_provider.name}] Search completed")
    except Exception as e:
        _logger.error(f"[{search_provider.name}] Search failed: {e}")
        raise Exception(f"{search_provider.name} search failed: {e}")
    # Apply consolidation for SERP providers without LLM answers
    if consolidation and not search_provider.supports_answer:
        llm_config = {}
        if consolidation_llm_model:
            llm_config["model"] = consolidation_llm_model

        consolidator = AnswerConsolidator(
            consolidation_type=consolidation,
            custom_template=consolidation_custom_template,
            llm_config=llm_config if llm_config else None,
        )
        response = consolidator.consolidate(response)

    # Convert to dict (backward compatible format)
    result = response.to_dict()

    # Save if output_dir provided
    if output_dir:
        output_path = save_results(result, output_dir, provider_name)
        result["result_file"] = output_path
        _logger.debug(f"Search results saved to: {output_path}")

    if verbose:
        answer = result.get("answer", "")
        _logger.info(f"Query: {query}")
        if answer:
            _logger.info(f"Answer: {answer[:200]}..." if len(answer) > 200 else f"Answer: {answer}")
        _logger.info(f"Citations: {len(result.get('citations', []))}")

    return result


def get_current_config() -> dict[str, Any]:
    """
    Get the current web search configuration.

    Returns:
        dict with:
            - enabled: bool
            - provider: str (effective provider name)
            - consolidation: str | None
            - consolidation_template: str | None (custom Jinja2 template)
            - providers: list[dict] (full provider info for frontend)
            - consolidation_types: list[str]
            - template_providers: list[str] (providers that support template consolidation)
            - config_source: "env" | "yaml" | "default"
    """
    from .consolidation import CONSOLIDATION_TYPES, PROVIDER_TEMPLATES
    from .providers import get_providers_info

    config = _get_web_search_config()

    # Determine effective provider
    provider = (os.environ.get("SEARCH_PROVIDER") or config.get("provider") or "perplexity").lower()

    return {
        "enabled": config.get("enabled", True),
        "provider": provider,
        "consolidation": config.get("consolidation"),
        "consolidation_template": config.get("consolidation_template") or None,
        # For frontend display
        "providers": get_providers_info(),
        "consolidation_types": CONSOLIDATION_TYPES,
        # Only these providers support template consolidation
        "template_providers": list(PROVIDER_TEMPLATES.keys()),
        "config_source": "env"
        if os.environ.get("SEARCH_PROVIDER")
        else "yaml"
        if config.get("provider")
        else "default",
    }


# Export public API
__all__ = [
    "web_search",
    "get_current_config",
    "get_provider",
    "list_providers",
    "get_available_providers",
    "get_default_provider",
    "WebSearchResponse",
    "Citation",
    "SearchResult",
    "AnswerConsolidator",
    "SearchProvider",
]
