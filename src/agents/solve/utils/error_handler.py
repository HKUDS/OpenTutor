#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Error Handler - Error handling and retry mechanism
"""

import asyncio
from collections.abc import Callable
import functools
from typing import Any


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

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except ParseError as e:
                    if attempt == max_retries:
                        # Last attempt failed, raise exception
                        raise e

                    # Wait and retry
                    print(
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
    parser_func: Callable, text: str, default: Any = None, raise_on_error: bool = False
) -> Any:
    """
    Safe parsing (catch exceptions and return default value)

    Args:
        parser_func: Parser function
        text: Text to parse
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

        print(f"⚠️ Parsing failed, using default value: {e!s}")
        return default


def validate_investigate_output(output: dict[str, Any]) -> bool:
    """Validate InvestigateAgent output (refactored: multi-tool intent)"""
    required_fields = ["reasoning", "tools"]
    field_types = {"reasoning": str, "tools": list}

    validate_output(output, required_fields, field_types)

    valid_tools = ["rag_naive", "rag_hybrid", "web_search", "query_item", "none"]
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
            if len(tools) > 1:
                raise ParseError(
                    "When [TOOL] none exists, no other tool intents should be provided"
                )
            continue

        if not query:
            raise ParseError(f"tool[{idx}] missing query")

        if tool_type == "query_item" and not (identifier or query):
            raise ParseError("query_item must provide identifier or query")

    return True


def validate_note_output(output: dict[str, Any]) -> bool:
    """Validate NoteAgent output (new format: only summary and citations)"""
    required_fields = ["summary"]
    field_types = {"summary": str, "citations": list}

    validate_output(output, required_fields, field_types)

    # Validate citations list
    if "citations" in output:
        for citation in output["citations"]:
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


def validate_plan_output(output: dict[str, Any]) -> bool:
    """Validate PlanAgent output"""
    required_fields = ["answer_style", "blocks"]
    field_types = {"answer_style": str, "blocks": list}

    validate_output(output, required_fields, field_types)

    # Validate blocks list is not empty (new)
    if not output["blocks"] or len(output["blocks"]) == 0:
        raise ParseError(
            "blocks list is empty, PlanAgent must generate at least one block.\n"
            "Possible reasons:\n"
            "1. LLM did not output [Block-N] tags\n"
            "2. Output format is incorrect\n"
            "3. Prompt design has issues"
        )

    # Validate blocks list
    for block in output["blocks"]:
        if not isinstance(block, dict):
            raise ParseError(f"block must be a dictionary, got: {type(block)}")

        if "block_id" not in block or "format" not in block or "steps" not in block:
            raise ParseError("block missing required fields: block_id, format, steps")

        # Validate steps list
        for step in block["steps"]:
            if not isinstance(step, dict):
                raise ParseError(f"step must be a dictionary, got: {type(step)}")

            if "step_id" not in step or "plan" not in step:
                raise ParseError("step missing required fields: step_id, plan")

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
    test_invalid_output = {"actions": []}

    try:
        validate_investigate_output(test_invalid_output)
        print("✓ Invalid output validation passed (should not happen)")
    except ParseError as e:
        print(f"✗ Invalid output validation failed (expected): {e}")
