#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GenerateAgent - Responsible for generating questions based on knowledge context.

Uses unified BaseAgent for LLM calls and configuration management.
"""

import json
import re
from typing import Any

from src.agents.base_agent import BaseAgent


class GenerateAgent(BaseAgent):
    """
    Agent responsible for generating questions from knowledge context.

    Responsibilities:
    - Generate questions based on requirements and knowledge
    - Support both custom mode (from scratch) and mimic mode (from reference)
    - Output structured question JSON
    """

    def __init__(
        self,
        language: str = "en",
        **kwargs,
    ):
        """
        Initialize GenerateAgent.

        Args:
            language: Language for prompts ("en" or "zh")
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(
            module_name="question",
            agent_name="generate_agent",
            language=language,
            **kwargs,
        )

    async def process(
        self,
        requirement: dict[str, Any],
        knowledge_context: str,
        focus: dict[str, Any] | None = None,
        reference_question: str | None = None,
    ) -> dict[str, Any]:
        """
        Main processing: generate a question.

        Args:
            requirement: Question requirement dict (knowledge_point, difficulty, question_type, etc.)
            knowledge_context: Retrieved knowledge summary
            focus: Optional focus/angle for the question
            reference_question: Optional reference question for mimic mode

        Returns:
            Dict with:
                - success: Whether generation succeeded
                - question: Generated question dict (if success)
                - error: Error message (if failed)
        """
        self.logger.info("Starting question generation")

        # Build requirements string
        requirements_str = json.dumps(requirement, ensure_ascii=False, indent=2)

        # Build focus string
        if focus:
            focus_str = f"Focus: {focus.get('focus', '')}\nType: {focus.get('type', requirement.get('question_type', 'written'))}"
        else:
            focus_str = f"Type: {requirement.get('question_type', 'written')}"

        # Choose prompt based on mode
        if reference_question:
            # Mimic mode
            return await self._generate_with_reference(
                requirements_str=requirements_str,
                knowledge_context=knowledge_context,
                reference_question=reference_question,
            )
        else:
            # Custom mode
            return await self._generate_custom(
                requirements_str=requirements_str,
                knowledge_context=knowledge_context,
                focus_str=focus_str,
                knowledge_point=requirement.get("knowledge_point", ""),
            )

    async def _generate_custom(
        self,
        requirements_str: str,
        knowledge_context: str,
        focus_str: str,
        knowledge_point: str,
    ) -> dict[str, Any]:
        """
        Generate a custom question (not based on reference).

        Args:
            requirements_str: JSON string of requirements
            knowledge_context: Retrieved knowledge summary
            focus_str: Focus/angle description
            knowledge_point: Main knowledge point

        Returns:
            Dict with success status and question/error
        """
        system_prompt = self.get_prompt("system", "")
        user_prompt_template = self.get_prompt("generate", "")

        if not user_prompt_template:
            # Fallback prompt
            user_prompt_template = (
                "Generate a question based on:\n"
                "Requirements: {requirements}\n"
                "Focus: {focus}\n"
                "Knowledge: {knowledge}\n\n"
                "Return JSON with question_type, question, correct_answer, explanation."
            )

        user_prompt = user_prompt_template.format(
            requirements=requirements_str,
            focus=focus_str,
            knowledge=knowledge_context[:4000]
            if len(knowledge_context) > 4000
            else knowledge_context,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
                stage="generate_question",
            )

            question = self._parse_question_response(response)
            question["knowledge_point"] = knowledge_point

            self.logger.info(f"Generated {question.get('question_type', 'unknown')} question")

            return {
                "success": True,
                "question": question,
            }

        except Exception as e:
            self.logger.error(f"Question generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _generate_with_reference(
        self,
        requirements_str: str,
        knowledge_context: str,
        reference_question: str,
    ) -> dict[str, Any]:
        """
        Generate a question based on a reference (mimic mode).

        Args:
            requirements_str: JSON string of requirements
            knowledge_context: Retrieved knowledge summary
            reference_question: Reference question text

        Returns:
            Dict with success status and question/error
        """
        system_prompt = self.get_prompt("system", "")
        user_prompt_template = self.get_prompt("generate_with_reference", "")

        if not user_prompt_template:
            # Fallback prompt
            user_prompt_template = (
                "Generate a new question inspired by the reference but distinct:\n"
                "Reference: {reference_question}\n"
                "Requirements: {requirements}\n"
                "Knowledge: {knowledge}\n\n"
                "Return JSON with question_type, question, correct_answer, explanation."
            )

        user_prompt = user_prompt_template.format(
            reference_question=reference_question,
            requirements=requirements_str,
            knowledge=knowledge_context[:4000]
            if len(knowledge_context) > 4000
            else knowledge_context,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
                stage="generate_with_reference",
            )

            question = self._parse_question_response(response)

            self.logger.info(f"Generated mimic {question.get('question_type', 'unknown')} question")

            return {
                "success": True,
                "question": question,
            }

        except Exception as e:
            self.logger.error(f"Reference-based generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _parse_question_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into question dict.

        Uses robust JSON extraction that handles:
        - Markdown code blocks
        - Control characters in LaTeX formulas
        - Python triple-quoted strings
        - Partial JSON extraction

        Args:
            response: LLM response string

        Returns:
            Parsed question dict

        Raises:
            ValueError: If parsing fails
        """
        if not response or not response.strip():
            raise ValueError("LLM returned empty response")

        # Try to extract JSON from markdown code blocks if present
        json_content = self._extract_json_from_markdown(response)

        # Clean control characters that may break JSON parsing
        json_content = self._clean_json_string(json_content)

        # Try multiple parsing strategies
        question = None
        parse_error = None

        # Strategy 1: Direct parse
        try:
            question = json.loads(json_content)
        except json.JSONDecodeError as e:
            parse_error = e

        # Strategy 2: Try extracting JSON object pattern
        if question is None:
            json_obj_pattern = re.compile(r"\{[\s\S]*\}")
            match = json_obj_pattern.search(json_content)
            if match:
                try:
                    question = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        # Strategy 3: Try fixing common LLM JSON issues
        if question is None:
            try:
                fixed_content = self._fix_common_json_issues(json_content)
                question = json.loads(fixed_content)
            except json.JSONDecodeError:
                pass

        if question is None:
            raise ValueError(f"Failed to parse question JSON: {parse_error}") from parse_error

        # Validate required fields
        if "question" not in question:
            raise ValueError("Question response missing 'question' field")

        # Ensure question_type exists
        if "question_type" not in question:
            question["question_type"] = "written"

        # Validate options for choice questions
        if question.get("question_type") == "choice":
            options = question.get("options")
            if not options:
                # Create default options if missing
                self.logger.warning("Choice question missing options, adding placeholder")
                question["options"] = {
                    "A": "Option A (placeholder)",
                    "B": "Option B (placeholder)",
                    "C": "Option C (placeholder)",
                    "D": "Option D (placeholder)",
                }
            elif not isinstance(options, dict):
                # Convert to dict if it's a list or other format
                self.logger.warning(f"Options is not a dict: {type(options)}, converting")
                if isinstance(options, list):
                    question["options"] = {
                        chr(65 + i): str(opt) for i, opt in enumerate(options[:4])
                    }
                else:
                    question["options"] = {"A": str(options)}
            elif len(options) < 2:
                self.logger.warning(f"Choice question has only {len(options)} options")

        return question

    def _clean_json_string(self, json_str: str) -> str:
        """
        Clean JSON string by removing/escaping problematic characters.

        Handles:
        - Control characters (0x00-0x1f except tab, newline, carriage return)
        - Unescaped newlines inside string values
        """
        if not json_str:
            return json_str

        # Remove most control characters but keep \t, \n, \r
        # These can appear in LLM output and break JSON parsing
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", json_str)

        return cleaned

    def _fix_common_json_issues(self, content: str) -> str:
        """
        Attempt to fix common JSON issues from LLM output.

        Fixes:
        - Python triple-quoted strings converted to JSON strings
        - Trailing commas before closing braces/brackets
        """
        if not content:
            return content

        # Fix Python triple-quoted strings (LLMs sometimes generate these)
        def replace_triple_quotes(match: re.Match) -> str:
            inner = match.group(1)
            # Use json.dumps to properly escape the content
            return json.dumps(inner)

        content = re.sub(r'"""([\s\S]*?)"""', replace_triple_quotes, content)

        # Remove trailing commas before } or ]
        content = re.sub(r",\s*([}\]])", r"\1", content)

        return content

    def _extract_json_from_markdown(self, content: str) -> str:
        """
        Extract JSON from markdown code blocks.

        LLMs often wrap JSON in ```json ... ``` blocks. This method strips
        the markdown formatting and any surrounding text.

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
            # Return the content inside the first code block
            return matches[0].strip()

        # If no code blocks found, return as-is (might already be valid JSON)
        return content.strip()
