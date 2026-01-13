#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DR-in-KG 2.0 Utils - Lightweight initialization
Only exports tools used by the current version.
"""

from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import from unified logging system
from src.logging import Logger, get_logger

from .json_utils import (
    ensure_json_dict,
    ensure_json_list,
    ensure_keys,
    extract_json_from_text,
    json_to_text,
    safe_json_loads,
)
from .token_tracker import TokenTracker, get_token_tracker

# Backwards compatibility: LLMLogger is now just Logger
LLMLogger = Logger


def get_llm_logger(research_id: str = None, log_dir: str = None, agent_name: str = None):
    """Get logger for LLM calls (backwards compatibility)"""
    name = agent_name or "Research"
    return get_logger(name, log_dir=log_dir)


def reset_llm_logger():
    """Reset LLM logger (backwards compatibility)"""
    from src.logging import reset_logger

    reset_logger()


__all__ = [
    "extract_json_from_text",
    "ensure_json_dict",
    "ensure_json_list",
    "ensure_keys",
    "safe_json_loads",
    "json_to_text",
    "get_token_tracker",
    "TokenTracker",
    "LLMLogger",
    "get_llm_logger",
    "reset_llm_logger",
    "Logger",
    "get_logger",
]
