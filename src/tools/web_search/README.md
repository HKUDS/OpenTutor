# Web Search Tool

A unified, pluggable web search interface supporting multiple search providers with standardized responses.

## Quick Start

```python
from src.tools.web_search import web_search

# Basic search (uses default provider from config)
result = web_search("What is machine learning?")
print(result["answer"])
print(result["citations"])

# Specify a provider
result = web_search("Latest AI news", provider="tavily")

# With provider-specific options
result = web_search(
    query="Python best practices",
    provider="serper",
    output_dir="./search_cache",
    verbose=True,
    num=20,  # Serper-specific option
)
```

## Available Providers

| Provider | Type | API Key Env Var | Generates Answer | Description |
|----------|------|-----------------|------------------|-------------|
| **perplexity** | AI Search | `PERPLEXITY_API_KEY` | ✅ Yes | AI-powered search with LLM answers |
| **baidu** | AI Search | `BAIDU_API_KEY` | ✅ Yes | Baidu AI Search with ERNIE models |
| **tavily** | AI Search | `TAVILY_API_KEY` | ✅ Yes | Research-focused with relevance scoring |
| **exa** | AI Search | `EXA_API_KEY` | ✅ Yes | Neural/embeddings search with summaries |
| **serper** | SERP | `SERPER_API_KEY` | ⚡ Partial | Google SERP (extracts from Knowledge Graph) |
| **jina** | SERP | `JINA_API_KEY` | ❌ No | SERP with content extraction (free tier available) |

### Provider-Specific Options

#### Perplexity
```python
result = web_search(
    query="Explain quantum computing",
    provider="perplexity",
    model="sonar",
    system_prompt="Be concise and technical",
)
```

#### Tavily
```python
result = web_search(
    query="Latest developments in renewable energy",
    provider="tavily",
    search_depth="advanced",      # "basic" or "advanced"
    topic="news",                 # "general", "news", "finance"
    max_results=15,               # 1-20
    include_answer=True,
    include_raw_content=False,
    include_images=False,
    days=30,                      # Filter to last N days (1-365)
    include_domains=["arxiv.org"],
    exclude_domains=["example.com"],
)
```

#### Exa
```python
result = web_search(
    query="Machine learning optimization",
    provider="exa",
    search_type="neural",         # "auto", "neural", "keyword"
    num_results=10,
    include_text=True,
    include_highlights=True,
    include_summary=True,
    category="research paper",    # "news", "company", "github", etc.
    start_published_date="2024-01-01",
    end_published_date="2024-12-31",
)
```

#### Baidu
```python
result = web_search(
    query="人工智能最新进展",
    provider="baidu",
    model="ernie-4.5-turbo-32k",
    enable_deep_search=True,
    search_recency_filter="month",  # "week", "month", "semiyear", "year"
)
```

#### Serper
```python
result = web_search(
    query="Best Python frameworks 2024",
    provider="serper",
    mode="search",        # "search" or "scholar"
    num=20,               # max: 100
    gl="us",              # Country code
    hl="en",              # Language code
)

# Scholar mode for academic papers
result = web_search(
    query="transformer architecture attention mechanism",
    provider="serper",
    mode="scholar",       # Google Scholar results
    num=10,
    consolidation="template",  # Uses serper_scholar template automatically
)
# Scholar results include in attributes: publicationInfo, citedBy, pdfUrl, year, paperId
```

#### Jina
```python
result = web_search(
    query="Python async programming guide",
    provider="jina",
    enrich=True,      # Full content + images (default: True)
    timeout=60,       # Request timeout in seconds
)

# Basic mode (SERP only, no content extraction)
result = web_search(
    query="Python async programming guide",
    provider="jina",
    enrich=False,     # Basic SERP only, faster
)
```

## Configuration

### Environment Variables

```bash
# Provider selection (optional)
export SEARCH_PROVIDER=tavily

# API Keys
export PERPLEXITY_API_KEY=your_key
export TAVILY_API_KEY=your_key
export EXA_API_KEY=your_key
export BAIDU_API_KEY=your_key
export SERPER_API_KEY=your_key
export JINA_API_KEY=your_key
```

### YAML Configuration (`config/main.yaml`)

```yaml
tools:
  web_search:
    enabled: true
    provider: perplexity
    consolidation: template  # "none", "template", "llm"
```

### Priority Order

1. Function argument (`provider="tavily"`)
2. Environment variable (`SEARCH_PROVIDER`)
3. YAML config (`config/main.yaml`)
4. Default (`perplexity`)

## Response Format

All providers return a standardized dictionary:

