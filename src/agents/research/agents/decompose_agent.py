#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DecomposeAgent - Topic decomposition Agent
Responsible for decomposing topics into multiple subtopics and generating overviews for each subtopic
"""

from pathlib import Path
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import json

from src.agents.base_agent import BaseAgent
from src.agents.research.data_structures import ToolTrace
from src.tools.rag_tool import rag_search

from ..utils.json_utils import extract_json_from_text


class DecomposeAgent(BaseAgent):
    """Topic decomposition Agent"""

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str = None,
        base_url: str = None,
        api_version: str = None,
        kb_name: str = "ai_textbook",
    ):
        language = config.get("system", {}).get("language", "zh")
        super().__init__(
            module_name="research",
            agent_name="decompose_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            config=config,
        )
        # Load KB and RAG mode from config, no hardcoding
        rag_cfg = config.get("rag", {})
        self.kb_name = rag_cfg.get("kb_name", kb_name or "ai_textbook")
        self.rag_mode = rag_cfg.get("default_mode", "hybrid")

        # Check if RAG is enabled (from researching config)
        researching_cfg = config.get("researching", {})
        self.enable_rag = researching_cfg.get("enable_rag_hybrid", True) or researching_cfg.get(
            "enable_rag_naive", True
        )

        # Citation manager (will be set during process)
        self.citation_manager = None

    def set_citation_manager(self, citation_manager):
        """Set citation manager"""
        self.citation_manager = citation_manager

    async def process(
        self, topic: str, num_subtopics: int = 5, mode: str = "manual"
    ) -> dict[str, Any]:
        """
        Decompose topic into subtopics and generate overview for each subtopic

        Args:
            topic: Main topic
            num_subtopics: Expected number of subtopics in manual mode, or maximum limit in auto mode
            mode: Mode, "manual" (manually specify count) or "auto" (auto-generate)

        Returns:
            Dictionary containing decomposition results
            {
                "main_topic": str,
                "sub_topics": [
                    {
                        "title": str,
                        "overview": str
                    },
                    ...
                ],
                "total_subtopics": int,
                "mode": str
            }
        """
        print(f"\n{'=' * 70}")
        print("🔀 DecomposeAgent - Topic Decomposition")
        print(f"{'=' * 70}")
        print(f"Main Topic: {topic}")
        print(f"Mode: {mode}")
        print(f"RAG Enabled: {self.enable_rag}")
        if mode == "auto":
            print(f"Max Subtopic Limit: {num_subtopics}\n")
        else:
            print(f"Expected Subtopic Count: {num_subtopics}\n")

        # If RAG is disabled, use direct LLM generation without RAG context
        if not self.enable_rag:
            print("⚠️ RAG is disabled, generating subtopics directly from LLM...")
            return await self._process_without_rag(topic, num_subtopics, mode)

        if mode == "auto":
            # Auto mode: autonomously generate subtopics
            return await self._process_auto_mode(topic, num_subtopics)
        # Manual mode: generate based on specified count
        return await self._process_manual_mode(topic, num_subtopics)

    async def _process_without_rag(
        self, topic: str, num_subtopics: int, mode: str = "manual"
    ) -> dict[str, Any]:
        """
        Process without RAG: directly generate subtopics from LLM based on topic.
        Used when RAG is disabled by user.

        Args:
            topic: Main topic
            num_subtopics: Number of subtopics to generate (exact for manual, max for auto)
            mode: "manual" or "auto"

        Returns:
            Dictionary containing decomposition results
        """
        print("\n🎯 Generating subtopics directly (no RAG)...")

        system_prompt = self.get_prompt(
            "system",
            "role",
            "You are a research planning expert. Your task is to decompose complex topics into clear subtopics.",
        )

        user_prompt_template = self.get_prompt("process", "decompose_without_rag")
        if not user_prompt_template:
            raise ValueError(
                "DecomposeAgent missing decompose_without_rag prompt, please configure process.decompose_without_rag in prompts/{lang}/decompose_agent.yaml"
            )

        # Build requirement based on mode
        if mode == "auto":
            decompose_requirement = f"""
