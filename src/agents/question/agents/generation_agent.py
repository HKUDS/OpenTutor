#!/usr/bin/env python
"""
Question Generation Agent - responsible for creating and refining questions.
Uses unified PromptManager for prompt loading.
"""

import json
from pathlib import Path
import sys
from typing import Any

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import get_logger
from src.services.config import load_config_with_main
from src.services.prompt import get_prompt_manager
from src.tools.rag_tool import rag_search

from .base_agent import Action, BaseAgent, Message, Observation

# Module logger
_logger = get_logger("QuestionGenerationAgent")


class QuestionGenerationAgent(BaseAgent):
    """Question generation agent"""

    def __init__(self, language: str = "en", **kwargs):
        super().__init__(agent_name="QuestionGenerationAgent", language=language, **kwargs)

        # Load prompts using unified PromptManager
        self._prompts = get_prompt_manager().load_prompts(
            module_name="question",
            agent_name="generation_agent",
            language=language,
        )

        # Load config for RAG settings
        self._config = load_config_with_main("question_config.yaml", project_root)

        # State
        self.current_requirement = None
        self.current_question = None
        self.retrieved_knowledge = []  # Retrieved knowledge
        self.submitted = False  # Whether a question has been submitted

    def reset(self):
        """Reset agent state, including custom fields."""
        super().reset()
        self.current_requirement = None
        self.current_question = None
        self.retrieved_knowledge = []
        self.submitted = False

    def get_system_prompt(self) -> str:
        return self._prompts.get("system", "")

    def get_available_actions(self) -> list[dict[str, str]]:
        """Return available actions for the agent."""
        return [
            {
                "name": "retrieve",
                "description": "Retrieve relevant knowledge from the knowledge base",
                "parameters": "query (str): search query",
            },
            {
                "name": "generate_question",
                "description": "Generate a new question based on retrieved knowledge",
                "parameters": "none",
            },
            {
                "name": "refine_question",
                "description": "Refine the question according to validation feedback",
                "parameters": "none",
            },
            {
                "name": "submit_question",
                "description": "Submit the current question to the Validation Agent",
                "parameters": "none",
            },
        ]

    async def execute_action(self, action: Action) -> Observation:
        """Execute concrete actions."""
        try:
            if action.name == "retrieve":
                return await self._action_retrieve(action.params)

            if action.name == "generate_question":
                return await self._action_generate_question()

            if action.name == "refine_question":
                return await self._action_refine_question()

            if action.name == "submit_question":
                return await self._action_submit_question()

            return Observation(success=False, result=None, message=f"Unknown action: {action.name}")

        except Exception as e:
            return Observation(
                success=False, result=None, message=f"Action execution failed: {e!s}"
            )

    async def _action_retrieve(self, params: dict[str, Any]) -> Observation:
        """Retrieve knowledge from the KB."""
        query = params.get("query", "")

        if not query:
            return Observation(success=False, result=None, message="Search query cannot be empty")

        # Get RAG mode from config
        question_cfg = self._config.get("question", {})
        rag_mode = question_cfg.get("rag_mode", "hybrid")

        # Use unified RAG tool
        result = await rag_search(
            query=query,
            kb_name=self.kb_name,
            mode=rag_mode,
            only_need_context=True,
        )

        answer = result.get("answer", "")

        # Save retrieved knowledge
        self.retrieved_knowledge.append(
            {
                "query": query,
                "answer": answer,
            }
        )

        # Summarize result
        answer_len = len(answer) if answer else 0
        summary = f"Retrieved context with {answer_len} characters for query: {query[:50]}..."

        return Observation(success=True, result={"answer": answer}, message=summary)

    async def _action_generate_question(self) -> Observation:
        """Generate a question."""
        if not self.retrieved_knowledge:
            return Observation(
                success=False, result=None, message="Run retrieve before generating a question"
            )

        # Format retrieved knowledge
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

        knowledge_str = "\n".join(knowledge_parts)

        # Check whether a reference question exists
        reference_question = self.current_requirement.get("reference_question")

        # Call LLM to generate the question
        if reference_question:
            # Use reference-aware prompt
            prompt_template = self._prompts.get("generate_with_reference", "")
            prompt = prompt_template.format(
                reference_question=reference_question,
                requirements=json.dumps(self.current_requirement, ensure_ascii=False, indent=2),
                knowledge=knowledge_str,
            )
        else:
            # Use standard prompt
            prompt_template = self._prompts.get("generate", "")
            prompt = prompt_template.format(
                requirements=json.dumps(self.current_requirement, ensure_ascii=False, indent=2),
                knowledge=knowledge_str,
            )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional question designer"},
                {"role": "user", "content": prompt},
            ],
            temperature=self._agent_params["temperature"],
            max_tokens=self._agent_params["max_tokens"],
            response_format={"type": "json_object"},
        )

        # Extract response content
        response_content = response.choices[0].message.content

        # Update token statistics if callback is available
        input_tokens = 0
        output_tokens = 0
        cost = 0.0
        if hasattr(response, "usage") and response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = input_tokens * 0.00000015 + output_tokens * 0.0000006
            if self.token_stats_callback:
                self.token_stats_callback(
                    input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
                )

        # Log LLM call with detailed information
        _logger.log_llm_call(
            model=self.model,
            stage="generate_question",
            system_prompt="You are a professional question designer",
            user_prompt=prompt,
            response=response_content,
            agent_name="QuestionGenerationAgent",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            level="DEBUG",
        )

        # Parse JSON with error handling
        try:
            question = json.loads(response_content)
            self.current_question = question
        except json.JSONDecodeError as e:
            error_msg = (
                f"[generate_question] Failed to parse JSON response: {e}\n"
                f"Response content: {response_content[:500]}..."
            )
            _logger.error(error_msg)
            return Observation(
                success=False, result=None, message=f"Failed to parse question JSON: {e}"
            )

        # Automatically submit after generation
        submit_result = await self._action_submit_question()
        self.submitted = True  # Mark as submitted

        # Return the submission result to stop the loop
        return submit_result

    async def _action_refine_question(self) -> Observation:
        """Refine the question."""
        if not self.current_question:
            return Observation(
                success=False, result=None, message="No question available for refinement"
            )

        # Get feedback from inbox
        feedback_msg = None
        for msg in self.inbox:
            if msg.message_type in ["request_modification", "request_regeneration"]:
                feedback_msg = msg
                break

        if not feedback_msg:
            return Observation(success=False, result=None, message="No validation feedback found")

        # Format retrieved knowledge
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
        knowledge_str = "\n".join(knowledge_parts)

        # Call LLM to refine the question
        prompt_template = self._prompts.get("refine", "")
        prompt = prompt_template.format(
            original_question=json.dumps(self.current_question, ensure_ascii=False, indent=2),
            feedback=json.dumps(feedback_msg.content, ensure_ascii=False, indent=2),
            knowledge=knowledge_str,
        )

        # Log request details
        _logger.debug(
            f"[refine_question] Calling LLM: model={self.model}, "
            f"prompt_len={len(prompt)}, temperature={self._agent_params['temperature']}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional question designer"},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._agent_params["temperature"],
                max_tokens=self._agent_params["max_tokens"],
                response_format={"type": "json_object"},
                timeout=180.0,  # Add timeout
            )
        except Exception as e:
            error_msg = f"[refine_question] LLM API call failed: {type(e).__name__}: {e}"
            _logger.error(error_msg)
            return Observation(
                success=False, result=None, message=f"Failed to refine question: {e}"
            )

        # Validate response structure
        if not response or not response.choices:
            error_msg = "[refine_question] LLM returned empty response or no choices"
            _logger.error(error_msg)
            return Observation(success=False, result=None, message="LLM returned empty response")

        # Extract response content with validation
        response_content = response.choices[0].message.content

        # Validate content is not None or empty
        if response_content is None:
            error_msg = f"[refine_question] LLM returned None content. Response: {response}"
            _logger.error(error_msg)
            return Observation(success=False, result=None, message="LLM returned None content")

        if not response_content.strip():
            error_msg = f"[refine_question] LLM returned empty string. Response: {response}"
            _logger.error(error_msg)
            return Observation(success=False, result=None, message="LLM returned empty string")

        # Log successful response
        _logger.debug(
            f"[refine_question] LLM response received: "
            f"length={len(response_content)}, preview={response_content[:200]}..."
        )

        # Update token statistics if callback is available
        input_tokens = 0
        output_tokens = 0
        cost = 0.0
        if hasattr(response, "usage") and response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = input_tokens * 0.00000015 + output_tokens * 0.0000006
            if self.token_stats_callback:
                self.token_stats_callback(
                    input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
                )

        # Log LLM call with detailed information
        _logger.log_llm_call(
            model=self.model,
            stage="refine_question",
            system_prompt="You are a professional question designer",
            user_prompt=prompt,
            response=response_content,
            agent_name="QuestionGenerationAgent",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            level="DEBUG",
        )

        # Parse JSON with error handling
        try:
            question = json.loads(response_content)
            self.current_question = question
        except json.JSONDecodeError as e:
            error_msg = (
                f"[refine_question] Failed to parse JSON response: {e}\n"
                f"Response content: {response_content[:500]}..."
            )
            _logger.error(error_msg)
            return Observation(
                success=False, result=None, message=f"Failed to parse question JSON: {e}"
            )

        # Remove the processed feedback message
        self.inbox.remove(feedback_msg)

        # Automatically submit after refinement
        submit_result = await self._action_submit_question()
        self.submitted = True  # Mark as submitted

        # Return submission result to stop the loop
        return submit_result

    async def _action_submit_question(self) -> Observation:
        """Submit the current question to validation."""
        if not self.current_question:
            return Observation(success=False, result=None, message="There is no question to submit")

        # Send validation request
        if hasattr(self, "send_message") and self.send_message:
            message = Message(
                from_agent=self.agent_name,
                to_agent="QuestionValidationAgent",
                message_type="validate_request",
                content={"question": self.current_question},
            )
            await self.send_message(message)

        return Observation(
            success=True,
            result=self.current_question,
            message="Question submitted to Validation Agent",
        )

    def set_requirement(self, requirement: dict[str, Any]):
        """Set the current generation requirement"""
        self.current_requirement = requirement
