# -*- coding: utf-8 -*-
"""
LLM Parameter Sanitization
==========================

Centralized parameter sanitization for LLM API calls.
Handles model-specific constraints, temperature strategies, and token limits.

Usage:
    from src.services.llm.parameters import sanitize_model_params

    params = sanitize_model_params("openai", "o1-preview", {
        "temperature": 0.5,
        "max_tokens": 2048,
    })
    # Returns: {"temperature": 1.0, "max_completion_tokens": 2048}
"""

import re
from typing import Any, Optional

# Default maximum tokens when not specified
DEFAULT_MAX_TOKENS = 4096


# =============================================================================
# Model Constraints Configuration
# =============================================================================

# Temperature strategies:
#   - "fixed": Replace user temperature with a fixed value (e.g., o1 -> 1.0)
#   - "drop": Remove temperature key entirely (model doesn't accept it)
#   - None: Allow user-specified temperature (default behavior)

MODEL_CONSTRAINTS: dict[str, dict[str, Any]] = {
    # OpenAI reasoning models - require temperature=1.0
    "o1": {
        "temperature_strategy": "fixed",
        "fixed_temperature": 1.0,
        "uses_max_completion_tokens": True,
    },
    "o1-preview": {
        "temperature_strategy": "fixed",
        "fixed_temperature": 1.0,
        "uses_max_completion_tokens": True,
    },
    "o1-mini": {
        "temperature_strategy": "fixed",
        "fixed_temperature": 1.0,
        "uses_max_completion_tokens": True,
    },
    # GPT-4o series - uses max_completion_tokens
    "gpt-4o": {
        "uses_max_completion_tokens": True,
    },
    "gpt-4o-mini": {
        "uses_max_completion_tokens": True,
    },
}


def get_model_constraint(
    model: str,
    constraint: str,
    default: Any = None,
) -> Any:
    """
    Get a constraint value for a specific model.

    Args:
        model: Model name
        constraint: Constraint key (e.g., "temperature_strategy", "fixed_temperature")
        default: Default value if constraint not defined

    Returns:
        Constraint value or default
    """
    if not model:
        return default

    model_lower = model.lower()

    # Check exact match first, then prefix match
    # Sort by length descending for most specific match first
    for pattern in sorted(MODEL_CONSTRAINTS.keys(), key=len, reverse=True):
        if model_lower == pattern or model_lower.startswith(pattern):
            constraints = MODEL_CONSTRAINTS[pattern]
            if constraint in constraints:
                return constraints[constraint]

    return default


def uses_max_completion_tokens(model: str) -> bool:
    """
    Check if the model uses max_completion_tokens instead of max_tokens.

    Newer OpenAI models (o1, gpt-4o, etc.) require max_completion_tokens
    while older models use max_tokens.

    Args:
        model: The model name

    Returns:
        True if the model requires max_completion_tokens
    """
    # First check MODEL_CONSTRAINTS
    if get_model_constraint(model, "uses_max_completion_tokens"):
        return True

    if not model:
        return False

    model_lower = model.lower()

    # Fallback patterns for models not in constraints
    patterns = [
        r"^o[13]",  # o1, o3 models
        r"^gpt-4o",  # gpt-4o models
        r"^gpt-[5-9]",  # gpt-5.x and later
        r"^gpt-\d{2,}",  # gpt-10+ (future proofing)
    ]

    for pattern in patterns:
        if re.match(pattern, model_lower):
            return True

    return False


def get_token_limit_kwargs(model: str, max_tokens: Optional[int] = None) -> dict:
    """
    Get the appropriate token limit parameter for the model.

    Args:
        model: The model name
        max_tokens: The desired token limit (uses DEFAULT_MAX_TOKENS if None)

    Returns:
        Dictionary with either {"max_tokens": value} or {"max_completion_tokens": value}
    """
    tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS

    if uses_max_completion_tokens(model):
        return {"max_completion_tokens": tokens}
    return {"max_tokens": tokens}


def sanitize_model_params(
    binding: str,
    model: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """
    Sanitize and transform model parameters based on model constraints.

    This centralizes all parameter transformation logic:
    - Temperature handling (fixed value, drop, or pass-through)
    - Token limit key resolution (max_tokens vs max_completion_tokens)
    - Removes unsupported parameters

    Args:
        binding: Provider binding name (e.g., "openai", "anthropic")
        model: Model name (e.g., "o1-preview", "gpt-4o")
        kwargs: Raw parameters from caller

    Returns:
        Sanitized parameter dictionary ready for API call
    """
    result = {}

    # 1. Handle temperature based on strategy
    temp_strategy = get_model_constraint(model, "temperature_strategy")

    if temp_strategy == "fixed":
        # Use the model's fixed temperature value
        fixed_temp = get_model_constraint(model, "fixed_temperature", 1.0)
        result["temperature"] = fixed_temp
    elif temp_strategy == "drop":
        # Don't include temperature at all
        pass
    else:
        # Default: use user-provided temperature or default
        result["temperature"] = kwargs.get("temperature", 0.7)

    # 2. Handle max_tokens / max_completion_tokens
    max_tokens = kwargs.get("max_tokens") or kwargs.get("max_completion_tokens")
    token_kwargs = get_token_limit_kwargs(model, max_tokens)
    result.update(token_kwargs)

    # 3. Pass through other supported parameters
    supported_params = [
        "response_format",
        "tools",
        "tool_choice",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "seed",
        "logprobs",
        "top_logprobs",
        "n",
    ]

    for param in supported_params:
        if param in kwargs:
            result[param] = kwargs[param]

    return result


__all__ = [
    "DEFAULT_MAX_TOKENS",
    "MODEL_CONSTRAINTS",
    "get_model_constraint",
    "uses_max_completion_tokens",
    "get_token_limit_kwargs",
    "sanitize_model_params",
]
