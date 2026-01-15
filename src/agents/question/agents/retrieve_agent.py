#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RetrieveAgent - Responsible for generating RAG queries and retrieving knowledge.

Uses unified BaseAgent for LLM calls and configuration management.
"""

import asyncio
import json
from typing import Any

from src.agents.base_agent import BaseAgent
from src.tools.rag_tool import rag_search


class RetrieveAgent(BaseAgent):
    """
    Agent responsible for knowledge retrieval from the knowledge base.

    Responsibilities:
    - Generate semantic search queries from requirements
    - Execute RAG searches in parallel
    - Merge and summarize retrieval results
    """

    def __init__(
        self,
        kb_name: str | None = None,
        rag_mode: str = "naive",
        language: str = "en",
        **kwargs,
    ):
        """
        Initialize RetrieveAgent.

        Args:
            kb_name: Knowledge base name to search
            rag_mode: RAG search mode ("naive" or "hybrid")
            language: Language for prompts ("en" or "zh")
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(
            module_name="question",
            agent_name="retrieve_agent",
            language=language,
            **kwargs,
        )
        self.kb_name = kb_name
        self.rag_mode = rag_mode

    async def process(
        self,
        requirement: dict[str, Any] | str,
        num_queries: int = 3,
    ) -> dict[str, Any]:
        """
        Main processing: generate queries and retrieve knowledge.

        Args:
            requirement: Question requirement (dict or string)
            num_queries: Number of RAG queries to generate

        Returns:
            Dict with:
                - queries: List of generated queries
                - retrievals: List of retrieval results
                - summary: Merged knowledge summary
        """
        self.logger.info("Starting knowledge retrieval")

        # Convert requirement to text
        if isinstance(requirement, dict):
            requirement_text = json.dumps(requirement, ensure_ascii=False, indent=2)
        else:
            requirement_text = str(requirement)

        # Step 1: Generate search queries
        queries = await self._generate_queries(requirement_text, num_queries)
        self.logger.info(f"Generated {len(queries)} search queries")

        # Step 2: Execute RAG searches in parallel
        retrievals = await self._execute_searches(queries)
        self.logger.info(f"Retrieved {len(retrievals)} results")

        # Step 3: Summarize results
        summary = self._summarize_retrievals(retrievals)

        return {
            "queries": queries,
            "retrievals": retrievals,
            "summary": summary,
            "has_content": any(r.get("answer", "").strip() for r in retrievals),
        }

    async def _generate_queries(
        self,
        requirement_text: str,
        num_queries: int,
    ) -> list[str]:
        """
        Use LLM to generate semantic search queries from requirement text.

        Args:
            requirement_text: Natural language requirement
            num_queries: Number of queries to generate

        Returns:
            List of query strings
        """
        system_prompt = self.get_prompt("system", "")
        user_prompt_template = self.get_prompt("generate_queries", "")

        if not user_prompt_template:
            # Fallback prompt
            user_prompt_template = (
                f"Extract {num_queries} knowledge point names from this requirement for retrieval:\n"
                "{requirement_text}\n\n"
                'Return JSON: {{"queries": ["point1", "point2", ...]}}'
            )

        user_prompt = user_prompt_template.format(
            requirement_text=requirement_text,
            num_queries=num_queries,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
                stage="generate_queries",
            )

            data = json.loads(response)
            queries_raw = data.get("queries", [])

            # Ensure queries is a list
            if not isinstance(queries_raw, list):
                if isinstance(queries_raw, dict):
                    queries_raw = list(queries_raw.values())
                elif isinstance(queries_raw, str):
                    queries_raw = [queries_raw]
                else:
                    queries_raw = []

            queries = [q.strip() for q in queries_raw if q and q.strip()]

        except Exception as e:
            self.logger.warning(f"Failed to generate queries: {e}")
            queries = []

        # Fallback: use requirement text as query
        if not queries:
            queries = [requirement_text[:100]]

        return queries[:num_queries]

    async def _single_rag_search(self, query: str) -> dict[str, Any]:
        """
        Execute a single RAG search.

        Args:
            query: Search query

        Returns:
            Dict with query and answer
        """
        try:
            result = await rag_search(
                query=query,
                kb_name=self.kb_name,
                mode=self.rag_mode,
                only_need_context=True,
            )
            return {
                "query": query,
                "answer": result.get("answer", ""),
                "mode": result.get("mode", self.rag_mode),
            }
        except Exception as e:
            self.logger.warning(f"RAG search failed for '{query}': {e}")
            return {
                "query": query,
                "answer": "",
                "error": str(e),
            }

    async def _execute_searches(self, queries: list[str]) -> list[dict[str, Any]]:
        """
        Execute RAG searches in parallel.

        Args:
            queries: List of search queries

        Returns:
            List of retrieval results
        """
        self.logger.debug(f"Executing {len(queries)} RAG searches in parallel")

        tasks = [self._single_rag_search(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        retrievals = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"Search failed for query '{queries[i]}': {result}")
                continue
            if result.get("answer"):
                retrievals.append(result)
                self.logger.debug(f"  → Query: {queries[i][:50]}... (retrieved)")

        return retrievals

    def _summarize_retrievals(self, retrievals: list[dict[str, Any]]) -> str:
        """
        Merge retrieval results into a summary string.

        Args:
            retrievals: List of retrieval results

        Returns:
            Merged summary string
        """
        if not retrievals:
            return "No retrieval context available."

        lines = []
        for item in retrievals:
            lines.append(f"=== Query: {item['query']} ===")
            answer = item.get("answer", "")
            if answer:
                # Truncate very long answers
                if len(answer) > 2000:
                    answer = answer[:2000] + "...[truncated]"
                lines.append(answer)
            lines.append("")

        return "\n".join(lines)
