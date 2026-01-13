#!/usr/bin/env python
"""
ChatAgent - Q&A Agent during learning process
Answers user questions while learning specific knowledge points
"""

from typing import Any

from src.agents.base_agent import BaseAgent


class ChatAgent(BaseAgent):
    """Learning Q&A agent"""

    def __init__(self, api_key: str, base_url: str, language: str = "zh", binding: str = "openai"):
        super().__init__(
            module_name="guide",
            agent_name="chat_agent",
            api_key=api_key,
            base_url=base_url,
            language=language,
        )

    def _format_chat_history(self, history: list[dict[str, str]]) -> str:
        """Format chat history"""
        if not history:
            return "(No chat history)"

        formatted = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                formatted.append(f"**User**: {content}")
            elif role == "assistant":
                formatted.append(f"**Assistant**: {content}")
            elif role == "system":
                formatted.append(f"_System: {content}_")

        return "\n\n".join(formatted)

    async def process(
        self, knowledge: dict[str, Any], chat_history: list[dict[str, str]], user_question: str
    ) -> dict[str, Any]:
        """
        Answer user questions about current knowledge point

        Args:
            knowledge: Current knowledge point information
            chat_history: Chat history
            user_question: User question

        Returns:
            Dictionary containing answer
        """
        if not user_question.strip():
            return {"success": False, "error": "Question cannot be empty", "answer": ""}

        system_prompt = self.get_prompt("system")
        if not system_prompt:
            raise ValueError(
                "ChatAgent missing system prompt, please configure system in prompts/{lang}/chat_agent.yaml"
            )

        user_template = self.get_prompt("user_template")
        if not user_template:
            raise ValueError(
                "ChatAgent missing user_template, please configure user_template in prompts/{lang}/chat_agent.yaml"
            )

        formatted_history = self._format_chat_history(chat_history)

        user_prompt = user_template.format(
            knowledge_title=knowledge.get("knowledge_title", ""),
            knowledge_summary=knowledge.get("knowledge_summary", ""),
            user_difficulty=knowledge.get("user_difficulty", ""),
            chat_history=formatted_history,
            user_question=user_question,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )

            return {"success": True, "answer": response.strip()}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "answer": "Sorry, an error occurred while answering the question. Please try again later.",
            }