Quantity Requirements:
Generate between 3 and {num_subtopics} subtopics based on the complexity of the topic.
- For simple topics, generate fewer subtopics (3-4)
- For complex topics, generate more subtopics (up to {num_subtopics})
- Prioritize the most important and distinctive aspects of the topic
"""
        else:
            decompose_requirement = f"""
Quantity Requirements:
Generate exactly {num_subtopics} subtopics. Please ensure exactly {num_subtopics} subtopics are generated, no more, no less.
"""

        user_prompt = user_prompt_template.format(
            topic=topic, decompose_requirement=decompose_requirement
        )

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            stage="decompose_no_rag",
        )

        # Parse JSON output
        from ..utils.json_utils import ensure_json_dict, ensure_keys, extract_json_from_text

        data = extract_json_from_text(response)
        try:
            obj = ensure_json_dict(data)
            ensure_keys(obj, ["sub_topics"])
            subs = obj.get("sub_topics", [])
            if not isinstance(subs, list):
                raise ValueError("sub_topics must be an array")
            # Clean and limit subtopics
            cleaned = []
            for it in subs[:num_subtopics]:
                if isinstance(it, dict):
                    cleaned.append(
                        {"title": it.get("title", ""), "overview": it.get("overview", "")}
                    )
            sub_topics = cleaned
        except Exception:
            sub_topics = []

        print(f"✓ Generated {len(sub_topics)} subtopics (without RAG)")

        return {
            "main_topic": topic,
            "sub_queries": [],  # No sub-queries when RAG is disabled
            "rag_context": "",  # No RAG context
            "sub_topics": sub_topics,
            "total_subtopics": len(sub_topics),
            "mode": f"{mode}_no_rag",
            "rag_context_summary": "RAG disabled - subtopics generated directly from LLM",
        }

    async def _process_manual_mode(self, topic: str, num_subtopics: int) -> dict[str, Any]:
        """Manual mode: generate subtopics based on specified count"""
        # Step 1: Generate sub-queries
        print("\n🔍 Step 1: Generating sub-queries...")
        sub_queries = await self._generate_sub_queries(topic, num_subtopics)
        print(f"✓ Generated {len(sub_queries)} sub-queries")

        # Step 2: Execute RAG retrieval to get background knowledge
        print("\n🔍 Step 2: Executing RAG retrieval...")
        rag_contexts = {}
        for i, query in enumerate(sub_queries, 1):
            try:
                result = await rag_search(query=query, kb_name=self.kb_name, mode=self.rag_mode)
                rag_answer = result.get("answer", "")
                rag_contexts[query] = rag_answer
                print(f"  ✓ Query {i}/{len(sub_queries)}: {query[:50]}...")

                # Record citation (if citation manager is enabled)
                if self.citation_manager:
                    # Get citation ID from CitationManager (unified ID generation)
                    citation_id = self.citation_manager.get_next_citation_id(stage="planning")
                    tool_type = f"rag_{self.rag_mode}" if self.rag_mode else "rag_hybrid"

                    # Create ToolTrace
                    import time

                    tool_id = f"plan_tool_{int(time.time() * 1000)}"
                    raw_answer_json = json.dumps(result, ensure_ascii=False)
                    trace = ToolTrace(
                        tool_id=tool_id,
                        citation_id=citation_id,
                        tool_type=tool_type,
                        query=query,
                        raw_answer=raw_answer_json,
                        summary=(
                            rag_answer[:500] if rag_answer else ""
                        ),  # Use first 500 characters as summary
                    )

                    # Add to citation manager
                    self.citation_manager.add_citation(
                        citation_id=citation_id,
                        tool_type=tool_type,
                        tool_trace=trace,
                        raw_answer=raw_answer_json,
                    )
            except Exception as e:
                print(f"  ✗ Query {i} failed: {e!s}")
                rag_contexts[query] = ""

        # Merge all RAG contexts
        combined_rag_context = "\n\n".join(
            [f"【{query}】\n{context}" for query, context in rag_contexts.items() if context]
        )

        # Step 3: Generate subtopics based on RAG background
        print("\n🎯 Step 3: Generating subtopics...")
        sub_topics = await self._generate_sub_topics(
            topic=topic, rag_context=combined_rag_context, num_subtopics=num_subtopics
        )

        print(f"✓ Generated {len(sub_topics)} subtopics")

        return {
            "main_topic": topic,
            "sub_queries": sub_queries,
            "rag_context": combined_rag_context,
            "sub_topics": sub_topics,
            "total_subtopics": len(sub_topics),
            "mode": "manual",
            "rag_context_summary": f"Used RAG background from {len(rag_contexts)} queries",
        }

    async def _process_auto_mode(self, topic: str, max_subtopics: int) -> dict[str, Any]:
        """Auto mode: autonomously generate subtopics based on topic and RAG context"""
        # Step 1: First perform a broad RAG retrieval to get topic-related background knowledge
        print("\n🔍 Step 1: Executing RAG retrieval to get background knowledge...")
        try:
            # Use topic itself as query to get related background
            result = await rag_search(query=topic, kb_name=self.kb_name, mode=self.rag_mode)
            rag_context = result.get("answer", "")
            print(f"  ✓ Retrieved background knowledge ({len(rag_context)} characters)")

            # Record citation (if citation manager is enabled)
            if self.citation_manager:
                # Get citation ID from CitationManager (unified ID generation)
                citation_id = self.citation_manager.get_next_citation_id(stage="planning")
                tool_type = f"rag_{self.rag_mode}" if self.rag_mode else "rag_hybrid"

                # Create ToolTrace
                import time

                tool_id = f"plan_tool_{int(time.time() * 1000)}"
                raw_answer_json = json.dumps(result, ensure_ascii=False)
                trace = ToolTrace(
                    tool_id=tool_id,
                    citation_id=citation_id,
                    tool_type=tool_type,
                    query=topic,
                    raw_answer=raw_answer_json,
                    summary=(
                        rag_context[:500] if rag_context else ""
                    ),  # Use first 500 characters as summary
                )

                # Add to citation manager
                self.citation_manager.add_citation(
                    citation_id=citation_id,
                    tool_type=tool_type,
                    tool_trace=trace,
                    raw_answer=raw_answer_json,
                )
        except Exception as e:
            print(f"  ✗ RAG retrieval failed: {e!s}")
            rag_context = ""

        # Step 2: Autonomously generate subtopics based on topic and RAG context
        print("\n🎯 Step 2: Autonomously generating subtopics...")
        sub_topics = await self._generate_sub_topics_auto(
            topic=topic, rag_context=rag_context, max_subtopics=max_subtopics
        )

        print(f"✓ Autonomously generated {len(sub_topics)} subtopics")

        return {
            "main_topic": topic,
            "sub_queries": [topic],  # In auto mode, use topic itself as query
            "rag_context": rag_context,
            "sub_topics": sub_topics,
            "total_subtopics": len(sub_topics),
            "mode": "auto",
            "rag_context_summary": "RAG background based on topic",
        }

    async def _generate_sub_topics_auto(
        self, topic: str, rag_context: str, max_subtopics: int
    ) -> list[dict[str, str]]:
        """
        Auto mode: Autonomously generate subtopics based on RAG background

        Args:
            topic: Main topic
            rag_context: RAG background knowledge
            max_subtopics: Maximum subtopic count limit

        Returns:
            Subtopics list
        """
        system_prompt = self.get_prompt("system", "role")
        if not system_prompt:
            raise ValueError(
                "DecomposeAgent missing system prompt, please configure system.role in prompts/{lang}/decompose_agent.yaml"
            )

        user_prompt_template = self.get_prompt("process", "decompose")
        if not user_prompt_template:
            raise ValueError(
                "DecomposeAgent missing decompose prompt, please configure process.decompose in prompts/{lang}/decompose_agent.yaml"
            )

        # Auto mode: Dynamically generate subtopics not exceeding the limit
        decompose_requirement = f"""
