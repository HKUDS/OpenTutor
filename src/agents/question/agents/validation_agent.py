#!/usr/bin/env python
"""
Validation Agent - Responsible for validating question rigor and correctness.
Uses unified PromptManager for prompt loading.
"""

import json
from pathlib import Path
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import get_logger
from src.services.config import load_config_with_main
from src.services.prompt import get_prompt_manager
from src.tools.rag_tool import rag_search

from .base_agent import Action, BaseAgent, Message, Observation

# Module logger
_logger = get_logger("QuestionValidationAgent")


class QuestionValidationAgent(BaseAgent):
    """Validation Agent"""

    def __init__(self, language: str = "en", **kwargs):
        super().__init__(agent_name="QuestionValidationAgent", language=language, **kwargs)

        # Load prompts using unified PromptManager
        self._prompts = get_prompt_manager().load_prompts(
            module_name="question",
            agent_name="validation_agent",
            language=language,
        )

        # Load config for RAG settings
        self._config = load_config_with_main("question_config.yaml", project_root)

        self.current_question = None
        self.validation_result = None

    def get_system_prompt(self) -> str:
        return self._prompts.get("system", "")

    def get_available_actions(self) -> list[dict[str, str]]:
        return [
            {
                "name": "retrieve",
                "description": "Retrieve knowledge from knowledge base for validation",
                "parameters": "query (str): Retrieval query",
            },
            {
                "name": "validate",
                "description": "Validate question rigor and correctness",
                "parameters": "None",
            },
            {
                "name": "request_modification",
                "description": "Request question generation agent to modify question",
                "parameters": "None",
            },
            {
                "name": "request_regeneration",
                "description": "Request question generation agent to regenerate question",
                "parameters": "None",
            },
            {
                "name": "approve_question",
                "description": "Validation passed, output final question",
                "parameters": "None",
            },
        ]

    async def execute_action(self, action: Action) -> Observation:
        """Execute specific action"""
        try:
            if action.name == "retrieve":
                return await self._action_retrieve(action.params)

            if action.name == "validate":
                return await self._action_validate()

            if action.name == "request_modification":
                return await self._action_request_modification()

            if action.name == "request_regeneration":
                return await self._action_request_regeneration()

            if action.name == "approve_question":
                return await self._action_approve_question()

            return Observation(success=False, result=None, message=f"Unknown action: {action.name}")

        except Exception as e:
            return Observation(
                success=False, result=None, message=f"Action execution failed: {e!s}"
            )

    async def _action_retrieve(self, params: dict[str, Any]) -> Observation:
        """Retrieve validation knowledge"""
        query = params.get("query", "")

        if not query:
            return Observation(
                success=False, result=None, message="Retrieval query cannot be empty"
            )

        # Get RAG mode from config
        question_cfg = self._config.get("question", {})
        rag_mode = question_cfg.get("rag_mode", "hybrid")

        result = await rag_search(
            query=query,
            kb_name=self.kb_name,
            mode=rag_mode,
            only_need_context=True,
        )

        answer = result.get("answer", "")

        self.retrieved_knowledge.append(
            {
                "query": query,
                "answer": answer,
            }
        )

        answer_len = len(answer) if answer else 0
        summary = f"Retrieved context with {answer_len} characters for query: {query[:50]}..."

        return Observation(success=True, result={"answer": answer}, message=summary)

    async def _action_validate(self) -> Observation:
        """Validate question"""
        if not self.current_question:
            return Observation(success=False, result=None, message="No question to validate")

        knowledge_parts = []
        for k in self.retrieved_knowledge:
            knowledge_parts.append(f"=== Query: {k['query']} ===")
            answer = k.get("answer", "")
            if answer:
                # Truncate very long contexts
                if len(answer) > 3000:
                    answer = answer[:3000] + "...[truncated]"
                knowledge_parts.append(answer)
            knowledge_parts.append("")

        validation_knowledge_str = (
            "\n".join(knowledge_parts) if knowledge_parts else "No validation knowledge retrieved"
        )

        prompt_template = self._prompts.get("validate", "")
        prompt = prompt_template.format(
            question=json.dumps(self.current_question, ensure_ascii=False, indent=2),
            validation_knowledge=validation_knowledge_str,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict question validation expert"},
                {"role": "user", "content": prompt},
            ],
            temperature=self._agent_params["temperature"],
            max_tokens=self._agent_params["max_tokens"],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        self.validation_result = result

        # Ensure issues and suggestions are lists
        issues = result.get("issues", [])
        if not isinstance(issues, list):
            _logger.warning(f"Issues is not a list (type: {type(issues)}), converting...")
            if isinstance(issues, dict):
                issues = [issues]
            else:
                issues = []
            result["issues"] = issues

        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            _logger.warning(f"Suggestions is not a list (type: {type(suggestions)}), converting...")
            if isinstance(suggestions, dict):
                suggestions = [suggestions]
            else:
                suggestions = []
            result["suggestions"] = suggestions

        decision = result.get("decision")
        issues_count = len(issues)

        return Observation(
            success=True,
            result=result,
            message=f"Validation decision: {decision}, found {issues_count} issues",
        )

    async def _action_request_modification(self) -> Observation:
        """Request question modification"""
        if not self.validation_result:
            return Observation(
                success=False,
                result=None,
                message="Error: Must execute validate action first to get validation result. Please execute validate to validate the question!",
            )

        decision = self.validation_result.get("decision")
        if decision != "request_modification":
            return Observation(
                success=False,
                result=None,
                message=f"Error: validate decision is '{decision}', should not execute request_modification. Please execute corresponding action based on validation decision!",
            )

        if hasattr(self, "send_message") and self.send_message:
            message = Message(
                from_agent=self.agent_name,
                to_agent="QuestionGenerationAgent",
                message_type="request_modification",
                content={
                    "issues": self.validation_result.get("issues", []),
                    "suggestions": self.validation_result.get("suggestions", []),
                    "reasoning": self.validation_result.get("reasoning", ""),
                },
            )
            await self.send_message(message)

        return Observation(
            success=True,
            result=self.validation_result,
            message="Modification request sent to question generation agent",
        )

    async def _action_request_regeneration(self) -> Observation:
        """Request question regeneration"""
        if not self.validation_result:
            return Observation(
                success=False,
                result=None,
                message="Error: Must execute validate action first to get validation result. Please execute validate to validate the question!",
            )

        decision = self.validation_result.get("decision")
        if decision != "request_regeneration":
            return Observation(
                success=False,
                result=None,
                message=f"Error: validate decision is '{decision}', should not execute request_regeneration.",
            )

        if hasattr(self, "send_message") and self.send_message:
            message = Message(
                from_agent=self.agent_name,
                to_agent="QuestionGenerationAgent",
                message_type="request_regeneration",
                content={
                    "issues": self.validation_result.get("issues", []),
                    "suggestions": self.validation_result.get("suggestions", []),
                    "reasoning": self.validation_result.get("reasoning", ""),
                },
            )
            await self.send_message(message)

        return Observation(
            success=True,
            result=self.validation_result,
            message="Regeneration request sent to question generation agent",
        )

    async def _action_approve_question(self) -> Observation:
        """Validation passed, output final question"""
        if not self.current_question:
            return Observation(
                success=False,
                result=None,
                message="Error: No question to approve. Please get question from inbox first.",
            )

        if not self.validation_result:
            return Observation(
                success=False,
                result=None,
                message="Error: Must execute validate action first to get validation result, then can approve. Please execute validate action to validate the question!",
            )

        decision = self.validation_result.get("decision")
        if decision != "approve":
            return Observation(
                success=False,
                result=None,
                message=f"Error: validate decision is '{decision}', cannot execute approve_question. Should execute corresponding action.",
            )

        final_result = {
            "question": self.current_question,
            "validation": self.validation_result,
            "status": "approved",
        }

        return Observation(success=True, result=final_result, message="Question validation passed!")