```python
{
    "timestamp": "2024-01-15T10:30:00.000000",
    "query": "What is machine learning?",
    "provider": "tavily",
    "model": "tavily-basic",
    "answer": "Machine learning is a subset of AI...",
    "citations": [
        {
            "id": 1,
            "reference": "[1]",
            "url": "https://example.com/ml-guide",
            "title": "Machine Learning Guide",
            "snippet": "A comprehensive introduction...",
            "date": "2024-01-10",
            "source": "example.com",
            "content": "",
            "type": "web",
            "icon": "",
            "website": "",
            "web_anchor": ""
        }
    ],
    "search_results": [
        {
            "title": "Machine Learning Guide",
            "url": "https://example.com/ml-guide",
            "snippet": "A comprehensive introduction...",
            "date": "2024-01-10",
            "source": "example.com",
            "content": "",
            "score": 0.95
        }
    ],
    "usage": {},
    "response": {
        "content": "Machine learning is...",
        "role": "assistant",
        "finish_reason": "stop"
    }
    # Provider-specific metadata may be merged at top level
}
```

## Answer Consolidation

SERP providers (Serper, Jina) don't generate LLM answers. Use consolidation to generate answers from raw results:

### Template Consolidation

Uses provider-specific Jinja2 templates. **Available for: `serper`, `serper_scholar`, `jina`**.

When using Serper with `mode="scholar"`, the provider automatically returns `provider="serper_scholar"` which triggers the academic-focused template with publication info, authors, and citation counts.

```python
result = web_search(
    query="Python best practices",
    provider="serper",
    consolidation="template",
)

# Scholar mode with automatic template selection
result = web_search(
    query="deep learning optimization",
    provider="serper",
    mode="scholar",  # Automatically uses serper_scholar template
    consolidation="template",
)
```

### LLM Consolidation

Uses the project's LLM client to synthesize answers. Works with any provider.

```python
result = web_search(
    query="Python best practices",
    provider="serper",
    consolidation="llm",
)
```

### Custom Template

```python
result = web_search(
    query="Python best practices",
    provider="serper",
    consolidation="template",
    consolidation_custom_template="""
# Results for: {{ query }}

{% for result in results[:5] %}
## {{ result.title }}
{{ result.snippet }}
[Source]({{ result.url }})
{% endfor %}
""",
)
```

---

# Creating New Providers

This section documents how to add new search providers to the web_search module.

## Architecture Overview

```
src/tools/web_search/
├── __init__.py          # Main entry point, web_search() function
├── base.py              # BaseSearchProvider abstract class
├── types.py             # WebSearchResponse, Citation, SearchResult dataclasses
├── consolidation.py     # Answer consolidation (template/LLM)
├── utils.py             # Helper utilities
└── providers/
    ├── __init__.py      # Provider registry (@register_provider decorator)
    ├── perplexity.py
    ├── tavily.py
    ├── exa.py
    ├── baidu.py
    ├── serper.py
    └── jina.py
```

## Step 1: Create Provider File

Create `src/tools/web_search/providers/my_provider.py`:

```python
"""
MyProvider Search Provider

API Docs: https://api.myprovider.com/docs
"""
from datetime import datetime
from typing import Any

import requests

from ..base import BaseSearchProvider
from ..types import Citation, SearchResult, WebSearchResponse
from . import register_provider


@register_provider("myprovider")
class MyProvider(BaseSearchProvider):
    """My custom search provider"""

    # =========================================================================
    # REQUIRED CLASS ATTRIBUTES
    # =========================================================================

    # Human-readable name for UI display
    display_name = "MyProvider"

    # Short description for UI
    description = "My custom search engine"

    # Environment variable name for API key
    api_key_env_var = "MYPROVIDER_API_KEY"

    # Does this provider generate LLM answers?
    # - True: AI providers (Perplexity, Tavily, Exa, Baidu)
    # - False: SERP providers (Serper, Jina) - need consolidation for answers
    supports_answer = True

    # =========================================================================
    # OPTIONAL CLASS ATTRIBUTES
    # =========================================================================

    # Set to False if provider has a free tier (like Jina)
    # Default: True
    requires_api_key = True

    # Provider name (auto-set by @register_provider decorator)
    # Only override if you need a different internal name
    # name = "myprovider"

    # =========================================================================
    # PROVIDER IMPLEMENTATION
    # =========================================================================

    BASE_URL = "https://api.myprovider.com/search"

    def search(
        self,
        query: str,
        # Add your provider-specific parameters here
        max_results: int = 10,
        language: str = "en",
        timeout: int = 30,
        **kwargs: Any,
    ) -> WebSearchResponse:
        """
        Execute search and return standardized response.

        Args:
            query: Search query string.
            max_results: Maximum results to return.
            language: Language code.
            timeout: Request timeout in seconds.
            **kwargs: Additional options (passed from web_search()).

        Returns:
            WebSearchResponse: Standardized search response.
        """
        # Use self.logger for logging (auto-configured in base class)
        self.logger.debug(f"Calling MyProvider API max_results={max_results}")

        # Use self.api_key (auto-loaded from env var or constructor)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "limit": max_results,
            "lang": language,
        }

        response = requests.post(
            self.BASE_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            self.logger.error(f"MyProvider API error: {response.status_code}")
            raise Exception(
                f"MyProvider API error: {response.status_code} - {response.text}"
            )

        data = response.json()
        self.logger.debug(f"MyProvider returned {len(data.get('results', []))} results")

        # =====================================================================
        # CONVERT API RESPONSE TO STANDARDIZED FORMAT
        # =====================================================================

        citations: list[Citation] = []
        search_results: list[SearchResult] = []

        for i, item in enumerate(data.get("results", []), 1):
            # Build SearchResult
            sr = SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                date=item.get("published_date", ""),
                source=item.get("domain", ""),
                content=item.get("full_content", ""),  # Full text if available
                score=item.get("relevance_score", 0.0),
                # Optional: sitelinks and attributes
                sitelinks=[],  # list[dict] with "title" and "link" keys
                attributes={},  # dict with any extra data
            )
            search_results.append(sr)

            # Build Citation (parallel to SearchResult)
            citations.append(
                Citation(
                    id=i,
                    reference=f"[{i}]",
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    date=item.get("published_date", ""),
                    source=item.get("domain", ""),
                    content=item.get("full_content", ""),
                )
            )

        # Build the response
        return WebSearchResponse(
            query=query,
            answer=data.get("generated_answer", ""),  # Empty string for SERP providers
            provider="myprovider",
            timestamp=datetime.now().isoformat(),
            model=data.get("model_used", "myprovider-default"),
            citations=citations,
            search_results=search_results,
            usage={
                # Token usage if available
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
            metadata={
                "finish_reason": "stop",
                # Add any provider-specific metadata here
                # This data is available for template consolidation
            },
        )
```

