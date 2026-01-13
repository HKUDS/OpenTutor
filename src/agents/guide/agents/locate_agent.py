#!/usr/bin/env python
"""
LocateAgent - Agent for locating and organizing knowledge points
Analyzes notebook content and generates progressive knowledge point learning plans
"""

import json
from typing import Any

from src.agents.base_agent import BaseAgent


class LocateAgent(BaseAgent):
    """Knowledge point location agent"""

    def __init__(self, api_key: str, base_url: str, language: str = "zh", binding: str = "openai"):
        super().__init__(
            module_name="guide",
            agent_name="locate_agent",
            api_key=api_key,
            base_url=base_url,
            language=language,
        )

    def _format_records(self, records: list[dict[str, Any]]) -> str:
        """Format notebook records as readable text"""
        formatted = []
        for i, record in enumerate(records, 1):
            record_type = record.get("type", "unknown")
            title = record.get("title", "Untitled")
            user_query = record.get("user_query", "")
            output = record.get("output", "")

            if len(output) > 2000:
                output = output[:2000] + "\n...[Content truncated]..."

            formatted.append(
                f"""
### Record {i} [{record_type.upper()}]
**Title**: {title}

**User Question/Input**:
{user_query}

**System Output**:
{output}
---"""
            )

        return "\n".join(formatted)

    async def process(
        self, notebook_id: str, notebook_name: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze notebook content and generate knowledge point learning plan

        Args:
            notebook_id: Notebook ID
            notebook_name: Notebook name
            records: List of records in notebook

        Returns:
            Dictionary containing knowledge point list
        """
        if not records:
            return {"success": False, "error": "No records in notebook", "knowledge_points": []}

        system_prompt = self.get_prompt("system")
        if not system_prompt:
            raise ValueError(
                "LocateAgent missing system prompt, please configure system in prompts/{lang}/locate_agent.yaml"
            )

        user_template = self.get_prompt("user_template")
        if not user_template:
            raise ValueError(
                "LocateAgent missing user_template, please configure user_template in prompts/{lang}/locate_agent.yaml"
            )

        records_content = self._format_records(records)

        user_prompt = user_template.format(
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            record_count=len(records),
            records_content=records_content,
        )

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )

            try:
                result = json.loads(response)

                if isinstance(result, list):
                    knowledge_points = result
                elif isinstance(result, dict):
                    knowledge_points = (
                        result.get("knowledge_points")
                        or result.get("points")
                        or result.get("data")
                        or []
                    )
                else:
                    knowledge_points = []

                validated_points = []
                for point in knowledge_points:
                    if isinstance(point, dict):
                        validated_points.append(
                            {
                                "knowledge_title": point.get(
                                    "knowledge_title", "Unnamed knowledge point"
                                ),
                                "knowledge_summary": point.get("knowledge_summary", ""),
                                "user_difficulty": point.get("user_difficulty", ""),
                            }
                        )

                return {
                    "success": True,
                    "knowledge_points": validated_points,
                    "total_points": len(validated_points),
                }

            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"JSON parsing failed: {e!s}",
                    "raw_response": response,
                    "knowledge_points": [],
                }

        except Exception as e:
            return {"success": False, "error": str(e), "knowledge_points": []}
