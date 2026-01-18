# -*- coding: utf-8 -*-
"""
Unit Tests for LLM Parameter Sanitization
==========================================

Table-driven tests for parameters.py to verify:
- Temperature strategy handling (fixed, drop, pass-through)
- Token limit key resolution (max_tokens vs max_completion_tokens)
- Various model constraints
"""

import pytest

from src.services.llm.parameters import (
    DEFAULT_MAX_TOKENS,
    MODEL_CONSTRAINTS,
    get_model_constraint,
    get_token_limit_kwargs,
    sanitize_model_params,
    uses_max_completion_tokens,
)

# =============================================================================
# Test get_model_constraint
# =============================================================================


class TestGetModelConstraint:
    """Tests for get_model_constraint function."""

    @pytest.mark.parametrize(
        "model,constraint,expected",
        [
            # Exact match
            ("o1", "temperature_strategy", "fixed"),
            ("o1", "fixed_temperature", 1.0),
            ("o1-preview", "temperature_strategy", "fixed"),
            ("o1-mini", "uses_max_completion_tokens", True),
            # Prefix match
            ("o1-2024-12-17", "temperature_strategy", "fixed"),
            ("gpt-4o-2024-08-06", "uses_max_completion_tokens", True),
            # No match - returns default
            ("gpt-4", "temperature_strategy", None),
            ("gpt-4-turbo", "uses_max_completion_tokens", None),
            ("claude-3-opus", "temperature_strategy", None),
        ],
    )
    def test_constraint_lookup(self, model, constraint, expected):
        """Test constraint lookup for various models."""
        result = get_model_constraint(model, constraint)
        assert result == expected

    def test_returns_default_for_unknown_model(self):
        """Unknown models should return the provided default."""
        assert get_model_constraint("unknown-model", "temperature_strategy", "default") == "default"

    def test_returns_none_for_none_model(self):
        """None model should return default."""
        assert get_model_constraint(None, "temperature_strategy") is None

    def test_case_insensitive_matching(self):
        """Model matching should be case-insensitive."""
        assert get_model_constraint("O1", "temperature_strategy") == "fixed"
        assert get_model_constraint("O1-PREVIEW", "fixed_temperature") == 1.0


# =============================================================================
# Test uses_max_completion_tokens
# =============================================================================


class TestUsesMaxCompletionTokens:
    """Tests for uses_max_completion_tokens function."""

    @pytest.mark.parametrize(
        "model,expected",
        [
            # Models in MODEL_CONSTRAINTS
            ("o1", True),
            ("o1-preview", True),
            ("o1-mini", True),
            ("gpt-4o", True),
            ("gpt-4o-mini", True),
            # Models matched by regex patterns
            ("o1-2024-12-17", True),
            ("gpt-4o-2024-08-06", True),
            ("gpt-5", True),  # Future proofing via regex
            ("gpt-5-turbo", True),
            ("gpt-10", True),
            # Models that use max_tokens (legacy)
            ("gpt-4", False),
            ("gpt-4-turbo", False),
            ("gpt-3.5-turbo", False),
            ("claude-3-opus", False),
            ("llama-3-70b", False),
        ],
    )
    def test_max_completion_tokens_detection(self, model, expected):
        """Test correct detection of models using max_completion_tokens."""
        assert uses_max_completion_tokens(model) == expected

    def test_empty_model_returns_false(self):
        """Empty or None model should return False."""
        assert uses_max_completion_tokens("") is False
        assert uses_max_completion_tokens(None) is False


# =============================================================================
# Test get_token_limit_kwargs
# =============================================================================


class TestGetTokenLimitKwargs:
    """Tests for get_token_limit_kwargs function."""

    @pytest.mark.parametrize(
        "model,max_tokens,expected_key",
        [
            ("o1", 2048, "max_completion_tokens"),
            ("o1-preview", 1000, "max_completion_tokens"),
            ("gpt-4o", 4096, "max_completion_tokens"),
            ("gpt-4", 4096, "max_tokens"),
            ("gpt-3.5-turbo", 2000, "max_tokens"),
            ("claude-3-opus", 4096, "max_tokens"),
        ],
    )
    def test_returns_correct_key(self, model, max_tokens, expected_key):
        """Test that correct token limit key is used."""
        result = get_token_limit_kwargs(model, max_tokens)
        assert expected_key in result
        assert result[expected_key] == max_tokens

    def test_uses_default_when_none(self):
        """Should use DEFAULT_MAX_TOKENS when max_tokens is None."""
        result = get_token_limit_kwargs("gpt-4", None)
        assert result["max_tokens"] == DEFAULT_MAX_TOKENS


