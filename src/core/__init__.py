#!/usr/bin/env python
"""
Core module - provides unified configuration, logging, and prompt management.
"""

from .core import (
    PROJECT_ROOT,
    get_agent_params,
    get_embedding_config,
    get_llm_config,
    get_path_from_config,
    get_tts_config,
    load_config_with_main,
    parse_language,
)
from .prompt_manager import PromptManager, get_prompt_manager

__all__ = [
    # Project root
    "PROJECT_ROOT",
    # Environment configuration
    "get_llm_config",
    "get_embedding_config",
    "get_tts_config",
    # Agent parameters
    "get_agent_params",
    # YAML configuration
    "load_config_with_main",
    "get_path_from_config",
    # Language utilities
    "parse_language",
    # Prompt management
    "PromptManager",
    "get_prompt_manager",
]
