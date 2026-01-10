"""
LLM Exceptions
==============

Exception hierarchy for LLM service errors.
Provides specific exception types for different error conditions
to enable proper retry logic and error handling.
"""


class LLMError(Exception):
    """Base exception for all LLM errors."""

    pass


class LLMConfigurationError(LLMError):
    """Configuration errors (missing keys, invalid URLs)."""

    pass


class LLMAuthenticationError(LLMError):
    """Authentication failures (401)."""

    pass


class LLMAPIError(LLMError):
    """
    Errors returned by the API provider.

    Attributes:
        status_code: HTTP status code
        provider: Name of the provider (openai, anthropic, etc.)
    """

    def __init__(self, message: str, status_code: int = None, provider: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class LLMRateLimitError(LLMAPIError):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: float = None, provider: str = None):
        super().__init__(message, status_code=429, provider=provider)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Connection or read timeouts."""

    pass
