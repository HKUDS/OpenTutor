#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Agent class - Implements the ReAct (Reasoning + Acting) paradigm.

Uses the unified LLM Factory for all LLM calls, supporting:
- Cloud providers (OpenAI, Anthropic, DeepSeek, etc.)
- Local providers (Ollama, LM Studio, vLLM, etc.)
- Automatic retry with exponential backoff
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI

# Load environment variables
load_dotenv(override=False)

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import get_logger
from src.services.config import get_agent_params
from src.services.llm import complete as llm_complete
from src.services.llm.capabilities import supports_response_format
from src.services.llm.config import get_llm_config

# Module logger
_logger = get_logger("QuestionAgent")


class Action:
    """Represents an Agent action"""

    def __init__(self, name: str, **params):
        self.name = name
        self.params = params

    def __repr__(self):
        params_str = ", ".join([f"{k}={v}" for k, v in self.params.items()])
        return f"Action({self.name}, {params_str})"


class Observation:
    """Represents the observation result of an action"""

    def __init__(self, success: bool, result: Any, message: str = ""):
        self.success = success
        self.result = result
        self.message = message

    def __repr__(self):
        return f"Observation(success={self.success}, message={self.message})"


class Message:
    """Message passed between agents"""

    def __init__(self, from_agent: str, to_agent: str, message_type: str, content: dict[str, Any]):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message_type = message_type
        self.content = content

    def __repr__(self):
        return f"Message({self.from_agent} -> {self.to_agent}: {self.message_type})"


