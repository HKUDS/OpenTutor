#!/usr/bin/env python
"""
Utility Module
Contains logging, performance monitoring, config validation, parsers, etc.
"""

# Logging system (from unified logs module)
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.logging import Logger, LogLevel, get_logger, reset_logger

# Backwards compatibility alias
SolveAgentLogger = Logger

# Performance monitoring
# Config validation
from .config_validator import ConfigValidator
from .error_handler import (
    ParseError,
    retry_on_parse_error,
    validate_investigate_output,
    validate_note_output,
    validate_output,
    validate_plan_output,
    validate_reflect_output,
)
from .performance_monitor import PerformanceMonitor

# Token tracker
from .token_tracker import TokenTracker, calculate_cost, get_model_pricing

__all__ = [
    # Logging system
    "Logger",
    "get_logger",
    "reset_logger",
    "LogLevel",
    "SolveAgentLogger",  # Backwards compatibility
    # Performance monitoring
    "PerformanceMonitor",
    # Config validation
    "ConfigValidator",
    # Token tracker
    "TokenTracker",
    "calculate_cost",
    "get_model_pricing",
    # Error handling
    "ParseError",
    "retry_on_parse_error",
    "validate_output",
    "validate_investigate_output",
    "validate_note_output",
    "validate_reflect_output",
    "validate_plan_output",
]