## Step 2: Register the Provider

Add the import to `src/tools/web_search/providers/__init__.py`:

```python
# At the bottom of the file, add your provider to the imports:
from . import perplexity, baidu, tavily, exa, serper, jina, my_provider
```

That's it! The `@register_provider("myprovider")` decorator automatically registers your provider in the global registry.

## Step 3: (Optional) Add Consolidation Template

If your provider is a SERP provider (`supports_answer = False`), you can add a Jinja2 template for template consolidation.

Edit `src/tools/web_search/consolidation.py`:

```python
# 1. Add to PROVIDER_TEMPLATES dict (module-level):
PROVIDER_TEMPLATES = {
    # ... existing templates ...

    "myprovider": """### Search Results for "{{ query }}"

{% for result in results[:max_results] %}
**[{{ loop.index }}] {{ result.title }}**
{{ result.snippet }}
🔗 {{ result.url }}
{% if result.date %}📅 {{ result.date }}{% endif %}

{% endfor %}
---
*{{ results|length }} results from MyProvider*""",
}

# 2. Add to AnswerConsolidator.PROVIDER_TEMPLATE_MAP (class attribute):
class AnswerConsolidator:
    PROVIDER_TEMPLATE_MAP = {
        "serper": "serper",
        "jina": "jina",
        "serper_scholar": "serper_scholar",
        "myprovider": "myprovider",  # Add this line
    }
```

### Template Context Variables

These variables are available in all templates:

| Variable | Type | Description |
|----------|------|-------------|
| `query` | `str` | Original search query |
| `provider` | `str` | Provider name |
| `model` | `str` | Model used |
| `max_results` | `int` | Max results to display (default: 5) |
| `results` | `list[dict]` | Search results with `title`, `url`, `snippet`, `date`, `source`, `content`, `sitelinks`, `attributes` |
| `citations` | `list[dict]` | Citations with `id`, `reference`, `url`, `title`, `snippet` |
| `timestamp` | `str` | ISO timestamp |

Provider-specific metadata from `WebSearchResponse.metadata` is also available. For example, Serper templates have access to:
- `knowledge_graph`
- `answer_box`
- `people_also_ask`
- `related_searches`

## Step 4: Test Your Provider

```python
from src.tools.web_search import web_search, list_providers, get_available_providers

# Verify registration
print(list_providers())
# ['baidu', 'exa', 'jina', 'myprovider', 'perplexity', 'serper', 'tavily']

# Check if available (API key set)
print(get_available_providers())

# Test search
result = web_search("test query", provider="myprovider")
print(result["answer"])
print(result["citations"])

# Test with consolidation (for SERP providers)
result = web_search(
    "test query",
    provider="myprovider",
    consolidation="template",
)
```

## BaseSearchProvider Reference