class BaseAgent(ABC):
    """
    Base Agent class implementing ReAct paradigm

    Subclasses need to implement:
    - get_available_actions(): Return available action list
    - execute_action(): Execute specific action
    - get_system_prompt(): Return system prompt
    """

    def __init__(
        self,
        agent_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
        max_iterations: int = 10,
        kb_name: str | None = None,
        token_stats_callback: Callable | None = None,
        language: str = "en",
    ):
        self.agent_name = agent_name
        self.max_iterations = max_iterations
        self.kb_name = kb_name
        self.token_stats_callback = token_stats_callback
        self.language = language

        # Load agent parameters from unified config (agents.yaml)
        self._agent_params = get_agent_params("question")

        # Load LLM configuration via unified config system
        try:
            llm_config = get_llm_config()
            self.api_key = api_key or llm_config.api_key
            self.base_url = base_url or llm_config.base_url
            self.api_version = api_version or llm_config.api_version
            self.binding = llm_config.binding or "openai"
            self.model = model or llm_config.model
        except Exception:
            # Fallback to environment variables
            self.api_key = api_key or os.getenv("LLM_API_KEY")
            self.base_url = base_url or os.getenv("LLM_HOST")
            self.api_version = api_version or os.getenv("LLM_API_VERSION")
            self.binding = os.getenv("LLM_BINDING", "openai")
            self.model = model or os.getenv("LLM_MODEL")

        if not self.model:
            from src.services.llm.exceptions import LLMConfigError
            raise LLMConfigError(
                "LLM_MODEL not configured. Please set it in .env or activate a provider."
            )

        # Initialize OpenAI client for direct API calls
        if self.binding == "azure":
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.base_url,
                api_version=self.api_version or "2024-02-15-preview",
            )
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

        self.thought_history: list[str] = []
        self.action_history: list[Action] = []
        self.observation_history: list[Observation] = []
        self.retrieved_knowledge: list[dict[str, Any]] = []

        self.inbox: list[Message] = []

    @abstractmethod
    def get_available_actions(self) -> list[dict[str, str]]:
        """
        Return available action list

        Returns:
            List[Dict]: [{"name": "action_name", "description": "action_desc", "parameters": "param_desc"}, ...]
        """

    @abstractmethod
    async def execute_action(self, action: Action) -> Observation:
        """
        Execute specific action

        Args:
            action: Action to execute

        Returns:
            Observation: Observation result of the action
        """

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return system prompt

        Returns:
            str: System prompt
        """

    def receive_message(self, message: Message):
        """Receive message from other Agent."""
        self.inbox.append(message)
        _logger.debug(f"[{self.agent_name}] Received message: {message}")

    def format_history(self) -> str:
        """Format history"""
        if not self.thought_history:
            return "(No history)"

        history_parts = []

        recent_count = min(3, len(self.action_history))
        if recent_count > 0:
            history_parts.append("🔥 **Recent Actions** (Must read! Avoid repeating actions)")
            history_parts.append("=" * 60)
            for i in range(len(self.action_history) - recent_count, len(self.action_history)):
                action = self.action_history[i]
                obs = self.observation_history[i] if i < len(self.observation_history) else None
                status = "✓ Success" if (obs and obs.success) else "✗ Failed"

                history_parts.append(f"  [{i + 1}] Action: {action.name} → {status}")
                if action.params:
                    history_parts.append(
                        f"      Params: {json.dumps(action.params, ensure_ascii=False)}"
                    )
                if obs and obs.message:
                    history_parts.append(f"      Result: {obs.message}")
            history_parts.append(
                "⚠️  Please decide next step based on recent actions, avoid repeating the same actions!"
            )
            history_parts.append("=" * 60 + "\n")

        if self.retrieved_knowledge:
            history_parts.append("📚 **Retrieved Knowledge Summary** (No need to retrieve again)")
            history_parts.append("=" * 60)
            for i, k in enumerate(self.retrieved_knowledge, 1):
                query = k.get("query", "N/A")
                num_entities = len(k.get("entities", []))
                num_relations = len(k.get("relations", []))
                num_text = len(k.get("text_chunks", []))
                num_multimodal = len(k.get("multimodal_chunks", []))
                history_parts.append(
                    f'  {i}. Query: "{query}" → '
                    f"{num_entities} entities, {num_relations} relations, "
                    f"{num_text} text chunks, {num_multimodal} multimodal content"
                )
            history_parts.append("=" * 60 + "\n")

        if len(self.thought_history) > 0:
            history_parts.append("📜 **Complete History**")
            history_parts.append("-" * 60)
            for i in range(len(self.thought_history)):
                history_parts.append(f"\nRound {i + 1}:")
                history_parts.append(f"Thought: {self.thought_history[i]}")

                if i < len(self.action_history):
                    action = self.action_history[i]
                    history_parts.append(f"Action: {action.name}")
                    if action.params:
                        history_parts.append(
                            f"  Params: {json.dumps(action.params, ensure_ascii=False)}"
                        )

                if i < len(self.observation_history):
                    obs = self.observation_history[i]
                    status = "✓ Success" if obs.success else "✗ Failed"
                    history_parts.append(f"Observation: {status}")
                    if obs.message:
                        history_parts.append(f"  Message: {obs.message}")
            history_parts.append("-" * 60)

        return "\n".join(history_parts)

    def format_inbox(self) -> str:
        """Format inbox"""
        if not self.inbox:
            return "(Inbox is empty)"

        inbox_parts = []
        for msg in self.inbox:
            inbox_parts.append(f"- From {msg.from_agent}: {msg.message_type}")
            inbox_parts.append(
                f"  Content: {json.dumps(msg.content, ensure_ascii=False, indent=2)}"
            )

        return "\n".join(inbox_parts)

    async def think(self, task: str, context: dict[str, Any] = None) -> dict[str, Any]:
        """
        Think about next action

        Args:
            task: Current task description
            context: Additional context information

        Returns:
            Dict: {"thought": str, "action": str, "parameters": Dict}
        """
        system_prompt = self.get_system_prompt()

        actions_desc = "\n".join(
            [
                f"- **{a['name']}**: {a['description']}\n  Parameters: {a['parameters']}"
                for a in self.get_available_actions()
            ]
        )

        # Build context description
        context_info = ""
        if context:
            # Check if it's a new round iteration
            round_num = context.get("round_num")
            is_new_round = context.get("is_new_round", False)

            if round_num and round_num > 1:
                context_info = (
                    f"\n{'=' * 60}\n⚠️  Important note: This is round {round_num} iteration\n"
                )
                if is_new_round:
                    context_info += "- Work in history was for previous version of question/task\n"
                    context_info += (
                        "- Now received new content, need to re-execute complete workflow\n"
                    )
                    context_info += "- Can reference retrieved knowledge from history, but don't skip necessary steps\n"
                    context_info += "- Special note: Even if validated/generated before, need to re-process now\n"
                context_info += f"{'=' * 60}\n"

            context_info += (
                f"\nCurrent context:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"
            )

        user_prompt = f"""Current task: {task}
{context_info}
Inbox:
{self.format_inbox()}

