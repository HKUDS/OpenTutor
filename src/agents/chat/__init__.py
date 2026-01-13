"""
Chat Module - Lightweight conversational AI with session management.

This module provides:
- ChatAgent: Multi-turn conversational agent with RAG/Web Search support
- SessionManager: Chat session persistence and management

Usage:
    from src.agents.chat import ChatAgent, SessionManager

    agent = ChatAgent(language="en")
    response = await agent.process(
        message="What is machine learning?",
        history=[],
        kb_name="ai_textbook",
        enable_rag=True,
        enable_web_search=False
    )
"""

from .chat_agent import ChatAgent
from .session_manager import SessionManager

__all__ = ["ChatAgent", "SessionManager"]
