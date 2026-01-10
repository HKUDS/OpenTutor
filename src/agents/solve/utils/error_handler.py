#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Error Handler - Error handling and retry mechanism
"""

import asyncio
from collections.abc import Callable
import functools
import logging
from typing import Any
import warnings

logger = logging.getLogger("Solver.error_handler")

# Lazy-load valid tools configuration to avoid I/O at module import time
_DEFAULT_VALID_TOOLS = ["rag_naive", "rag_hybrid", "web_search", "query_item", "none"]


class _LazyValidTools:
    """
    Lazily resolves the list of valid tools on first use.

    This avoids performing configuration I/O at module import time while
    preserving list-like behavior for existing callers.
    """

    def __init__(self, default_tools: list[str]):
        self._default_tools = list(default_tools)  # Create a copy to prevent mutation
        self._tools: list[str] | None = None
        self._lock = asyncio.Lock()

    async def get_tools(self) -> list[str]:
        # Double-check locking pattern for async
        if self._tools is not None:
            return self._tools

        async with self._lock:
            # Check again in case another task initialized it while we waited
            if self._tools is not None:
                return self._tools

            # Perform initialization
            try:
                from src.services.config import (
                    PROJECT_ROOT,
                    load_config_with_main,
                )

                config = load_config_with_main("main.yaml", PROJECT_ROOT)
                self._tools = config.get("solve", {}).get("valid_tools", self._default_tools)
            except (ImportError, FileNotFoundError, OSError, KeyError) as exc:
                logger.warning(
                    "Failed to load valid_tools from config (%s). Using defaults. "
                    "Ensure the config file exists and contains solve.valid_tools. Original error: %s",
                    type(exc).__name__,
                    exc,
                )
                self._tools = self._default_tools
            return self._tools

    def _load(self) -> list[str]:
        # DEPRECATED: This method is deprecated and may cause thread-safety issues.
        # It no longer attempts to load from config to avoid race conditions.
        # Use get_tools() instead for async-safe access.
        warnings.warn(
            "_load() is deprecated and no longer loads from config. "
            "Use get_tools() instead for async-safe access.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Return already loaded tools or defaults - no config loading to avoid race conditions
        return self._tools if self._tools is not None else self._default_tools

    def __iter__(self):
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, return defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return iter(tools)

    def __contains__(self, item: object) -> bool:
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, check defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return item in tools

    def __len__(self) -> int:
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, return length of defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return len(tools)

    def __getitem__(self, index):
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, index into defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return tools[index]

    def __bool__(self) -> bool:
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, evaluate truthiness of defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return bool(tools)

    def __repr__(self) -> str:
        # Avoid calling _load() to prevent race conditions with async get_tools()
        # If tools haven't been loaded yet, represent defaults
        tools = self._tools if self._tools is not None else self._default_tools
        return repr(tools)


_VALID_TOOLS_CONFIG = _LazyValidTools(_DEFAULT_VALID_TOOLS)


class ParseError(Exception):
    """Parse error"""


def retry_on_parse_error(max_retries: int = 2, delay: float = 1.0, backoff: float = 2.0):
    """
    Parse error retry decorator

    Args:
        max_retries: Maximum retry count
        delay: Initial delay time (seconds)
        backoff: Delay multiplier factor
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except ParseError as e:
                    if attempt == max_retries:
                        # Last attempt failed, raise exception
                        raise e

                    # Wait and retry
                    logger.warning(
                        f"⚠️ Parse failed (attempt {attempt + 1}), retrying in {current_delay:.1f}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # Should not reach here
            raise ParseError("Retry attempts exhausted")

        return wrapper

    return decorator


def validate_output(
    output: dict[str, Any], required_fields: list, field_types: dict[str, type] | None = None
) -> bool:
    """
    Validate output contains required fields and correct types

    Args:
        output: Output dictionary
        required_fields: List of required fields
        field_types: Field type dictionary (optional)

    Returns:
        bool: Whether valid

    Raises:
        ParseError: Raised when validation fails
    """
    # Check required fields
    missing_fields = [field for field in required_fields if field not in output]

    if missing_fields:
        raise ParseError(f"Missing required fields: {', '.join(missing_fields)}")

    # Check field types
    if field_types:
        for field, expected_type in field_types.items():
            if field in output and not isinstance(output[field], expected_type):
                actual_type = type(output[field]).__name__
                expected_type_name = expected_type.__name__
                raise ParseError(
                    f"Field '{field}' type error: expected {expected_type_name}, got {actual_type}"
                )

    return True


def safe_parse(
    text: str, parser_func: Callable[[str], Any], default: Any = None, raise_on_error: bool = False
) -> Any:
    """
    Safely parse text using a parser function

    Args:
        text: Text to parse
        parser_func: Parser function
        default: Default value
        raise_on_error: Whether to raise exception on error

    Returns:
        Parsed result or default value
    """
    try:
        return parser_func(text)
    except Exception as e:
        if raise_on_error:
            raise ParseError(f"Parsing failed: {e!s}")

        logger.warning(f"⚠️ Parsing failed, using default value: {e!s}")
        return default


async def validate_investigate_output(
    output: dict[str, Any],
    valid_tools: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Validate InvestigateAgent output (refactored: multi-tool intent)"""
    if valid_tools is None:
        if config is not None:
            # Use provided config
            valid_tools = config.get("solve", {}).get("valid_tools", _DEFAULT_VALID_TOOLS)
        else:
            # Fallback to lazy loading
            valid_tools = await _VALID_TOOLS_CONFIG.get_tools()

    required_fields = ["reasoning", "tools"]
    field_types = {"reasoning": str, "tools": list}

    validate_output(output, required_fields, field_types)

    tools = output["tools"]
    if not tools:
        raise ParseError("tools list cannot be empty")

    for idx, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise ParseError(f"tool[{idx}] must be a dictionary")

        tool_type = tool.get("tool_type", "").lower()
        query = tool.get("query", "")
        identifier = tool.get("identifier", "")

        if tool_type not in valid_tools:
            raise ParseError(
                f"tool[{idx}] tool_type must be one of {valid_tools}, got: {tool_type}"
            )

        if tool_type == "none":
            continue

        if not query:
            raise ParseError(f"tool[{idx}] missing query")

        if tool_type == "query_item" and not (identifier or query):
            raise ParseError("query_item must provide identifier or query")

    # Validate none tool constraint after all tools are validated as dictionaries
    validate_none_tool_constraint(tools, "tool_type")

    return True


def validate_note_output(output: dict[str, Any]) -> bool:
    """Validate NoteAgent output (new format: only summary and citations)"""
    required_fields = ["summary"]
    field_types = {"summary": str}

    # For backward compatibility, citations is optional (may be missing in older cached data)
    if "citations" in output:
        field_types["citations"] = list

    validate_output(output, required_fields, field_types)

    # Validate citations list if present
    if "citations" in output:
        citations = output["citations"]
        # validate_output already ensures citations is a list

        for citation in citations:
            if not isinstance(citation, dict):
                raise ParseError(f"citation must be a dictionary, got: {type(citation)}")

            # citations should contain reference_id, source, content
            if "reference_id" not in citation and "source" not in citation:
                raise ParseError("citation must contain reference_id or source")

    return True


def validate_reflect_output(output: dict[str, Any]) -> bool:
    """Validate InvestigateReflectAgent output (new format: simplified)"""
    required_fields = ["should_stop", "reason", "remaining_questions"]
    field_types = {"should_stop": bool, "reason": str, "remaining_questions": list}

    validate_output(output, required_fields, field_types)

    # Validate remaining_questions list
    if "remaining_questions" in output:
        for question in output["remaining_questions"]:
            if not isinstance(question, str):
                raise ParseError(f"remaining_question must be a string, got: {type(question)}")

    return True


def validate_none_tool_constraint(
    tools: list[dict[str, Any]], tool_type_key: str = "tool_type"
) -> None:
    """
    Validate that 'none' tool does not coexist with other tools.

    Args:
        tools: List of tool dictionaries
        tool_type_key: Key to access tool type in each dict (default: "tool_type")

    Raises:
        ParseError: If none tool constraint is violated
    """
    has_none = any(
        isinstance(tool.get(tool_type_key), str) and tool.get(tool_type_key).lower() == "none"
        for tool in tools
    )

    if has_none and len(tools) > 1:
        raise ParseError("When 'none' tool exists, no other tool intents should be provided")


async def validate_solve_output(
    output: dict[str, Any],
    valid_tools: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Validate SolveAgent output (tool plan format)"""
    if valid_tools is None:
        if config is not None:
            # Use provided config
            valid_tools = config.get("solve", {}).get("valid_tools", _DEFAULT_VALID_TOOLS)
        else:
            # Fallback to lazy loading
            valid_tools = await _VALID_TOOLS_CONFIG.get_tools()

    required_fields = ["tool_calls"]
    field_types = {"tool_calls": list}

    validate_output(output, required_fields, field_types)

    tool_calls = output["tool_calls"]
    has_terminating_call = any(
        call.get("type", "").lower() in ("none", "finish") for call in tool_calls
    )
    if has_terminating_call and len(tool_calls) > 1:
        # Check for terminating tools (none/finish) - they cannot coexist with other tools
        terminating_tools = [
            call for call in tool_calls if call.get("type", "").lower() in ("none", "finish")
        ]
        if terminating_tools and len(tool_calls) > 1:
            raise ParseError(
                "When terminating tools (none/finish) exist, no other tool calls should be provided"
            )

    # Track if we've seen a terminating tool for ordering validation
    has_terminating_tool = False

    for idx, tool_call in enumerate(tool_calls):
        if not isinstance(tool_call, dict):
            raise ParseError(f"tool_calls[{idx}] must be a dictionary")

        tool_type = tool_call.get("type", "").strip().lower()
        intent = tool_call.get("intent", "").strip()

        if not tool_type:
            raise ParseError(f"tool_calls[{idx}] missing type")

        if tool_type not in valid_tools:
            raise ParseError(
                f"tool_calls[{idx}] type must be one of {valid_tools}, got: {tool_type}"
            )

        # Check for terminating tools
        if tool_type in ("none", "finish"):
            if has_terminating_tool:
                raise ParseError(
                    f"tool_calls[{idx}] cannot have multiple terminating tools (none/finish)"
                )
            has_terminating_tool = True
        elif has_terminating_tool:
            raise ParseError(
                f"tool_calls[{idx}] cannot have non-terminating tools after none/finish"
            )

        # All tools except "none" need an intent
        if tool_type != "none" and not intent:
            raise ParseError(f"tool_calls[{idx}] missing intent for {tool_type}")

    return True


# Example usage
if __name__ == "__main__":
    # Test validation functions
    test_investigate_output = {
        "investigation_summary": "This round investigation target...",
        "actions": [
            {"type": "rag_naive", "query": "What is linear convolution?", "priority": "high"}
        ],
        "followup_suggestions": "If definition is unclear..",
    }

    try:
        validate_investigate_output(test_investigate_output)
        print("✓ InvestigateAgent output validation passed")
    except ParseError as e:
        print(f"✗ InvestigateAgent output validation failed: {e}")

    # Test missing required fields
    test_invalid_output = {"tools": []}

    try:
        validate_investigate_output(test_invalid_output)
        print("✓ Invalid output validation passed (should not happen)")
    except ParseError as e:
        print(f"✗ Invalid output validation failed (expected): {e}")
