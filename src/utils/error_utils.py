# -*- coding: utf-8 -*-
"""
Error handling utilities for parsing API exceptions.
"""

import json
import logging

# Optional imports for OpenAI errors
try:
    from openai import APIError, APIStatusError, RateLimitError
except ImportError:
    APIError = APIStatusError = RateLimitError = None

logger = logging.getLogger(__name__)


def format_exception_message(exc: Exception) -> str:
    """
    Build a human-friendly error message, preserving API details when available.

    Extracts detailed error messages from OpenAI/API exceptions, including
    JSON bodies and rate limit hints.
    """

    def append_unique_message(target: list[str], value: object):
        if not value:
            return
        text = str(value).strip()
        if not text:
            return
        if text not in target:
            target.append(text)

    messages: list[str] = []

    append_unique_message(messages, str(exc))
    # Some exceptions keep a separate message attribute
    message_attr = getattr(exc, "message", None)
    if message_attr is not None:
        append_unique_message(messages, message_attr)

    # OpenAI errors expose structured bodies with detailed messages
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error_payload = body.get("error") or body
        if isinstance(error_payload, dict):
            for key in ("message", "detail", "error", "description"):
                if key in error_payload:
                    append_unique_message(messages, error_payload[key])

    if RateLimitError is not None and isinstance(exc, RateLimitError):
        # Provide a consistent hint for rate limit scenarios
        append_unique_message(messages, "OpenAI API rate limit reached")

    # APIStatusError / APIError may provide response payloads
    if APIStatusError is not None and isinstance(exc, APIStatusError):
        response = getattr(exc, "response", None)
        if response is not None:
            json_loader = getattr(response, "json", None)
            if callable(json_loader):
                try:
                    data = json_loader()
                except (json.JSONDecodeError, ValueError) as e:
                    # best effort only: ignore JSON decoding issues
                    logger.debug(f"Failed to parse JSON from response: {e}")
                    data = None
            else:
                data = None

            if isinstance(data, dict):
                error_payload = data.get("error") or data
                if isinstance(error_payload, dict):
                    for key in ("message", "detail", "error", "description"):
                        if key in error_payload:
                            append_unique_message(messages, error_payload[key])
            else:
                text = getattr(response, "text", None)
                if text:
                    append_unique_message(messages, text)

    if APIError is not None and isinstance(exc, APIError):
        append_unique_message(messages, f"OpenAI API error ({exc.__class__.__name__})")

    if not messages:
        append_unique_message(messages, exc.__class__.__name__)

    return " | ".join(messages)
