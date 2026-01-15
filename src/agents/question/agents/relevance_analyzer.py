#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RelevanceAnalyzer - Analyzes the relevance between questions and knowledge base.

Replaces the old validation workflow with a single-pass relevance analysis.
No iterative validation or rejection - all questions are accepted and analyzed.
"""

import json
import re
from typing import Any

from src.agents.base_agent import BaseAgent


class RelevanceAnalyzer(BaseAgent):
    """
    Agent responsible for analyzing question-knowledge relevance.

    Key difference from old ValidationWorkflow:
    - NO rejection: all questions are accepted
    - NO iteration: single-pass analysis
    - Output: relevance level (high/partial) with explanations

    Responsibilities:
    - Analyze how well a question aligns with knowledge base content
    - Identify what KB concepts the question tests
    - Identify any extensions beyond the KB (for "partial" relevance)
    """

    def __init__(
        self,
        language: str = "en",
        **kwargs,
    ):
        """
        Initialize RelevanceAnalyzer.

        Args:
            language: Language for prompts ("en" or "zh")
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(
            module_name="question",
            agent_name="relevance_analyzer",
            language=language,
            **kwargs,
        )

    async def process(
        self,
        question: dict[str, Any],
        knowledge_context: str,
    ) -> dict[str, Any]:
        """
        Main processing: analyze relevance between question and knowledge.

        Args:
            question: Generated question dict
            knowledge_context: Retrieved knowledge summary

        Returns:
            Dict with:
                - relevance: "high" or "partial"
                - kb_coverage: Description of KB content tested
                - extension_points: Description of extensions (only if partial)
        """
        self.logger.info("Starting relevance analysis")

        # Format question for analysis
        question_str = json.dumps(question, ensure_ascii=False, indent=2)

        # Truncate context if too long
        if len(knowledge_context) > 4000:
            knowledge_context = knowledge_context[:4000] + "...[truncated]"

        # Get prompts
        system_prompt = self.get_prompt("system", "")
        user_prompt_template = self.get_prompt("analyze_relevance", "")

        if not user_prompt_template:
            # Fallback prompt
            user_prompt_template = (
                "Analyze the relevance between this question and knowledge base:\n\n"
                "Question:\n{question}\n\n"
                "Knowledge Base:\n{knowledge}\n\n"
                "Return JSON with: relevance (high/partial), kb_coverage, extension_points"
            )

        user_prompt = user_prompt_template.format(
            question=question_str,
            knowledge=knowledge_context,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent analysis
                stage="analyze_relevance",
            )

            result = self._parse_analysis_response(response)

            self.logger.info(f"Relevance analysis completed: {result['relevance']}")

            return result

        except Exception as e:
            self.logger.warning(f"Relevance analysis failed: {e}")
            # Return default "partial" on failure
            return {
                "relevance": "partial",
                "kb_coverage": "Unable to analyze knowledge base coverage",
                "extension_points": f"Analysis could not be completed: {e}",
            }

    def _parse_analysis_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into analysis result.

        Uses robust JSON extraction that handles control characters
        and common LLM output issues.

        Args:
            response: LLM response string

        Returns:
            Parsed analysis dict with normalized relevance value
        """
        if not response or not response.strip():
            raise ValueError("LLM returned empty response")

        # Try to extract JSON from markdown code blocks if present
        json_content = self._extract_json_from_markdown(response)

        # Clean control characters
        json_content = self._clean_json_string(json_content)

        # Try multiple parsing strategies
        result = None
        parse_error = None

        # Strategy 1: Direct parse
        try:
            result = json.loads(json_content)
        except json.JSONDecodeError as e:
            parse_error = e

        # Strategy 2: Extract JSON object pattern
        if result is None:
            json_obj_pattern = re.compile(r"\{[\s\S]*\}")
            match = json_obj_pattern.search(json_content)
            if match:
                try:
                    result = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        if result is None:
            raise ValueError(f"Failed to parse analysis JSON: {parse_error}") from parse_error

        # Normalize relevance value
        relevance = result.get("relevance", "partial")
        if relevance not in ["high", "partial"]:
            relevance = "partial"

        return {
            "relevance": relevance,
            "kb_coverage": result.get("kb_coverage", ""),
            "extension_points": result.get("extension_points", "")
            if relevance == "partial"
            else "",
        }

    def _clean_json_string(self, json_str: str) -> str:
        """
        Clean JSON string by removing problematic control characters.
        """
        if not json_str:
            return json_str
        # Remove control characters except tab, newline, carriage return
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", json_str)

    def _extract_json_from_markdown(self, content: str) -> str:
        """
        Extract JSON from markdown code blocks.

        Args:
            content: Raw LLM response

        Returns:
            Extracted JSON string
        """
        if not content:
            return content

        # Try to find JSON code block
        json_block_pattern = r"```(?:json)?\s*\n?(.*?)```"
        matches = re.findall(json_block_pattern, content, re.DOTALL)

        if matches:
            return matches[0].strip()

        return content.strip()
