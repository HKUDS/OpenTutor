"""
Legacy SearchProvider enum for backward compatibility.

This enum is kept for any existing code that imports it.
New code should use provider names as strings with the web_search() function.
"""

from enum import Enum


class SearchProvider(str, Enum):
    """
    Supported search providers.

    DEPRECATED: Use provider names directly as strings with web_search().
    Example: web_search(query="...", provider="perplexity")
    """

    PERPLEXITY = "perplexity"
    BAIDU = "baidu"
    TAVILY = "tavily"
    EXA = "exa"
    SERPER = "serper"
    JINA = "jina"
