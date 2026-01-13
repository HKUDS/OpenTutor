#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PrecisionAnswerAgent - Precision answer generator (two-stage)
"""

from pathlib import Path
import sys
from typing import Any, Dict

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent


class PrecisionAnswerAgent(BaseAgent):
    """Staged precision answer"""

    def __init__(self, config: Dict[str, Any], api_key: str, base_url: str, token_tracker=None):
        language = config.get("system", {}).get("language", "zh")
        super().__init__(
            module_name="solve",
            agent_name="precision_answer_agent",
            api_key=api_key,
            base_url=base_url,
            language=language,
            config=config,
            token_tracker=token_tracker,
        )

    async def process(
        self, question: str, detailed_answer: str, verbose: bool = True
    ) -> Dict[str, Any]:
        decision = await self._should_generate(question, verbose)
        if not decision["needs_precision"]:
            return {
                "needs_precision": False,
                "precision_answer": "",
                "final_answer": detailed_answer,
            }

        precision_answer = await self._generate_precision_answer(
            question=question, detailed_answer=detailed_answer, verbose=verbose
        )
        return {
            "needs_precision": True,
            "precision_answer": precision_answer,
            "final_answer": detailed_answer,
        }

    async def _should_generate(self, question: str, verbose: bool) -> Dict[str, Any]:
        system_prompt = self.get_prompt("decision_system") if self.has_prompts() else None
        if not system_prompt:
            raise ValueError(
                "PrecisionAnswerAgent missing decision_system prompt, please configure decision_system in prompts/{lang}/solve_loop/precision_answer_agent.yaml"
            )
        template = self.get_prompt("decision_user_template") if self.has_prompts() else None
        if not template:
            raise ValueError(
                "PrecisionAnswerAgent missing decision_user_template, please configure decision_user_template in prompts/{lang}/solve_loop/precision_answer_agent.yaml"
            )
        user_prompt = template.format(question=question)
        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, verbose=verbose
        )
        needs_precision = response.strip().upper().startswith("Y")
        return {"needs_precision": needs_precision, "raw_decision": response.strip()}

    async def _generate_precision_answer(
        self, question: str, detailed_answer: str, verbose: bool
    ) -> str:
        system_prompt = self.get_prompt("precision_system") if self.has_prompts() else None
        if not system_prompt:
            raise ValueError(
                "PrecisionAnswerAgent missing precision_system prompt, please configure precision_system in prompts/{lang}/solve_loop/precision_answer_agent.yaml"
            )
        template = self.get_prompt("precision_user_template") if self.has_prompts() else None
        if not template:
            raise ValueError(
                "PrecisionAnswerAgent missing precision_user_template, please configure precision_user_template in prompts/{lang}/solve_loop/precision_answer_agent.yaml"
            )
        user_prompt = template.format(question=question, detailed_answer=detailed_answer)
        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, verbose=verbose
        )
        return response.strip()
