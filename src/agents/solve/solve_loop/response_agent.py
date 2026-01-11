#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResponseAgent - Step response generator
Based on materials in solve-chain, generates formal response for current step
"""

from pathlib import Path
import re
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent

from ..memory import CitationMemory, InvestigateMemory, SolveChainStep, SolveMemory


class ResponseAgent(BaseAgent):
    """Response generator Agent"""

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str,
        base_url: str,
        api_version: str | None = None,
        token_tracker=None,
    ):
        language = config.get("system", {}).get("language", "zh")
        super().__init__(
            module_name="solve",
            agent_name="response_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            config=config,
            token_tracker=token_tracker,
        )
        # Store citation configuration
        self.enable_citations = config.get("system", {}).get("enable_citations", True)

    async def process(
        self,
        question: str,
        step: SolveChainStep,
        solve_memory: SolveMemory,
        investigate_memory: InvestigateMemory,
        citation_memory: CitationMemory,
        output_dir: str | None = None,
        verbose: bool = True,
        accumulated_response: str = "",
    ) -> dict[str, Any]:
        if not step:
            return {"step_response": "(No pending step)"}

        context = self._build_context(
            question=question,
            step=step,
            solve_memory=solve_memory,
            investigate_memory=investigate_memory,
            citation_memory=citation_memory,
            output_dir=output_dir,
            accumulated_response=accumulated_response,
        )

        system_prompt = self._build_system_prompt(context["image_materials"])
        user_prompt = self._build_user_prompt(context)

        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, verbose=verbose
        )

        # Directly use LLM's raw output as step_response, no parsing
        step_response = response.strip() if response else ""
        used_citations = self._extract_used_citations(step_response, step)
        solve_memory.submit_step_response(
            step_id=step.step_id, response=step_response, used_citations=used_citations
        )
        solve_memory.save()

        return {
            "step_id": step.step_id,
            "step_response": step_response,
            "used_citations": used_citations,
            "raw_response": response,
        }

    # ------------------------------------------------------------------ #
    # Prompt Building
    # ------------------------------------------------------------------ #
    def _build_context(
        self,
        question: str,
        step: SolveChainStep,
        solve_memory: SolveMemory,
        investigate_memory: InvestigateMemory,
        citation_memory: CitationMemory,
        output_dir: str | None,
        accumulated_response: str = "",
    ) -> dict[str, Any]:
        available_cite_details = self._format_available_cite(step, investigate_memory)
        tool_materials, image_materials = self._format_tool_materials(step, output_dir)
        citation_details = self._format_citation_details(step, citation_memory)

        return {
            "question": question,
            "step_id": step.step_id,
            "step_target": step.step_target,
            "available_cite_details": available_cite_details,
            "tool_materials": tool_materials,
            "citation_details": citation_details,
            "image_materials": image_materials,
            "previous_context": accumulated_response
            or "(No previous content, this is the first step)",
        }

    def _build_system_prompt(self, image_materials: list[str]) -> str:
        base_prompt = self.get_prompt("system") if self.has_prompts() else None
        if not base_prompt:
            raise ValueError(
                "ResponseAgent missing system prompt, please configure in prompts/zh/solve_loop/response_agent.yaml."
            )

        # Add citation disable instruction if citations are disabled
        citation_instruction = ""
        if not self.enable_citations:
            citation_instruction_yaml = self.get_prompt("citation_instruction_disabled")
            if citation_instruction_yaml:
                citation_instruction = citation_instruction_yaml
            else:
                citation_instruction = "\n\n**Important: Citation Feature Disabled**\n"

        if image_materials:
            image_list = "\n".join([f"  - {img}" for img in image_materials])
            image_instruction_template = self.get_prompt("image_instruction")
            if image_instruction_template:
                image_instruction = image_instruction_template.format(image_list=image_list)
            else:
                image_instruction = f"\n\n**Image files to insert**:\n{image_list}\n"
            return base_prompt + citation_instruction + image_instruction

        return base_prompt + citation_instruction

    def _build_user_prompt(self, context: dict[str, Any]) -> str:
        template = self.get_prompt("user_template") if self.has_prompts() else None
        if not template:
            raise ValueError(
                "ResponseAgent missing user_template, please configure user_template in prompts/{lang}/solve_loop/response_agent.yaml"
            )

        # Format image_materials as clear text list
        image_materials = context.get("image_materials", [])
        if image_materials:
            image_text = "\n".join([f"- {img}" for img in image_materials])
        else:
            image_text = "(No image files)"

        # Create new context, format image_materials as text
        formatted_context = context.copy()
        formatted_context["image_materials"] = image_text

        return template.format(**formatted_context)

    # ------------------------------------------------------------------ #
    # Material Organization
    # ------------------------------------------------------------------ #
    def _format_available_cite(
        self, step: SolveChainStep, investigate_memory: InvestigateMemory
    ) -> str:
        if not step.available_cite:
            return "(No available knowledge chain)"
        lines: list[str] = []
        for cite in step.available_cite:
            knowledge = next(
                (k for k in investigate_memory.knowledge_chain if k.cite_id == cite), None
            )
            if not knowledge:
                continue
            summary = knowledge.summary or knowledge.raw_result[:300]
            lines.append(
                f"{cite} [{knowledge.tool_type}]\n"
                f"  Query: {knowledge.query}\n"
                f"  Summary: {summary}\n"
                f"  Raw: {knowledge.raw_result[:300]}..."
            )
        return "\n".join(lines) if lines else "(No matching knowledge)"

    def _format_tool_materials(
        self, step: SolveChainStep, output_dir: str | None
    ) -> tuple[str, list[str]]:
        if not step.tool_calls:
            return "(No tool calls yet)", []

        lines: list[str] = []
        images: list[str] = []
        seen_images: set[str] = set()

        def _append_image(path_str: str):
            normalized = str(path_str).replace("\\", "/")
            if normalized and normalized not in seen_images:
                images.append(normalized)
                seen_images.add(normalized)

        for call in step.tool_calls:
            summary = call.summary or "(Summary pending)"
            raw_preview = (call.raw_answer or "")[:500]
            lines.append(
                f"{call.tool_type} | cite_id={call.cite_id} | Status={call.status}\n"
                f"Query: {call.query}\n"
                f"Summary: {summary}\n"
                f"Raw excerpt: {raw_preview}"
            )
            # Priority: use recorded relative paths, then absolute paths, finally fall back to original artifacts list
            artifact_rel_paths = call.metadata.get("artifact_rel_paths") if call.metadata else None
            artifact_paths = call.metadata.get("artifact_paths") if call.metadata else None
            artifacts = call.metadata.get("artifacts") if call.metadata else None

            if artifact_rel_paths:
                for rel_path in artifact_rel_paths:
                    _append_image(rel_path)

            if artifact_paths:
                # Use absolute paths, but convert to relative paths relative to output_dir for display
                for abs_path in artifact_paths:
                    path = Path(abs_path)
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".bmp"}:
                        # If output_dir exists, calculate relative path; otherwise use absolute path
                        if output_dir:
                            try:
                                rel_path = path.relative_to(Path(output_dir))
                                _append_image(str(rel_path))
                            except ValueError:
                                # If cannot calculate relative path, use filename
                                _append_image(path.name)
                        else:
                            _append_image(path.name)
            elif artifacts:
                # Fall back to using artifacts list
                for artifact in artifacts:
                    path = Path(artifact)
                    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".bmp"}:
                        # Build relative path to artifacts directory
                        rel_path = Path("artifacts") / path.name
                        _append_image(str(rel_path))
        return "\n\n".join(lines), images

    def _format_citation_details(
        self, step: SolveChainStep, citation_memory: CitationMemory
    ) -> str:
        # If citations are disabled, return empty string
        if not self.enable_citations:
            return "(Citations disabled)"

        cite_ids = list(
            dict.fromkeys(
                step.available_cite + [tc.cite_id for tc in step.tool_calls if tc.cite_id]
            )
        )
        if not cite_ids:
            return "(No citations)"
        lines: list[str] = []
        for cite_id in cite_ids:
            citation = citation_memory.get_citation(cite_id)
            if not citation:
                continue
            summary = citation.content or citation.raw_result[:200]
            lines.append(f"- {cite_id} [{citation.tool_type}] Query: {citation.query}")
            if summary:
                lines.append(f"  Summary: {summary[:300]}")
        return "\n".join(lines) if lines else "(Citation information missing)"

    # ------------------------------------------------------------------ #
    # Citation Extraction
    # ------------------------------------------------------------------ #
    def _extract_used_citations(self, content: str, step: SolveChainStep) -> list[str]:
        # If citations are disabled, return empty list
        if not self.enable_citations:
            return []

        if not content:
            return []
        # Allow standard English brackets [cite], also tolerate some error formats (like Chinese full-width brackets【cite】), uniformly normalize to [cite]
        pattern = re.compile(r"\[([^\]\[]+)\](?!\()|【([^】\[]+)】")
        matches = pattern.findall(content)
        normalized: list[str] = []
        for match in matches:
            candidate = match[0] or match[1]
            if not candidate:
                continue
            normalized.append(f"[{candidate.strip()}]")
        allowed = set(step.available_cite + [tc.cite_id for tc in step.tool_calls if tc.cite_id])
        ordered: list[str] = []
        for cite in normalized:
            if cite in allowed and cite not in ordered:
                ordered.append(cite)
        return ordered
