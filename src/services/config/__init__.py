"""
Configuration Service
=====================

Unified configuration loading for all DeepTutor modules.

Usage:
    from src.services.config import load_config_with_main, PROJECT_ROOT

    # Load module configuration
    config = load_config_with_main("solve_config.yaml")

    # Get agent parameters
    params = get_agent_params("guide")
"""

from .loader import (
    PROJECT_ROOT,
    _deep_merge,
    get_agent_params,
    get_path_from_config,
    load_config_with_main,
    parse_language,
)

__all__ = [
    "PROJECT_ROOT",
    "load_config_with_main",
    "get_path_from_config",
    "parse_language",
    "get_agent_params",
    "_deep_merge",
]
