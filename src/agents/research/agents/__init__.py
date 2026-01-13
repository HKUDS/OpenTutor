#!/usr/bin/env python
"""
DR-in-KG 2.0 Agents Module
"""

from src.agents.base_agent import BaseAgent

from .decompose_agent import DecomposeAgent
from .manager_agent import ManagerAgent
from .note_agent import NoteAgent
from .rephrase_agent import RephraseAgent
from .reporting_agent import ReportingAgent
from .research_agent import ResearchAgent

__all__ = [
    "BaseAgent",
    "DecomposeAgent",
    "ManagerAgent",
    "NoteAgent",
    "RephraseAgent",
    "ReportingAgent",
    "ResearchAgent",
]
