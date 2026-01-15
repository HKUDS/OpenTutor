"""
SearXNG Metasearch Provider

SearXNG is a free, open-source metasearch engine that aggregates results
from multiple search engines while protecting user privacy.

Features:
- Privacy-focused: No API keys required for self-hosted instances
- Configurable: Choose specific engines and categories
- Free: No per-query costs
- Self-hosted: Full control over search sources

Configuration:
- SEARXNG_BASE_URL: Base URL of SearXNG instance (default: http://localhost:8888)

Note: JSON format must be enabled in SearXNG settings.yml:
    search:
      formats:
        - html
        - json
"""

from datetime import datetime
import os
from typing import Any

import requests

from ..base import BaseSearchProvider
from ..types import Citation, SearchResult, WebSearchResponse
from . import register_provider


class SearXNGAPIError(Exception):
    """SearXNG API error"""

    pass


@register_provider("searxng")
class SearXNGProvider(BaseSearchProvider):
    """SearXNG metasearch engine provider"""

    display_name = "SearXNG"
    description = "Privacy-focused metasearch engine"
    api_key_env_var = "SEARXNG_BASE_URL"
    requires_api_key = False
    supports_answer = False

    DEFAULT_BASE_URL = "http://192.168.1.90:8888"

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        """
        Initialize SearXNG provider.

        Args:
            api_key: Not used (SearXNG doesn't require API key).
            **kwargs: Additional configuration options.
        """
        super().__init__(api_key=api_key, **kwargs)
        self.base_url = (
            kwargs.get("base_url") or os.environ.get("SEARXNG_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")

    DEFAULT_ENGINES = "brave,bing,wikipedia,wikidata,wikinews"
    DEFAULT_CATEGORIES = "general"

    def search(
        self,
        query: str,
        categories: str | None = None,
        engines: str | None = None,
        language: str | None = None,
        time_range: str | None = None,
        page: int = 1,
        safesearch: int = 1,
        timeout: int = 30,
        **kwargs: Any,
    ) -> WebSearchResponse:
        """
        Perform search using SearXNG API.

        Args:
            query: Search query.
            categories: Comma-separated categories (e.g., 'general,science').
            engines: Comma-separated engines (e.g., 'google,duckduckgo').
            language: Language code (e.g., "en", "es"); omit or use "auto" for defaults.
            time_range: Time filter ('day', 'month', 'year').
            page: Page number (default 1).
            safesearch: Safe search level (0, 1, 2).
            timeout: Request timeout in seconds.
            **kwargs: Additional SearXNG parameters.

        Returns:
            WebSearchResponse: Standardized search response.
        """
        effective_engines = engines or os.environ.get("SEARXNG_ENGINES") or self.DEFAULT_ENGINES
        effective_categories = (
            categories or os.environ.get("SEARXNG_CATEGORIES") or self.DEFAULT_CATEGORIES
        )
        effective_language = None if not language or language == "auto" else language
        self.logger.info(
            f"[SearXNG] Request: base_url={self.base_url}, language={effective_language or 'auto'}, "
            f"categories={effective_categories}, engines={effective_engines}"
        )

        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": page,
            "safesearch": safesearch,
        }

        if effective_language:
            params["language"] = effective_language

        if effective_categories:
            params["categories"] = effective_categories

        if effective_engines:
            params["engines"] = effective_engines
        if time_range:
            params["time_range"] = time_range

        params.update(kwargs)

        search_endpoint = f"{self.base_url}/search"

        headers = {
            "Accept": "application/json",
            "User-Agent": "DeepTutor/1.0 (SearXNG API Client)",
        }
        if effective_language:
            headers["Accept-Language"] = effective_language

        self.logger.info(f"[SearXNG] Endpoint: {search_endpoint}")
        self.logger.info(f"[SearXNG] Query params: {params}")

        try:
            response = requests.get(
                search_endpoint,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            self.logger.info(f"[SearXNG] Request URL: {response.url}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"SearXNG request failed: {e}")
            raise SearXNGAPIError(f"SearXNG request failed: {e}") from e

        if response.status_code == 403:
            self.logger.error(
                "SearXNG returned 403 Forbidden. "
                "JSON format must be enabled in SearXNG settings.yml: "
                "search.formats: [html, json]"
            )
            raise SearXNGAPIError(
                "SearXNG API returned 403 Forbidden. "
                "Ensure JSON format is enabled in your SearXNG instance settings.yml: "
                "search:\n  formats:\n    - html\n    - json"
            )

        if response.status_code != 200:
            self.logger.error(f"SearXNG API error: {response.status_code} - {response.text}")
            raise SearXNGAPIError(f"SearXNG API error: {response.status_code} - {response.text}")

        data = response.json()

        self.logger.info(f"[SearXNG] Response status: {response.status_code}")
        self.logger.info(f"[SearXNG] Response keys: {list(data.keys())}")
        self.logger.info(f"[SearXNG] Results count: {len(data.get('results', []))}")
        self.logger.info(f"[SearXNG] Answers count: {len(data.get('answers', []))}")
        self.logger.info(f"[SearXNG] Suggestions: {data.get('suggestions', [])}")
        self.logger.info(f"[SearXNG] Corrections: {data.get('corrections', [])}")
        self.logger.info(f"[SearXNG] Infoboxes count: {len(data.get('infoboxes', []))}")

        unresponsive = data.get("unresponsive_engines", [])
        if unresponsive:
            self.logger.warning(f"[SearXNG] Unresponsive engines: {unresponsive}")

        if data.get("results"):
            engine_counts: dict[str, int] = {}
            for r in data["results"]:
                eng = r.get("engine", "unknown")
                engine_counts[eng] = engine_counts.get(eng, 0) + 1
            self.logger.info(f"[SearXNG] Results by engine: {engine_counts}")
            self.logger.info(f"[SearXNG] First result: {data['results'][0]}")
        elif unresponsive:
            engine_errors = ", ".join([f"{e[0]}({e[1]})" for e in unresponsive])
            self.logger.error(
                f"[SearXNG] No results - all engines failed: {engine_errors}. "
                "Configure working engines in SearXNG settings.yml (brave, bing, wikipedia, wikidata, arxiv)"
            )
        else:
            self.logger.warning(f"[SearXNG] No results returned. Full response: {data}")

        citations: list[Citation] = []
        search_results: list[SearchResult] = []

        for i, result in enumerate(data.get("results", []), 1):
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("content", "")
            date = result.get("publishedDate", "")
            engine = result.get("engine", "")
            category = result.get("category", "web")
            score = result.get("score", 0.0)

            attributes: dict[str, Any] = {}
            if result.get("img_src"):
                attributes["img_src"] = result["img_src"]
            if engine:
                attributes["engine"] = engine

            sr = SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                date=date,
                source=engine,
                score=score,
                attributes=attributes,
            )
            search_results.append(sr)

            citations.append(
                Citation(
                    id=i,
                    reference=f"[{i}]",
                    url=url,
                    title=title,
                    snippet=snippet,
                    date=date,
                    source=engine,
                    type=category,
                )
            )

        raw_answers = data.get("answers", [])
        self.logger.info(f"[SearXNG] Raw answers: {raw_answers}")

        answer_texts = []
        for ans in raw_answers:
            if isinstance(ans, str):
                answer_texts.append(ans)
            elif isinstance(ans, dict) and ans.get("content"):
                answer_texts.append(ans["content"])

        answer = "\n\n".join(answer_texts) if answer_texts else ""
        self.logger.info(f"[SearXNG] Parsed answer: {answer[:200] if answer else 'None'}")

        if not answer and search_results:
            answer = search_results[0].snippet

        metadata: dict[str, Any] = {
            "finish_reason": "stop",
            "base_url": self.base_url,
            "answers": answer_texts,
            "infoboxes": data.get("infoboxes", []),
            "suggestions": data.get("suggestions", []),
            "corrections": data.get("corrections", []),
        }

        self.logger.info(
            f"[SearXNG] Final results: {len(search_results)} search_results, {len(citations)} citations"
        )
        self.logger.info(f"[SearXNG] Final answer length: {len(answer)} chars")

        return WebSearchResponse(
            query=query,
            answer=answer,
            provider="searxng",
            timestamp=datetime.now().isoformat(),
            model="searxng",
            citations=citations,
            search_results=search_results,
            usage={},
            metadata=metadata,
        )

    def is_available(self) -> bool:
        """
        Check if SearXNG instance is reachable.

        Returns:
            bool: True if instance responds, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
