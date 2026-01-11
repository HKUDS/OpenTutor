#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ManagerAgent - Manager (Refactored: directly plans step-level solution steps)
Based on user question and knowledge chain, plans solution steps
"""

from pathlib import Path
import sys
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent

from ..memory import InvestigateMemory, SolveChainStep, SolveMemory
from ..utils.json_utils import extract_json_from_text


class ManagerAgent(BaseAgent):
    """Manager Agent - Plans solution steps"""

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
            agent_name="manager_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            config=config,
            token_tracker=token_tracker,
        )

    async def process(
        self,
        question: str,
        investigate_memory: InvestigateMemory,
        solve_memory: SolveMemory,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """
        Process management workflow - plan solution steps

        Args:
            question: User question
            investigate_memory: Investigation memory (contains knowledge chain)
            solve_memory: Solve memory
            verbose: Whether to print detailed information

        Returns:
            dict: Management result
        """
        stage_label = "Plan"
        self.logger.log_stage_progress(
            stage_label, "start", f"question={question[:60]}{'...' if len(question) > 60 else ''}"
        )

        # 1. Check if steps already exist
        if solve_memory.solve_chains:
            steps_count = len(solve_memory.solve_chains)
            self.logger.log_stage_progress(stage_label, "skip", f"Already has {steps_count} steps")
            return {
                "has_steps": True,
                "steps_count": steps_count,
                "num_steps": steps_count,  # Maintain compatibility
                "message": "Steps already exist, skipping planning",
            }

        # 2. Build context
        context = self._build_context(question=question, investigate_memory=investigate_memory)

        # 3. Build Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)

        # 4. Call LLM (requires JSON format output)
        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            verbose=verbose,
            stage=stage_label,
            response_format={"type": "json_object"},  # Force JSON
        )

        # 5. Parse output and create StepItem
        steps = self._parse_response(response, investigate_memory)

        # 6. Add steps to solve_memory
        solve_memory.create_chains(steps)
        solve_memory.save()

        steps_count = len(steps)
        self.logger.log_stage_progress(stage_label, "complete", f"Generated {steps_count} steps")
        return {
            "has_steps": True,
            "steps_count": steps_count,
            "num_steps": steps_count,  # Maintain compatibility
            "message": f"Generated {steps_count} steps",
        }

    def _build_context(
        self, question: str, investigate_memory: InvestigateMemory
    ) -> dict[str, Any]:
        """Build context"""
        # Get knowledge chain information (cite_id + summary)
        knowledge_info = []
        for knowledge in investigate_memory.knowledge_chain:
            if knowledge.summary:  # Only use knowledge with summary
                knowledge_info.append(
                    {
                        "cite_id": knowledge.cite_id,
                        "tool_type": knowledge.tool_type,
                        "query": knowledge.query,
                        "summary": knowledge.summary,
                    }
                )

        knowledge_text = ""
        for info in knowledge_info:
            knowledge_text += f"\n{info['cite_id']} [{info['tool_type']}]\n"
            knowledge_text += f"  Query: {info['query']}\n"
            knowledge_text += f"  Summary: {info['summary']}\n"

        remaining_questions = []
        if investigate_memory and getattr(investigate_memory, "reflections", None):
            remaining_questions = investigate_memory.reflections.remaining_questions or []

        reflections_summary = (
            "\n".join(f"- {q}" for q in remaining_questions)
            if remaining_questions
            else "(No remaining questions)"
        )

        knowledge_summary_text = knowledge_text if knowledge_text else "(No research information)"

        return {
            "question": question,
            "knowledge_info": knowledge_info,
            "knowledge_text": knowledge_summary_text,
            "knowledge_chain_summary": knowledge_summary_text,
            "reflections_summary": reflections_summary,
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        prompt = self.get_prompt("system") if self.has_prompts() else None
        if not prompt:
            raise ValueError(
                "ManagerAgent missing system prompt, please configure system section in prompts/zh/solve_loop/manager_agent.yaml."
            )
        return prompt

    def _build_user_prompt(self, context: dict[str, Any]) -> str:
        """Build user prompt"""
        template = self.get_prompt("user_template") if self.has_prompts() else None
        if not template:
            raise ValueError(
                "ManagerAgent missing user prompt template, please configure user_template in prompts/zh/solve_loop/manager_agent.yaml."
            )
        return template.format(**context)

    def _parse_response(
        self, response: str, investigate_memory: InvestigateMemory
    ) -> list[SolveChainStep]:
        """Parse LLM output (JSON format), create solve-chain steps"""
        steps: list[SolveChainStep] = []
        knowledge_ids = {k.cite_id for k in investigate_memory.knowledge_chain}

        # Use json_utils to extract JSON
        parsed_data = extract_json_from_text(response)

        if not parsed_data or not isinstance(parsed_data, dict):
            raise ValueError(
                f"Failed to parse valid JSON object from LLM output. Original output: {response[:200]}..."
            )

        steps_data = parsed_data.get("steps", [])
        if not isinstance(steps_data, list):
            raise ValueError(f"'steps' field in JSON is not an array. Parsed result: {parsed_data}")

        if not steps_data:
            raise ValueError("'steps' array in JSON is empty, please check LLM output.")

        # Parse each step
        for idx, step_data in enumerate(steps_data, 1):
            if not isinstance(step_data, dict):
                self.logger.warning(
                    f"[ManagerAgent] Skipping invalid step data (index {idx}): {step_data}"
                )
                continue

            # Get step_id
            step_id = step_data.get("step_id", "").strip()
            if not step_id:
                step_id = f"S{idx}"
            elif not step_id.upper().startswith("S"):
                step_id = f"S{step_id}"

            # Get role and target
            role = step_data.get("role", "").strip()
            target = step_data.get("target", "").strip()

            # If target already contains role, use directly; otherwise combine
            if target:
                if "：" in target or ":" in target:
                    step_target = target
                elif role:
                    step_target = f"{role}：{target}"
                else:
                    step_target = target
            else:
                raise ValueError(f"Step {step_id} missing 'target' field")

            # Get cite_ids
            cite_ids_raw = step_data.get("cite_ids", [])
            if not isinstance(cite_ids_raw, list):
                # Compatible with string format
                if isinstance(cite_ids_raw, str):
                    cite_ids_raw = [cite_ids_raw] if cite_ids_raw and cite_ids_raw != "none" else []
                else:
                    cite_ids_raw = []

            # Clean and normalize cite_ids
            filtered_cites = []
            for cite in cite_ids_raw:
                if not cite or cite == "none":
                    continue
                # Ensure format is [xxx]
                cleaned = str(cite).strip()
                if not cleaned.startswith("["):
                    cleaned = f"[{cleaned.strip('[] ')}]"

                # Filter invalid cite
                if cleaned in knowledge_ids:
                    filtered_cites.append(cleaned)
                else:
                    self.logger.warning(
                        f"[ManagerAgent] Skipping unknown cite_id {cleaned} (not in knowledge chain)"
                    )

            # Create step
            steps.append(
                SolveChainStep(
                    step_id=step_id,
                    step_target=step_target,
                    available_cite=list(dict.fromkeys(filtered_cites)),  # Remove duplicates
                    status="undone",
                )
            )

        if not steps:
            raise ValueError("Failed to parse any valid steps, please check LLM output format.")

        logger = getattr(self, "logger", None)
        if logger is not None:
            logger.info(f"[ManagerAgent._parse_response] Parsed {len(steps)} solve-chain steps")
            for step in steps:
                logger.info(f"  - {step.step_id}: {step.step_target}")
                logger.info(
                    f"    Available citations: {', '.join(step.available_cite) or '(none)'}"
                )

        return steps
