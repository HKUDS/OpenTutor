"""Utilities for optional RagAnything integration.

This module centralizes the lazy import logic so that core functionality
continues to work even when the optional `raganything` package is not
installed.  Callers can use :func:`load_raganything` to attempt an import and
react gracefully if it fails.
"""

from __future__ import annotations

from typing import Any

__all__ = ["load_raganything"]


def load_raganything() -> tuple[Any | None, Any | None, str | None]:
    """Attempt to import RagAnything lazily.

    Returns:
        tuple: ``(RAGAnything, RAGAnythingConfig, error_message)`` where the
        first two values are ``None`` when the optional dependency is missing.
    """

    try:
        from raganything import RAGAnything, RAGAnythingConfig  # type: ignore

        return RAGAnything, RAGAnythingConfig, None
    except ModuleNotFoundError as exc:  # pragma: no cover - optional import
        return None, None, str(exc)
    except Exception as exc:  # pragma: no cover - unexpected import failure
        return None, None, str(exc)
