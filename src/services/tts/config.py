"""
TTS Configuration
=================

Configuration management for Text-to-Speech services.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / "DeepTutor.env", override=False)
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _strip_value(value: Optional[str]) -> Optional[str]:
    """Remove leading/trailing whitespace and quotes from string."""
    if value is None:
        return None
    return value.strip().strip("\"'")


def get_tts_config() -> dict:
    """
    Return complete environment configuration for TTS (Text-to-Speech).

    Returns:
        dict: Dictionary containing the following keys:
            - model: TTS model name
            - api_key: TTS API key
            - base_url: TTS API endpoint URL
            - api_version: TTS API version (for Azure OpenAI)
            - voice: Default voice character

    Raises:
        ValueError: If required configuration is missing
    """
    model = _strip_value(os.getenv("TTS_MODEL"))
    api_key = _strip_value(os.getenv("TTS_API_KEY"))
    base_url = _strip_value(os.getenv("TTS_URL"))
    api_version = _strip_value(os.getenv("TTS_BINDING_API_VERSION"))
    voice = _strip_value(os.getenv("TTS_VOICE", "alloy"))

    # Validate required configuration
    if not model:
        raise ValueError(
            "Error: TTS_MODEL not set, please configure it in .env file (e.g., tts-1 or tts-1-hd)"
        )
    if not api_key:
        raise ValueError("Error: TTS_API_KEY not set, please configure it in .env file")
    if not base_url:
        raise ValueError(
            "Error: TTS_URL not set, please configure it in .env file (e.g., https://api.openai.com/v1)"
        )

    return {
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "api_version": api_version,
        "voice": voice,
    }


__all__ = ["get_tts_config"]