# =============================================================================
# Test sanitize_model_params - Main Function
# =============================================================================


class TestSanitizeModelParams:
    """Tests for sanitize_model_params function."""

    @pytest.mark.parametrize(
        "binding,model,kwargs,expected_temp,expected_token_key",
        [
            # o1 models: fixed temperature, max_completion_tokens
            ("openai", "o1", {"temperature": 0.5}, 1.0, "max_completion_tokens"),
            ("openai", "o1-preview", {"temperature": 0.0}, 1.0, "max_completion_tokens"),
            (
                "openai",
                "o1-mini",
                {"temperature": 0.9, "max_tokens": 2048},
                1.0,
                "max_completion_tokens",
            ),
            # gpt-4o models: user temperature, max_completion_tokens
            ("openai", "gpt-4o", {"temperature": 0.3}, 0.3, "max_completion_tokens"),
            ("openai", "gpt-4o-mini", {}, 0.7, "max_completion_tokens"),  # default temp
            # Legacy models: user temperature, max_tokens
            ("openai", "gpt-4", {"temperature": 0.5}, 0.5, "max_tokens"),
            ("openai", "gpt-4-turbo", {"temperature": 0.8, "max_tokens": 1000}, 0.8, "max_tokens"),
            ("openai", "gpt-3.5-turbo", {}, 0.7, "max_tokens"),
            # Other providers
            ("anthropic", "claude-3-opus", {"temperature": 0.6}, 0.6, "max_tokens"),
            ("deepseek", "deepseek-chat", {"temperature": 0.4}, 0.4, "max_tokens"),
        ],
    )
    def test_parameter_sanitization(
        self, binding, model, kwargs, expected_temp, expected_token_key
    ):
        """Test parameter sanitization for various model configurations."""
        result = sanitize_model_params(binding, model, kwargs)

        # Check temperature
        assert result["temperature"] == expected_temp

        # Check token limit key
        assert expected_token_key in result

    def test_max_tokens_extraction(self):
        """Test that max_tokens is correctly extracted from kwargs."""
        result = sanitize_model_params("openai", "gpt-4", {"max_tokens": 2048})
        assert result["max_tokens"] == 2048

        result = sanitize_model_params("openai", "gpt-4", {"max_completion_tokens": 3000})
        assert result["max_tokens"] == 3000

    def test_default_max_tokens(self):
        """Test that DEFAULT_MAX_TOKENS is used when not specified."""
        result = sanitize_model_params("openai", "gpt-4", {})
        assert result["max_tokens"] == DEFAULT_MAX_TOKENS

    def test_response_format_passthrough(self):
        """Test that response_format is passed through."""
        result = sanitize_model_params(
            "openai", "gpt-4", {"response_format": {"type": "json_object"}}
        )
        assert result["response_format"] == {"type": "json_object"}

    def test_tools_passthrough(self):
        """Test that tools and tool_choice are passed through."""
        tools = [{"type": "function", "function": {"name": "test"}}]
        result = sanitize_model_params("openai", "gpt-4", {"tools": tools, "tool_choice": "auto"})
        assert result["tools"] == tools
        assert result["tool_choice"] == "auto"

    def test_unsupported_params_dropped(self):
        """Test that unsupported parameters are not included."""
        result = sanitize_model_params(
            "openai", "gpt-4", {"unsupported_param": "value", "another_bad": 123}
        )
        assert "unsupported_param" not in result
        assert "another_bad" not in result


# =============================================================================
# Test MODEL_CONSTRAINTS Configuration
# =============================================================================


class TestModelConstraintsConfiguration:
    """Tests for MODEL_CONSTRAINTS configuration validity."""

    def test_all_fixed_strategy_have_fixed_temperature(self):
        """Models with 'fixed' strategy must have fixed_temperature defined."""
        for model, constraints in MODEL_CONSTRAINTS.items():
            if constraints.get("temperature_strategy") == "fixed":
                assert "fixed_temperature" in constraints, f"{model} missing fixed_temperature"
                assert isinstance(constraints["fixed_temperature"], (int, float)), (
                    f"{model} fixed_temperature must be numeric"
                )

    def test_o1_models_have_correct_constraints(self):
        """Verify o1 model family has correct temperature and token constraints."""
        o1_models = ["o1", "o1-preview", "o1-mini"]
        for model in o1_models:
            assert model in MODEL_CONSTRAINTS, f"{model} missing from MODEL_CONSTRAINTS"
            assert MODEL_CONSTRAINTS[model]["temperature_strategy"] == "fixed"
            assert MODEL_CONSTRAINTS[model]["fixed_temperature"] == 1.0
            assert MODEL_CONSTRAINTS[model]["uses_max_completion_tokens"] is True