History:
{self.format_history()}

Available actions:
{actions_desc}

Please think and decide the next action.

Output JSON format:
{{
    "thought": "your thinking process",
    "action": "action name",
    "parameters": {{"parameter_name": "parameter_value"}}
}}

⚠️  **Important notes**:
1. **Must read history**: Check "Recent actions" section to understand what you just did
2. **Avoid duplicate actions**: If you just successfully executed an action, don't execute the same action again!
3. **Logical flow**: Based on recent action results, choose reasonable next action
   - Example: retrieve → generate → submit, not generate → generate
4. If inbox has messages, process messages first
5. History can be referenced, but if it's a new round, must re-execute key steps
"""

        # Build kwargs for LLM Factory
        llm_kwargs = {
            "temperature": self._agent_params["temperature"],
            "max_tokens": self._agent_params["max_tokens"],
        }

        # Only add response_format if the provider supports it
        if supports_response_format(self.binding, self.model):
            llm_kwargs["response_format"] = {"type": "json_object"}

        # Call LLM via unified Factory (supports all providers with retry)
        response_content = await llm_complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            api_version=self.api_version,
            binding=self.binding,
            **llm_kwargs,
        )

        # Update token statistics if callback is available
        # Note: Factory doesn't return token counts, estimate based on response
        if self.token_stats_callback:
            # Rough estimation: ~4 chars per token
            input_tokens = (len(system_prompt) + len(user_prompt)) // 4
            output_tokens = len(response_content) // 4
            self.token_stats_callback(
                input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
            )

        # Log LLM call with detailed information
        _logger.log_llm_call(
            model=self.model,
            stage="think",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response_content,
            agent_name=self.agent_name,
            input_tokens=0,  # Not available from factory
            output_tokens=0,
            cost=0.0,
            level="DEBUG",
        )

        result = json.loads(response_content)

        # Record thought
        thought = result.get("thought", "")
        self.thought_history.append(thought)

        _logger.debug(f"[{self.agent_name}] Thinking: {thought[:100]}...")

        return result

    async def act(self, action_name: str, parameters: dict[str, Any]) -> Observation:
        """
        Execute an action

        Args:
            action_name: Action name
            parameters: Action parameters

        Returns:
            Observation: Observation result
        """
        action = Action(action_name, **parameters)
        self.action_history.append(action)

        _logger.info(f"[{self.agent_name}] Action: {action_name}")
        if parameters:
            _logger.debug(f"  Parameters: {json.dumps(parameters, ensure_ascii=False)[:100]}")

        observation = await self.execute_action(action)
        self.observation_history.append(observation)

        if observation.success:
            _logger.debug(f"[{self.agent_name}] Observation: Success")
        else:
            _logger.warning(f"[{self.agent_name}] Observation: Failed")
        if observation.message:
            _logger.debug(f"  Message: {observation.message[:100]}")

        # Print detailed information about action results
        if observation.success and observation.result:
            self._print_result(action_name, observation.result)

        return observation

    def _print_result(self, action_name: str, result: Any):
        """Log action result details."""
        try:
            if action_name == "retrieve":
                # Retrieval action result
                if isinstance(result, dict):
                    entities = result.get("entities", [])
                    relations = result.get("relations", [])
                    text_chunks = result.get("text_chunks", [])
                    multimodal_chunks = result.get("multimodal_chunks", [])

                    _logger.debug(
                        f"  Result: {len(entities)} entities, {len(relations)} relations, {len(text_chunks)} text chunks, {len(multimodal_chunks)} multimodal items"
                    )

            elif action_name == "generate_question":
                # Generate question result
                if isinstance(result, dict):
                    q_type = result.get("question_type", "N/A")
                    _logger.debug(f"  Result: Generated {q_type} type question")

            elif action_name == "refine_question":
                # Refine question result
                if isinstance(result, dict):
                    q_type = result.get("question_type", "N/A")
                    _logger.debug(f"  Result: Refined {q_type} type question")

            elif action_name == "validate":
                # Validation result
                if isinstance(result, dict):
                    decision = result.get("decision", "N/A")
                    issues = result.get("issues", [])
                    _logger.debug(
                        f"  Result: Validation decision = {decision}, {len(issues)} issues"
                    )

            elif action_name == "reject_task":
                # Task rejection result
                if isinstance(result, dict):
                    reason = result.get("reason", "N/A")
                    _logger.info(f"  Result: Task rejected - {reason[:100]}")

            elif action_name in [
                "submit_question",
                "request_modification",
                "request_regeneration",
                "approve_question",
            ]:
                # Message sending actions
                _logger.debug("  Result: Message sent")

            # Other actions
            elif isinstance(result, dict):
                _logger.debug(f"  Result: {json.dumps(result, ensure_ascii=False)[:80]}...")
            elif isinstance(result, str):
                _logger.debug(f"  Result: {result[:80]}...")

        except Exception:
            # Log failure should not affect main flow
            pass

    async def run(
        self,
        task: str,
        context: dict[str, Any] = None,
        send_message_callback: Callable | None = None,
    ) -> dict[str, Any]:
        """
        Run the main loop of the Agent (think-act-observe)

        Args:
            task: Task description
            context: Initial context
            send_message_callback: Callback function for sending messages

        Returns:
            Dict: Execution result
        """
        _logger.info(f"[{self.agent_name}] Starting task execution")
        _logger.debug(f"  Task: {task[:80]}...")

        self.send_message = send_message_callback

        for iteration in range(self.max_iterations):
            _logger.info(
                f"[{self.agent_name}] ReAct iteration {iteration + 1}/{self.max_iterations}"
            )

            # Think
            decision = await self.think(task, context)

            # Act
            action_name = decision.get("action")
            parameters = decision.get("parameters", {})

            observation = await self.act(action_name, parameters)

            # Check if submitted (for QuestionGenerationAgent)
            if hasattr(self, "submitted") and self.submitted:
                _logger.success(f"[{self.agent_name}] Question submitted, task completed")
                return {"success": True, "result": observation.result, "iterations": iteration + 1}

            # Check if completed
            # These actions indicate the Agent has completed the current stage
            terminal_actions = [
                "submit_question",  # Generation agent submits question
                "approve_question",  # Validation agent approves question
                "request_modification",  # Validation agent requests modification
                "request_regeneration",  # Validation agent requests regeneration
                "reject_task",  # Generation agent rejects task
                "finish",  # Generic completion flag
            ]

            if action_name in terminal_actions:
                _logger.success(f"[{self.agent_name}] Task completed")
                return {"success": True, "result": observation.result, "iterations": iteration + 1}

        _logger.warning(f"[{self.agent_name}] Max iterations reached")
        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": self.max_iterations,
        }

    def reset(self):
        """Reset Agent state"""
        self.thought_history.clear()
        self.action_history.clear()
        self.observation_history.clear()
        self.inbox.clear()
