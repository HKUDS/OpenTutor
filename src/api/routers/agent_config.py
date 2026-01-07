#!/usr/bin/env python
"""
Agent Configuration API - Provides agent metadata for data-driven UI.
"""

from fastapi import APIRouter

router = APIRouter()

# Agent registry - single source of truth for agent UI metadata
AGENT_REGISTRY = {
    "solve": {
        "icon": "HelpCircle",
        "color": "blue",
        "label_key": "Problem Solved",
    },
    "question": {
        "icon": "FileText",
        "color": "purple",
        "label_key": "Question Generated",
    },
    "research": {
        "icon": "Search",
        "color": "emerald",
        "label_key": "Research Report",
    },
    "co_writer": {
        "icon": "PenTool",
        "color": "amber",
        "label_key": "Co-Writer",
    },
    "guide": {
        "icon": "BookOpen",
        "color": "indigo",
        "label_key": "Guided Learning",
    },
    "ideagen": {
        "icon": "Lightbulb",
        "color": "yellow",
        "label_key": "Idea Generated",
    },
}


@router.get("/agents")
async def get_agent_config():
    """
    Get agent UI configuration.

    Returns:
        Dict mapping agent type to UI metadata (icon, color, label_key)
    """
    return AGENT_REGISTRY


@router.get("/agents/{agent_type}")
async def get_single_agent_config(agent_type: str):
    """
    Get UI configuration for a specific agent.

    Args:
        agent_type: Agent type (solve, question, research, etc.)

    Returns:
        Agent UI metadata or 404 if not found
    """
    if agent_type in AGENT_REGISTRY:
        return AGENT_REGISTRY[agent_type]
    return {"error": f"Agent type '{agent_type}' not found"}