Quantity Requirements:
Dynamically generate no more than {max_subtopics} subtopics. Please carefully analyze the background knowledge, identify core content areas related to the topic, and independently generate subtopics around the topic-related book content.
- The number of subtopics should be reasonable, not exceeding {max_subtopics}
- Prioritize subtopics most relevant and important to the topic
- Ensure subtopics do not duplicate and cover different dimensions of the topic
"""

        user_prompt = user_prompt_template.format(
            topic=topic, rag_context=rag_context, decompose_requirement=decompose_requirement
        )

        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, stage="decompose"
        )

        # Parse JSON output (strict validation)
        from ..utils.json_utils import ensure_json_dict, ensure_keys, extract_json_from_text

        data = extract_json_from_text(response)
        try:
            obj = ensure_json_dict(data)
            ensure_keys(obj, ["sub_topics"])
            subs = obj.get("sub_topics", [])
            if not isinstance(subs, list):
                raise ValueError("sub_topics must be an array")
            # Limit count not exceeding max_subtopics
            cleaned = []
            for it in subs[:max_subtopics]:
                if isinstance(it, dict):
                    cleaned.append(
                        {"title": it.get("title", ""), "overview": it.get("overview", "")}
                    )
            return cleaned
        except Exception:
            # Fallback: return empty list
            return []

    async def _generate_sub_queries(self, topic: str, num_queries: int) -> list[str]:
        """
        Generate sub-queries

        Args:
            topic: Main topic
            num_queries: Expected number of queries

        Returns:
            Query list
        """
        system_prompt = self.get_prompt("system", "role")
        if not system_prompt:
            raise ValueError(
                "DecomposeAgent missing system prompt, please configure system.role in prompts/{lang}/decompose_agent.yaml"
            )

        user_prompt_template = self.get_prompt("process", "generate_queries")
        if not user_prompt_template:
            raise ValueError(
                "DecomposeAgent missing generate_queries prompt, please configure process.generate_queries in prompts/{lang}/decompose_agent.yaml"
            )

        user_prompt = user_prompt_template.format(topic=topic, num_queries=num_queries)

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            stage="generate_queries",
        )

        from ..utils.json_utils import ensure_json_dict, ensure_keys

        data = extract_json_from_text(response)
        try:
            obj = ensure_json_dict(data)
            ensure_keys(obj, ["queries"])
            queries = obj.get("queries", [])
            if not isinstance(queries, list):
                raise ValueError("queries must be an array")
            return queries[:num_queries]
        except Exception:
            # Fallback: extract queries from text
            lines = response.split("\n")
            queries = [line.strip() for line in lines if line.strip() and len(line.strip()) > 3]
            return queries[:num_queries]

    async def _generate_sub_topics(
        self, topic: str, rag_context: str, num_subtopics: int
    ) -> list[dict[str, str]]:
        """
        Generate subtopics based on RAG background

        Args:
            topic: Main topic
            rag_context: RAG background knowledge
            num_subtopics: Expected number of subtopics

        Returns:
            Subtopics list
        """
        system_prompt = self.get_prompt("system", "role")
        if not system_prompt:
            raise ValueError(
                "DecomposeAgent missing system prompt, please configure system.role in prompts/{lang}/decompose_agent.yaml"
            )

        user_prompt_template = self.get_prompt("process", "decompose")
        if not user_prompt_template:
            raise ValueError(
                "DecomposeAgent missing decompose prompt, please configure process.decompose in prompts/{lang}/decompose_agent.yaml"
            )

        # Manual mode: Explicitly generate specified number of subtopics
        decompose_requirement = f"""
Quantity Requirements:
Explicitly generate {num_subtopics} subtopics. Please ensure exactly {num_subtopics} subtopics are generated, no more, no less.
"""

        user_prompt = user_prompt_template.format(
            topic=topic, rag_context=rag_context, decompose_requirement=decompose_requirement
        )

        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, stage="decompose"
        )

        # Parse JSON output (strict validation)
        from ..utils.json_utils import ensure_json_dict, ensure_keys, extract_json_from_text

        data = extract_json_from_text(response)
        try:
            obj = ensure_json_dict(data)
            ensure_keys(obj, ["sub_topics"])
            subs = obj.get("sub_topics", [])
            if not isinstance(subs, list):
                raise ValueError("sub_topics must be an array")
            # Only select required fields
            cleaned = []
            for it in subs[:num_subtopics]:
                if isinstance(it, dict):
                    cleaned.append(
                        {"title": it.get("title", ""), "overview": it.get("overview", "")}
                    )
            return cleaned
        except Exception:
            # Fallback: return empty list
            return []


__all__ = ["DecomposeAgent"]
