"""
Idea Generation Workflow.
Uses unified PromptManager for prompt loading.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.agents.base_agent import BaseAgent
from src.services.prompt import get_prompt_manager


class IdeaGenerationWorkflow(BaseAgent):
    """Idea generation workflow"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
        progress_callback: Callable[[str, Any], None | Awaitable[None]] | None = None,
        output_dir: Path | None = None,
        language: str = "en",
    ):
        """
        Initialize workflow

        Args:
            api_key: API key
            base_url: API endpoint
            api_version: API version (for Azure OpenAI)
            model: Model name
            progress_callback: Progress callback function for streaming output
            output_dir: Output directory for saving intermediate results
            language: Language for prompts ("en" or "zh")
        """
        super().__init__(
            module_name="ideagen",
            agent_name="idea_generation",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            model=model,
            language=language,
        )
        self.progress_callback = progress_callback
        self.output_dir = output_dir
        self._prompts = get_prompt_manager().load_prompts(
            module_name="ideagen",
            agent_name="idea_generation",
            language=language,
        )

    async def _emit_progress(self, stage: str, data: Any):
        """Emit progress update"""
        if self.progress_callback:
            result = self.progress_callback(stage, data)
            if result is not None and asyncio.iscoroutine(result):
                await result

    async def loose_filter(self, knowledge_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Loose filtering - filter out unsuitable knowledge points

        Args:
            knowledge_points: Knowledge point list

        Returns:
            Filtered knowledge point list
        """
        await self._emit_progress(
            "loose_filter", {"status": "start", "total": len(knowledge_points)}
        )

        system_prompt = self._prompts.get("loose_filter_system", "")
        user_template = self._prompts.get("loose_filter_user_template", "")

        points_text = ""
        for i, point in enumerate(knowledge_points, 1):
            points_text += (
                f"\n{i}. {point['knowledge_point']}\n   Description: {point['description']}\n"
            )

        user_prompt = user_template.format(points_text=points_text)

        self.logger.info(f"Calling LLM to filter {len(knowledge_points)} knowledge points...")

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
        )

        self.logger.debug(f"LLM response length: {len(response)} chars")

        try:
            result = json.loads(response)
            filtered = result.get("filtered_points", [])

            self.logger.info(
                f"Parsed result: {len(filtered)} filtered points from {len(knowledge_points)} original"
            )

            # If filtered is empty but original list is not, filter is too strict, return original list
            if not filtered and knowledge_points:
                self.logger.warning("All points filtered out! Returning original list.")
                filtered = knowledge_points

            # Save filtered results
            if self.output_dir:
                with open(
                    self.output_dir / "02_filtered_knowledge_points.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(
                        {
                            "stage": "loose_filter",
                            "original_count": len(knowledge_points),
                            "filtered_count": len(filtered),
                            "filtered_points": filtered,
                            "timestamp": datetime.now().isoformat(),
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

            await self._emit_progress(
                "loose_filter", {"status": "complete", "filtered": len(filtered)}
            )
            return filtered
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            await self._emit_progress("loose_filter", {"status": "error"})
            return knowledge_points  # If parsing fails, return original list

    async def explore_ideas(self, knowledge_point: dict[str, Any]) -> list[str]:
        """
        3.2 Explore knowledge points - Generate at least 5 research ideas for each knowledge point

        Args:
            knowledge_point: Knowledge point dictionary

        Returns:
            List of research ideas (at least 5)
        """
        system_prompt = self._prompts.get("explore_ideas_system", "")
        user_template = self._prompts.get("explore_ideas_user_template", "")

        user_prompt = user_template.format(
            knowledge_point=knowledge_point["knowledge_point"],
            description=knowledge_point["description"],
        )

        self.logger.info(
            f"Generating ideas for: {knowledge_point.get('knowledge_point', 'unknown')}"
        )

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
        )

        self.logger.debug(f"LLM response length: {len(response)} chars")

        try:
            result = json.loads(response)
            ideas = result.get("research_ideas", [])
            self.logger.info(f"Generated {len(ideas)} research ideas")
            # Ensure at least 5
            if len(ideas) < 5:
                # If less than 5, can call again or supplement
                self.logger.warning(f"Only {len(ideas)} ideas generated (expected at least 5)")

            # Save generated research ideas
            if self.output_dir:
                safe_name = (
                    "".join(
                        c
                        for c in knowledge_point["knowledge_point"]
                        if c.isalnum() or c in (" ", "-", "_")
                    )
                    .strip()[:50]
                    .replace(" ", "_")
                )
                with open(
                    self.output_dir / f"03_ideas_{safe_name}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(
                        {
                            "stage": "explore_ideas",
                            "knowledge_point": knowledge_point,
                            "research_ideas": ideas,
                            "count": len(ideas),
                            "timestamp": datetime.now().isoformat(),
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

            return ideas[:10]  # Return at most 10
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            return []

    async def strict_filter(
        self, knowledge_point: dict[str, Any], research_ideas: list[str]
    ) -> list[str]:
        """
        3.3 Strict filtering - Evaluate research ideas with strict standards

        Args:
            knowledge_point: Knowledge point dictionary
            research_ideas: Research ideas list

        Returns:
            Retained research ideas list (at least keep 1, at least filter out 2)
        """
        if len(research_ideas) <= 1:
            return research_ideas  # If only 1 or less, return directly

        system_prompt = self._prompts.get("strict_filter_system", "")
        user_template = self._prompts.get("strict_filter_user_template", "")

        ideas_text = ""
        for i, idea in enumerate(research_ideas, 1):
            ideas_text += f"{i}. {idea}\n"

        user_prompt = user_template.format(
            knowledge_point=knowledge_point["knowledge_point"],
            description=knowledge_point["description"],
            ideas_text=ideas_text,
        )

        self.logger.info(
            f"Filtering {len(research_ideas)} ideas for: {knowledge_point.get('knowledge_point', 'unknown')}"
        )

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
        )

        self.logger.debug(f"LLM response length: {len(response)} chars")

        try:
            result = json.loads(response)
            kept = result.get("kept_ideas", [])
            rejected = result.get("rejected_ideas", [])
            reasons = result.get("reasons", {})
            self.logger.info(f"Kept {len(kept)}, rejected {len(rejected)}")

            # Validation: at least keep 1, at least filter out 2
            if len(kept) == 0:
                # If all filtered out, at least keep the first one
                kept = [research_ideas[0]]
                rejected = research_ideas[1:]
            elif len(rejected) < 2 and len(research_ideas) >= 3:
                # If less than 2 filtered out, force filter out the least suitable
                # Can add smarter logic here
                if len(kept) > 1:
                    rejected.extend(kept[1:])
                    kept = [kept[0]]

            # Save filtering results
            if self.output_dir:
                safe_name = (
                    "".join(
                        c
                        for c in knowledge_point["knowledge_point"]
                        if c.isalnum() or c in (" ", "-", "_")
                    )
                    .strip()[:50]
                    .replace(" ", "_")
                )
                with open(
                    self.output_dir / f"04_filtered_ideas_{safe_name}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(
                        {
                            "stage": "strict_filter",
                            "knowledge_point": knowledge_point,
                            "original_ideas": research_ideas,
                            "kept_ideas": kept,
                            "rejected_ideas": rejected,
                            "reasons": reasons,
                            "kept_count": len(kept),
                            "rejected_count": len(rejected),
                            "timestamp": datetime.now().isoformat(),
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

            return kept
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            # If parsing fails, at least keep the first one
            return research_ideas[:1] if research_ideas else []

    async def generate_statement(
        self, knowledge_point: dict[str, Any], research_ideas: list[str]
    ) -> str:
        """
        3.4 Generate statement - Generate markdown-formatted statement for knowledge points and research ideas

        Args:
            knowledge_point: Knowledge point dictionary
            research_ideas: Retained research ideas list

        Returns:
            Markdown-formatted statement
        """
        system_prompt = self._prompts.get("generate_statement_system", "")
        user_template = self._prompts.get("generate_statement_user_template", "")

        ideas_text = ""
        for i, idea in enumerate(research_ideas, 1):
            ideas_text += f"{i}. {idea}\n"

        user_prompt = user_template.format(
            knowledge_point=knowledge_point["knowledge_point"],
            description=knowledge_point["description"],
            ideas_text=ideas_text,
        )

        response = await self.call_llm(user_prompt=user_prompt, system_prompt=system_prompt)

        return response

    async def process(self, knowledge_points: list[dict[str, Any]]) -> str:
        """
        Execute complete workflow

        Args:
            knowledge_points: Knowledge points list

        Returns:
            Final markdown document
        """
        # 3.1 Loose filtering
        filtered_points = await self.loose_filter(knowledge_points)

        if not filtered_points:
            return "# Research Ideas Generation Result\n\nNo suitable knowledge points found."

        # 3.2 and 3.3 Process each knowledge point
        final_statements = []

        for idx, point in enumerate(filtered_points):
            await self._emit_progress(
                "explore", {"status": "processing", "index": idx + 1, "total": len(filtered_points)}
            )

            # 3.2 Explore knowledge points
            research_ideas = await self.explore_ideas(point)
            await self._emit_progress(
                "explore",
                {"status": "complete", "index": idx + 1, "ideas_count": len(research_ideas)},
            )

            if not research_ideas:
                continue

            # 3.3 Strict filtering
            kept_ideas = await self.strict_filter(point, research_ideas)
            await self._emit_progress(
                "filter", {"status": "complete", "index": idx + 1, "kept": len(kept_ideas)}
            )

            if not kept_ideas:
                continue

            # 3.4 Generate statement
            statement = await self.generate_statement(point, kept_ideas)
            final_statements.append(statement)

        # Join all statements
        final_markdown = "# Research Ideas Generation Result\n\n"
        final_markdown += "\n\n---\n\n".join(final_statements)

        # Save workflow summary
        if self.output_dir:
            workflow_summary = {
                "stage": "workflow_summary",
                "original_knowledge_points_count": len(knowledge_points),
                "filtered_knowledge_points_count": len(filtered_points),
                "processed_points": [
                    {
                        "knowledge_point": point["knowledge_point"],
                        "description": point["description"],
                        "statement": statement,
                    }
                    for point, statement in zip(
                        [
                            p
                            for p in filtered_points
                            if any(p["knowledge_point"] in s for s in final_statements)
                        ],
                        final_statements,
                    )
                ],
                "final_statements_count": len(final_statements),
                "timestamp": datetime.now().isoformat(),
            }
            with open(self.output_dir / "06_workflow_summary.json", "w", encoding="utf-8") as f:
                json.dump(workflow_summary, f, ensure_ascii=False, indent=2)

        return final_markdown
