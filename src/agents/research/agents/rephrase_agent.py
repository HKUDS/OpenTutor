#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RephraseAgent - Topic rephrasing Agent
Responsible for rephrasing and optimizing user input
"""

from pathlib import Path
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent

from ..utils.json_utils import extract_json_from_text


class RephraseAgent(BaseAgent):
    """Topic rephrasing Agent"""

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str = None,
        base_url: str = None,
        api_version: str = None,
    ):
        language = config.get("system", {}).get("language", "zh")
        super().__init__(
            module_name="research",
            agent_name="rephrase_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            config=config,
        )
        # Store complete conversation history for multi-turn optimization
        self.conversation_history: list[dict[str, Any]] = []

    def reset_history(self):
        """Reset conversation history for a new research session"""
        self.conversation_history = []

    def _format_conversation_history(self) -> str:
        """Format conversation history for prompt"""
        if not self.conversation_history:
            return ""

        history_parts = []
        for entry in self.conversation_history:
            role = entry.get("role", "unknown")
            iteration = entry.get("iteration", 0)
            content = entry.get("content", "")

            if role == "user":
                if iteration == 0:
                    history_parts.append(f"[User - Initial Input]\n{content}")
                else:
                    history_parts.append(f"[User - Feedback (Round {iteration})]\n{content}")
            elif role == "assistant":
                topic = content.get("topic", "") if isinstance(content, dict) else str(content)
                history_parts.append(f"[Assistant - Rephrased Topic (Round {iteration})]\n{topic}")

        return "\n\n".join(history_parts)

    async def process(
        self, user_input: str, iteration: int = 0, previous_result: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Rephrase and optimize user input, supports user interaction confirmation
        Uses complete conversation history for better context understanding

        Args:
            user_input: User's original input (first time) or feedback (subsequent iterations)
            iteration: Iteration count (for tracking rephrasing rounds)
            previous_result: Previous rephrasing result (for backward compatibility)

        Returns:
            Dictionary containing rephrasing results
            {
                "topic": str,                  # Optimized research topic (a clear, explicit statement)
                "iteration": int,              # Iteration count
            }
        """
        print(f"\n{'=' * 70}")
        print(f"🔄 RephraseAgent - Topic Rephrasing (Iteration {iteration})")
        print(f"{'=' * 70}")

        # Reset history for new session (iteration 0)
        if iteration == 0:
            self.reset_history()
            print(f"Original Input: {user_input}\n")
        else:
            print(f"User Feedback: {user_input}\n")
            print(f"Conversation History: {len(self.conversation_history)} entries\n")

        # Add current user input to history
        self.conversation_history.append(
            {
                "role": "user",
                "content": user_input,
                "iteration": iteration,
            }
        )

        # Get system prompt
        system_prompt = self.get_prompt("system", "role")
        if not system_prompt:
            raise ValueError(
                "RephraseAgent missing system prompt, please configure system.role in prompts/{lang}/rephrase_agent.yaml"
            )

        # Get user prompt template
        user_prompt_template = self.get_prompt("process", "rephrase")
        if not user_prompt_template:
            raise ValueError(
                "RephraseAgent missing rephrase prompt, please configure process.rephrase in prompts/{lang}/rephrase_agent.yaml"
            )

        # Format conversation history for prompt
        history_text = self._format_conversation_history()

        # Format user prompt with full history
        user_prompt = user_prompt_template.format(
            user_input=user_input,
            iteration=iteration,
            conversation_history=history_text,
            previous_result=history_text,  # For backward compatibility with old templates
        )

        # Call LLM
        response = await self.call_llm(
            user_prompt=user_prompt, system_prompt=system_prompt, stage="rephrase"
        )

        # Parse JSON output
        data = extract_json_from_text(response)
        from ..utils.json_utils import ensure_json_dict, ensure_keys

        try:
            result = ensure_json_dict(data)
            ensure_keys(result, ["topic"])
        except Exception:
            # Fallback: use user input or last assistant topic
            fallback_topic = user_input
            for entry in reversed(self.conversation_history):
                if entry.get("role") == "assistant":
                    content = entry.get("content", {})
                    if isinstance(content, dict) and content.get("topic"):
                        fallback_topic = content["topic"]
                        break
            result = {"topic": fallback_topic}

        result["iteration"] = iteration

        # Add assistant response to history
        self.conversation_history.append(
            {
                "role": "assistant",
                "content": result,
                "iteration": iteration,
            }
        )

        print("\n✓ Rephrasing Completed:")
        print(f"  Optimized Research Topic: {result.get('topic', '')}")

        return result

    async def check_user_satisfaction(
        self, rephrase_result: dict[str, Any], user_feedback: str
    ) -> dict[str, Any]:
        """
        Determine user satisfaction with rephrasing result

        Args:
            rephrase_result: Current rephrasing result
            user_feedback: User feedback

        Returns:
            Dictionary containing judgment results
            {
                "user_satisfied": bool,        # Whether user is satisfied
                "should_continue": bool,       # Whether to continue rephrasing
                "interpretation": str,         # Interpretation of user intent
                "suggested_action": str        # Suggested next action
            }
        """
        print(f"\n{'=' * 70}")
        print("🤔 RephraseAgent - Judging User Intent")
        print(f"{'=' * 70}")
        print(f"User Feedback: {user_feedback}\n")

        system_prompt = self.get_prompt("system", "role")
        if not system_prompt:
            raise ValueError(
                "RephraseAgent missing system prompt, please configure system.role in prompts/{lang}/rephrase_agent.yaml"
            )

        user_prompt_template = self.get_prompt("process", "check_satisfaction")
        if not user_prompt_template:
            raise ValueError(
                "RephraseAgent missing check_satisfaction prompt, please configure process.check_satisfaction in prompts/{lang}/rephrase_agent.yaml"
            )

        user_prompt = user_prompt_template.format(
            topic=rephrase_result.get("topic", ""), user_feedback=user_feedback
        )

        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            stage="check_satisfaction",
            verbose=False,
        )

        # Parse JSON output
        data = extract_json_from_text(response)
        from ..utils.json_utils import ensure_json_dict, ensure_keys

        try:
            result = ensure_json_dict(data)
            ensure_keys(result, ["user_satisfied", "should_continue", "interpretation"])
        except Exception:
            # Fallback: judge based on keywords
            feedback_lower = user_feedback.lower()
            satisfied_keywords = ["ok", "yes", "satisfied", "good", "fine", "agree", "approved"]
            continue_keywords = [
                "modify",
                "change",
                "adjust",
                "no",
                "need",
                "want",
                "should",
                "hope",
            ]

            user_satisfied = any(kw in feedback_lower for kw in satisfied_keywords) and not any(
                kw in feedback_lower for kw in continue_keywords
            )

            result = {
                "user_satisfied": user_satisfied,
                "should_continue": not user_satisfied,
                "interpretation": "Judged based on keywords",
                "suggested_action": (
                    "Continue rephrasing" if not user_satisfied else "Proceed to next stage"
                ),
            }

        print("\n📊 Judgment Result:")
        print(f"  User Satisfied: {'Yes' if result.get('user_satisfied') else 'No'}")
        print(f"  Continue Rephrasing: {'Yes' if result.get('should_continue') else 'No'}")
        print(f"  Intent Interpretation: {result.get('interpretation', '')}")

        return result


__all__ = ["RephraseAgent"]
