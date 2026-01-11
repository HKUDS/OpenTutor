"""
LLM Service Exceptions
======================

Custom exception classes for the LLM service.
Provides a consistent exception hierarchy for better error handling.

Usage:
    from src.services.llm.exceptions import LLMError, LLMConfigError, LLMAPIError

    try:
        response = await complete(...)
    except LLMConfigError as e:
        # Handle configuration errors (missing API key, etc.)
        logger.error(f"Configuration error: {e}")
    except LLMAPIError as e:
        # Handle API errors (rate limits, invalid requests, etc.)
        logger.error(f"API error: {e.status_code} - {e.message}")
    except LLMError as e:
        # Handle all other LLM-related errors
        logger.error(f"LLM error: {e}")
"""

from typing import Optional


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class LLMConfigError(LLMError):
    """
    Raised when there's an error in LLM configuration.

    Examples:
    - Missing API key
    - Missing model name
    - Invalid base URL
    - Missing required environment variables
    """

    pass


class LLMProviderError(LLMError):
    """
    Raised when there's an error with the LLM provider.

    Examples:
    - Provider not found
    - Provider not configured
    - Provider activation failed
    """

    pass


class LLMAPIError(LLMError):
    """
    Raised when an API call to an LLM provider fails.

    Attributes:
        status_code: HTTP status code from the API (if available)
        provider: Name of the provider that returned the error
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        provider: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.provider = provider

    def __str__(self) -> str:
        parts = []
        if self.provider:
            parts.append(f"[{self.provider}]")
        if self.status_code:
            parts.append(f"HTTP {self.status_code}")
        parts.append(self.message)
        return " ".join(parts)


class LLMTimeoutError(LLMAPIError):
    """
    Raised when an API call times out.
    """

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: Optional[float] = None,
        provider: Optional[str] = None,
    ):
        super().__init__(message, status_code=408, provider=provider)
        self.timeout = timeout


class LLMRateLimitError(LLMAPIError):
    """
    Raised when rate limited by the API.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        provider: Optional[str] = None,
    ):
        super().__init__(message, status_code=429, provider=provider)
        self.retry_after = retry_after


class LLMAuthenticationError(LLMAPIError):
    """
    Raised when authentication fails (invalid API key, etc.).
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        provider: Optional[str] = None,
    ):
        super().__init__(message, status_code=401, provider=provider)


class LLMModelNotFoundError(LLMAPIError):
    """
    Raised when the requested model is not found or not available.
    """

    def __init__(
        self,
        message: str = "Model not found",
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        super().__init__(message, status_code=404, provider=provider)
        self.model = model


__all__ = [
    "LLMError",
    "LLMConfigError",
    "LLMProviderError",
    "LLMAPIError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMModelNotFoundError",
]
