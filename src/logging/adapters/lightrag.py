#!/usr/bin/env python
"""
LightRAG Log Forwarder
======================

Forwards LightRAG and RAG-Anything logs to DeepTutor's unified logging system.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Optional


class LightRAGLogForwarder(logging.Handler):
    """
    Handler that forwards LightRAG logger messages to DeepTutor logger.
    """

    def __init__(self, ai_tutor_logger, add_prefix: bool = True):
        """
        Args:
            ai_tutor_logger: DeepTutor Logger instance
            add_prefix: Whether to add [LightRAG] prefix to messages
        """
        super().__init__()
        self.ai_tutor_logger = ai_tutor_logger
        self.add_prefix = add_prefix
        # Capture all log levels
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord):
        """
        Forward log record to DeepTutor logger.
        All logs are forwarded as info level to maintain consistent format.
        """
        try:
            # Get the original message directly without adding [LightRAG] prefix
            # LightRAG already formats messages appropriately (e.g., "DEBUG: xxx" for debug logs)
            message = record.getMessage()

            # Use info() for all levels to maintain consistent format
            # This ensures all logs appear as [RAGTool] ... (or [RAGTool] DEBUG: ... for debug)
            self.ai_tutor_logger.info(message)

        except Exception:
            # Avoid errors in forwarding from affecting main flow
            self.handleError(record)


def get_lightrag_forwarding_config() -> dict:
    """
    Load LightRAG forwarding configuration from main.yaml.

    Returns:
        dict: Configuration dictionary with defaults if not found
    """
    try:
        from src.services.config import load_config_with_main

        # Use resolve() to get absolute path, ensuring correct project root regardless of working directory
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        config = load_config_with_main("solve_config.yaml", project_root)

        forwarding_config = config.get("logging", {}).get("lightrag_forwarding", {})

        return {
            "enabled": forwarding_config.get("enabled", True),
            "min_level": forwarding_config.get("min_level", "INFO"),
            "add_prefix": forwarding_config.get("add_prefix", True),
            "logger_names": forwarding_config.get(
                "logger_names", {"knowledge_init": "KnowledgeInit", "rag_tool": "RAGTool"}
            ),
        }
    except Exception:
        # Return defaults if config loading fails
        return {
            "enabled": True,
            "min_level": "INFO",
            "add_prefix": True,
            "logger_names": {"knowledge_init": "KnowledgeInit", "rag_tool": "RAGTool"},
        }


@contextmanager
def LightRAGLogContext(logger_name: Optional[str] = None, scene: Optional[str] = None):
    """
    Context manager for LightRAG log forwarding.

    Automatically sets up and tears down log forwarding.

    Args:
        logger_name: Explicit logger name (overrides scene-based lookup)
        scene: Scene name ('knowledge_init' or 'rag_tool') for logger name lookup

    Usage:
        with LightRAGLogContext("RAGTool"):
            # RAG operations
            rag = RAGAnything(...)
    """
    from ..logger import get_logger

    # Get configuration
    config = get_lightrag_forwarding_config()

    # Check if forwarding is enabled
    if not config.get("enabled", True):
        # If disabled, just pass through without forwarding
        yield
        return

    # Debug: Log that forwarding is being set up (only if we have a logger)
    # This helps verify the context manager is being called
    try:
        debug_logger = get_logger("RAGForward")
        debug_logger.debug(
            f"Setting up LightRAG log forwarding (scene={scene}, logger_name={logger_name})"
        )
    except:
        pass  # Ignore if logger setup fails

    # Determine logger name
    if logger_name is None:
        if scene:
            logger_names = config.get("logger_names", {})
            logger_name = logger_names.get(scene, "Main")
        else:
            logger_name = "Main"

    # Get DeepTutor logger
    ai_tutor_logger = get_logger(logger_name)

    # Get forwarding settings
    add_prefix = config.get("add_prefix", True)
    min_level_str = config.get("min_level", "INFO")
    min_level = getattr(logging, min_level_str.upper(), logging.INFO)

    # Get LightRAG logger
    lightrag_logger = logging.getLogger("lightrag")

    # Store original handlers and level to restore later if needed
    original_handlers = lightrag_logger.handlers[:]  # Copy list
    original_level = lightrag_logger.level

    # Temporarily remove existing console handlers to avoid duplicate output
    # We'll forward all logs through our handler instead
    console_handlers_to_remove = []
    for handler in original_handlers:
        if isinstance(handler, logging.StreamHandler):
            console_handlers_to_remove.append(handler)

    for handler in console_handlers_to_remove:
        lightrag_logger.removeHandler(handler)

    # Ensure LightRAG logger level is set low enough to capture all logs
    # The logger level controls which logs are created, handler level controls which are processed
    # Set to DEBUG to ensure we capture everything, then filter at handler level
    if lightrag_logger.level > logging.DEBUG:
        lightrag_logger.setLevel(logging.DEBUG)

    # Create and add forwarder
    forwarder = LightRAGLogForwarder(ai_tutor_logger, add_prefix=add_prefix)
    forwarder.setLevel(min_level)
    lightrag_logger.addHandler(forwarder)

    # Test that forwarding works by sending a test log
    try:
        test_msg = "LightRAG log forwarding enabled"
        lightrag_logger.info(test_msg)
    except:
        pass  # Ignore test log errors

    try:
        yield
    finally:
        # Clean up: remove our forwarder
        if forwarder in lightrag_logger.handlers:
            lightrag_logger.removeHandler(forwarder)
            forwarder.close()

        # Restore original console handlers if they were removed
        for handler in console_handlers_to_remove:
            if handler not in lightrag_logger.handlers:
                lightrag_logger.addHandler(handler)
