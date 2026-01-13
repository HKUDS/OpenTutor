#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SummaryAgent - Learning Summary Generation Agent
Generates personalized learning summary reports after users complete learning
"""

from typing import Any

from src.agents.base_agent import BaseAgent


class SummaryAgent(BaseAgent):
    """Learning summary agent"""

    def __init__(self, api_key: str, base_url: str, language: str = "zh", binding: str = "openai"):
        super().__init__(
            module_name="guide",
            agent_name="summary_agent",
            api_key=api_key,
            base_url=base_url,
            language=language,
        )

    def _format_knowledge_points(self, points: list[dict[str, Any]]) -> str:
        """Format knowledge point list"""
        formatted = []
        for i, point in enumerate(points, 1):
            formatted.append(
                f"""
### Knowledge Point {i}: {point.get("knowledge_title", "Unnamed")}
**Content Summary**: {point.get("knowledge_summary", "")}
**Potential Difficulty**: {point.get("user_difficulty", "")}
"""
            )
        return "\n".join(formatted)

    def _format_chat_history(self, history: list[dict[str, str]]) -> str:
        """Format complete chat history"""
        if not history:
            return "(User did not ask questions during learning)"

        formatted = []
        current_knowledge = None

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            knowledge_index = msg.get("knowledge_index")

            if knowledge_index is not None and knowledge_index != current_knowledge:
                current_knowledge = knowledge_index
                formatted.append(
                    f"\n--- During learning knowledge point {knowledge_index + 1} ---\n"
                )

            if role == "user":
                formatted.append(f"**User Question**: {content}")
            elif role == "assistant":
                formatted.append(f"**Assistant Answer**: {content}")
            elif role == "system":
                formatted.append(f"_System Message: {content}_")

        return "\n\n".join(formatted)

    async def process(
        self,
        notebook_name: str,
        knowledge_points: list[dict[str, Any]],
        chat_history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Generate learning summary report

        Args:
            notebook_name: Notebook name
            knowledge_points: All knowledge point list
            chat_history: Complete chat history

        Returns:
            Dictionary containing summary report
        """
        system_prompt = self.get_prompt("system")
        if not system_prompt:
            raise ValueError(
                "SummaryAgent missing system prompt, please configure system in prompts/{lang}/summary_agent.yaml"
            )

        user_template = self.get_prompt("user_template")
        if not user_template:
            raise ValueError(
                "SummaryAgent missing user_template, please configure user_template in prompts/{lang}/summary_agent.yaml"
            )

        formatted_points = self._format_knowledge_points(knowledge_points)
        formatted_history = self._format_chat_history(chat_history)

        user_prompt = user_template.format(
            notebook_name=notebook_name,
            total_points=len(knowledge_points),
            all_knowledge_points=formatted_points,
            full_chat_history=formatted_history,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )

            cleaned_summary = response.strip()

            import re

            markdown_pattern = r"```(?:markdown)?\s*([\s\S]*?)\s*```"
            match = re.search(markdown_pattern, cleaned_summary)
            if match:
                cleaned_summary = match.group(1).strip()

            return {
                "success": True,
                "summary": cleaned_summary,
                "notebook_name": notebook_name,
                "total_points": len(knowledge_points),
                "total_interactions": len([m for m in chat_history if m.get("role") == "user"]),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"""# 📊 Learning Summary

Congratulations on completing learning **{notebook_name}**!

## Learning Overview
- Learned {len(knowledge_points)} knowledge points
- Had {len([m for m in chat_history if m.get("role") == "user"])} interactions during learning

Thank you for your hard work! Keep up this learning enthusiasm! 🎉
""",
            }