```python
class BaseSearchProvider(ABC):
    """Abstract base class for search providers"""

    # Class attributes (override in subclass)
    name: str = "base"                    # Auto-set by @register_provider
    display_name: str = "Base Provider"   # Human-readable name
    description: str = ""                 # Short description
    requires_api_key: bool = True         # False for free-tier providers
    api_key_env_var: str = ""             # Env var name for API key
    supports_answer: bool = False         # True for AI providers

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        """
        Initialize the provider.

        Args:
            api_key: API key. If not provided, reads from api_key_env_var.
            **kwargs: Additional config stored in self.config.
        """
        self.logger = get_logger(f"WebSearch.{self.__class__.__name__}")
        self.api_key = api_key or self._get_api_key()
        self.config = kwargs

    @abstractmethod
    def search(self, query: str, **kwargs: Any) -> WebSearchResponse:
        """Execute search - MUST be implemented by subclass."""
        pass

    def is_available(self) -> bool:
        """Check if provider is available (API key set if required)."""
        if self.requires_api_key:
            return bool(self.api_key)
        return True
```

## Types Reference

### WebSearchResponse

```python
@dataclass
class WebSearchResponse:
    query: str                              # Original search query
    answer: str                             # LLM answer (empty for SERP)
    provider: str                           # Provider name
    timestamp: str                          # ISO timestamp
    model: str                              # Model used
    citations: list[Citation]               # Citation list
    search_results: list[SearchResult]      # Raw search results
    usage: dict[str, Any]                   # Token/cost usage
    metadata: dict[str, Any]                # Provider-specific data

    def to_dict(self) -> dict[str, Any]:
        """Convert to backward-compatible dict format."""
```

### Citation

```python
@dataclass
class Citation:
    id: int                     # Citation number (1, 2, 3...)
    reference: str              # Display reference ("[1]", "[2]"...)
    url: str                    # Source URL
    title: str = ""             # Page title
    snippet: str = ""           # Text snippet
    date: str = ""              # Publication date
    source: str = ""            # Source domain
    content: str = ""           # Full content if available
    # Additional fields for backward compatibility
    type: str = "web"           # Citation type (web, pdf, etc.)
    icon: str = ""              # Source icon URL
    website: str = ""           # Website name
    web_anchor: str = ""        # Web anchor text
```

### SearchResult

```python
@dataclass
class SearchResult:
    title: str                              # Result title
    url: str                                # Result URL
    snippet: str                            # Text snippet
    date: str = ""                          # Publication date
    source: str = ""                        # Source domain
    content: str = ""                       # Full content if available
    score: float = 0.0                      # Relevance score
    sitelinks: list[dict[str, str]] = []    # Related links
    attributes: dict[str, Any] = {}         # Additional attributes
```

## Helper Functions

```python
from src.tools.web_search import (
    web_search,              # Main search function
    get_current_config,      # Get active configuration
    list_providers,          # List all registered providers
    get_available_providers, # List providers with API keys set
    get_provider,            # Get a provider instance directly
    get_default_provider,    # Get default provider instance
    WebSearchResponse,       # Response dataclass
    Citation,                # Citation dataclass
    SearchResult,            # SearchResult dataclass
    AnswerConsolidator,      # Consolidation class
)

# From providers submodule (for advanced use)
from src.tools.web_search.providers import (
    get_providers_info,      # Get full provider info for frontend display
    register_provider,       # Decorator to register custom providers
)
```

## Example: Real Provider Implementation

Here's a simplified version of the Tavily provider as reference:

```python
@register_provider("tavily")
class TavilyProvider(BaseSearchProvider):
    """Tavily research-focused search provider"""

    display_name = "Tavily"
    description = "Research-focused search"
    api_key_env_var = "TAVILY_API_KEY"
    supports_answer = True  # Tavily generates LLM answers

    BASE_URL = "https://api.tavily.com/search"

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        topic: str = "general",
        max_results: int = 10,
        include_answer: bool = True,
        timeout: int = 60,
        **kwargs: Any,
    ) -> WebSearchResponse:
        self.logger.debug(f"Calling Tavily API depth={search_depth}")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
        }

        response = requests.post(self.BASE_URL, json=payload, timeout=timeout)

        if response.status_code != 200:
            raise Exception(f"Tavily API error: {response.status_code}")

        data = response.json()

        citations = []
        search_results = []

        for i, result in enumerate(data.get("results", []), 1):
            sr = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", ""),
                score=result.get("score", 0.0),
            )
            search_results.append(sr)
            citations.append(Citation(
                id=i,
                reference=f"[{i}]",
                url=result.get("url", ""),
                title=result.get("title", ""),
                snippet=result.get("content", ""),
            ))

        return WebSearchResponse(
            query=query,
            answer=data.get("answer", ""),
            provider="tavily",
            timestamp=datetime.now().isoformat(),
            model=f"tavily-{search_depth}",
            citations=citations,
            search_results=search_results,
            usage={},
            metadata={"search_depth": search_depth},
        )
```
