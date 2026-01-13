"""
LLM URL Utilities
=================

Utility functions for handling LLM API URLs, especially for local servers.
"""


def sanitize_url(base_url: str, model: str = "") -> str:
    """
    Sanitize base URL for OpenAI-compatible APIs, with special handling for local LLM servers.

    Handles:
    - Ollama (port 11434)
    - LM Studio (port 1234)
    - Other localhost OpenAI-compatible servers

    Args:
        base_url: The base URL to sanitize
        model: Optional model name (unused, kept for API compatibility)

    Returns:
        Sanitized URL string
    """
    if not base_url:
        return base_url

    url = base_url.rstrip("/")

    # Ensure URL has a protocol (default to http for local servers)
    if url and not url.startswith(("http://", "https://")):
        url = "http://" + url

    # Standard OpenAI client library is strict about URLs:
    # - No trailing slashes
    # - No /chat/completions or /completions/messages/embeddings suffixes
    #   (it adds these automatically)
    for suffix in ["/chat/completions", "/completions", "/messages", "/embeddings"]:
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            url = url.rstrip("/")

    # Special handling for local LLM servers that require /v1:
    # - Ollama (port 11434)
    # - LM Studio (port 1234)
    is_local_ollama = ":11434" in url or (
        "ollama" in url.lower() and "ollama.com" not in url.lower()
    )
    is_lm_studio = ":1234" in url

    # For local LLM servers, ensure /v1 is present for OpenAI compatibility
    if (is_local_ollama or is_lm_studio) and not url.endswith("/v1"):
        url = url.rstrip("/") + "/v1"

    return url


def is_local_llm_server(base_url: str) -> bool:
    """
    Check if the given URL points to a local LLM server.

    Args:
        base_url: The base URL to check

    Returns:
        True if the URL appears to be a local LLM server
    """
    if not base_url:
        return False

    base_url_lower = base_url.lower()
    return any(
        indicator in base_url_lower
        for indicator in ["localhost", "127.0.0.1", "0.0.0.0", ":1234", ":11434"]
    )


__all__ = ["sanitize_url", "is_local_llm_server"]
