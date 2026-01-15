#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NarratorAgent - Note narration agent.
Inherits from unified BaseAgent with special TTS configuration.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Any, Optional
from urllib.parse import urlparse
import uuid

from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.agents.base_agent import BaseAgent
from src.services.tts import get_tts_config

# Import shared stats from edit_agent for legacy compatibility

# Define storage path (unified under user/co-writer/ directory)
USER_DIR = Path(__file__).parent.parent.parent.parent / "data" / "user" / "co-writer" / "audio"


def ensure_dirs():
    """Ensure directories exist"""
    USER_DIR.mkdir(parents=True, exist_ok=True)


class NarratorAgent(BaseAgent):
    """Note Narration Agent - Generate narration script and convert to audio"""

    def __init__(self, language: str = "en"):
        """
        Initialize NarratorAgent.

        Args:
            language: Language setting ('en' | 'zh'), default 'en'

        Note: LLM configuration (api_key, base_url, model, etc.) is loaded
        automatically from the unified config service. Use refresh_config()
        to pick up configuration changes made in Settings.
        """
        # Use "narrator" as module_name to get independent temperature/max_tokens config
        super().__init__(
            module_name="narrator",
            agent_name="narrator_agent",
            language=language,
        )

        # Override prompts to load from co_writer module
        # (narrator_agent prompts are stored under co_writer/prompts/)
        from src.services.prompt import get_prompt_manager

        self.prompts = get_prompt_manager().load_prompts(
            module_name="co_writer",
            agent_name="narrator_agent",
            language=language,
        )

        # Load TTS-specific configuration
        self._load_tts_config()

    def _load_tts_config(self):
        """Load TTS-specific configuration from unified config service."""
        try:
            self.tts_config = get_tts_config()
            # Get voice from unified config (defaults to "alloy")
            self.default_voice = self.tts_config.get("voice", "alloy")
            self.logger.info(f"TTS settings loaded: voice={self.default_voice}")
            # Validate TTS configuration
            self._validate_tts_config()
        except Exception as e:
            self.logger.error(f"Failed to load TTS config: {e}", exc_info=True)
            self.tts_config = None
            self.default_voice = "alloy"

    def _validate_tts_config(self):
        """Validate TTS configuration completeness and format"""
        if not self.tts_config:
            raise ValueError("TTS config is None")

        # Check required keys
        required_keys = ["model", "api_key", "base_url"]
        missing_keys = [key for key in required_keys if key not in self.tts_config]
        if missing_keys:
            raise ValueError(f"TTS config missing required keys: {missing_keys}")

        # Validate base_url format
        base_url = self.tts_config["base_url"]
        if not base_url:
            raise ValueError("TTS config 'base_url' is empty")

        if not isinstance(base_url, str):
            raise ValueError(f"TTS config 'base_url' must be a string, got {type(base_url)}")

        # Validate URL format
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"TTS config 'base_url' must start with http:// or https://, got: {base_url}"
            )

        try:
            parsed = urlparse(base_url)
            if not parsed.netloc:
                raise ValueError(f"TTS config 'base_url' has invalid format: {base_url}")
        except Exception as e:
            raise ValueError(f"TTS config 'base_url' parsing error: {e}")

        # Validate api_key
        api_key = self.tts_config.get("api_key")
        if not api_key:
            raise ValueError("TTS config 'api_key' is empty")

        if not isinstance(api_key, str) or len(api_key.strip()) == 0:
            raise ValueError("TTS config 'api_key' must be a non-empty string")

        # Validate model
        model = self.tts_config.get("model")
        if not model:
            raise ValueError("TTS config 'model' is empty")

        # Log configuration info (hide sensitive information)
        api_key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "*" * 10
        self.logger.info("TTS Configuration Loaded (OpenAI API):")
        self.logger.info(f"  Model: {model}")
        self.logger.info(f"  Base URL: {base_url}")
        self.logger.info(f"  API Key: {api_key_preview}")
        self.logger.info(f"  Default Voice: {self.default_voice}")

    async def process(
        self,
        content: str,
        style: str = "friendly",
        voice: Optional[str] = None,
        skip_audio: bool = False,
    ) -> dict[str, Any]:
        """
        Main processing method - alias for narrate().

        Args:
            content: Note content
            style: Narration style
            voice: Voice role
            skip_audio: Whether to skip audio generation

        Returns:
            Dict containing script info and optionally audio info
        """
        return await self.narrate(content, style, voice, skip_audio)

    async def generate_script(self, content: str, style: str = "friendly") -> dict[str, Any]:
        """
        Generate narration script

        Args:
            content: Note content (Markdown format)
            style: Narration style (friendly, academic, concise)

        Returns:
            Dict containing:
                - script: Narration script text
                - key_points: List of extracted key points
        """
        # Estimate target length: OpenAI TTS supports up to 4096 characters
        is_long_content = len(content) > 5000

        style_prompts = {
            "friendly": self.get_prompt("style_friendly", ""),
            "academic": self.get_prompt("style_academic", ""),
            "concise": self.get_prompt("style_concise", ""),
        }

        length_instruction = (
            self.get_prompt("length_instruction_long", "")
            if is_long_content
            else self.get_prompt("length_instruction_short", "")
        )

        system_template = self.get_prompt("generate_script_system_template", "")
        system_prompt = system_template.format(
            style_prompt=style_prompts.get(style, style_prompts["friendly"]),
            length_instruction=length_instruction,
        )

        if is_long_content:
            user_template = self.get_prompt("generate_script_user_long", "")
            user_prompt = user_template.format(content=content[:8000] + "...")
        else:
            user_template = self.get_prompt("generate_script_user_short", "")
            user_prompt = user_template.format(content=content)

        self.logger.info(f"Generating narration script with style: {style}")

        # Use inherited call_llm method
        response = await self.call_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            stage="generate_script",
        )

        # Clean and truncate response, ensure it doesn't exceed 4000 characters
        script = response.strip()
        if len(script) > 4000:
            self.logger.warning(
                f"Generated script length {len(script)} exceeds 4000 limit. Truncating..."
            )
            truncated = script[:3997]
            last_period = max(
                truncated.rfind("。"),
                truncated.rfind("！"),
                truncated.rfind("？"),
                truncated.rfind("."),
                truncated.rfind("!"),
                truncated.rfind("?"),
            )
            if last_period > 3500:
                script = truncated[: last_period + 1]
            else:
                script = truncated + "..."

        key_points = await self._extract_key_points(content)

        return {
            "script": script,
            "key_points": key_points,
            "style": style,
            "original_length": len(content),
            "script_length": len(script),
        }

    async def _extract_key_points(self, content: str) -> list:
        """Extract key points from notes"""
        system_prompt = self.get_prompt("extract_key_points_system", "")
        user_template = self.get_prompt(
            "extract_key_points_user",
            "Please extract key points from the following notes:\n\n{content}",
        )
        user_prompt = user_template.format(content=content[:4000])

        try:
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                stage="extract_key_points",
            )

            # Try to parse JSON
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            self.logger.warning(f"Failed to extract key points: {e}")
            return []

    async def generate_audio(self, script: str, voice: str = None) -> dict[str, Any]:
        """
        Convert narration script to audio using OpenAI TTS API

        Args:
            script: Narration script text
            voice: Voice role (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            Dict containing:
                - audio_path: Audio file path
                - audio_url: Audio access URL
                - audio_id: Unique audio identifier
                - voice: Voice used
        """
        if not self.tts_config:
            raise ValueError(
                "TTS configuration not available. Please configure TTS_MODEL, TTS_API_KEY, and TTS_URL in .env"
            )

        # Use default voice if not specified
        if voice is None:
            voice = self.default_voice

        # Validate input parameters
        if not script or not script.strip():
            raise ValueError("Script cannot be empty")

        ensure_dirs()

        # Truncate overly long scripts (OpenAI TTS supports up to 4096 characters)
        original_script_length = len(script)
        if len(script) > 4096:
            self.logger.warning(f"Script length {len(script)} exceeds 4096 limit. Truncating...")
            truncated = script[:4093]
            last_period = max(
                truncated.rfind("。"),
                truncated.rfind("！"),
                truncated.rfind("？"),
                truncated.rfind("."),
                truncated.rfind("!"),
                truncated.rfind("?"),
            )
            if last_period > 3500:
                script = truncated[: last_period + 1]
            else:
                script = truncated + "..."
            self.logger.info(
                f"Script truncated from {original_script_length} to {len(script)} characters"
            )

        audio_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        audio_filename = f"narration_{audio_id}.mp3"
        audio_path = USER_DIR / audio_filename

        self.logger.info(f"Starting TTS audio generation - ID: {audio_id}, Voice: {voice}")

        try:
            binding = os.getenv("TTS_BINDING", "openai")
            api_version = self.tts_config.get("api_version")

            # Only use Azure client if binding is explicitly Azure,
            # OR if binding is generic 'openai' but an Azure-specific api_version is present.
            if binding == "azure_openai" or (binding == "openai" and api_version):
                client = AsyncAzureOpenAI(
                    api_key=self.tts_config["api_key"],
                    azure_endpoint=self.tts_config["base_url"],
                    api_version=api_version,
                )
            else:
                # Create OpenAI client with custom base_url
                client = AsyncOpenAI(
                    base_url=self.tts_config["base_url"], api_key=self.tts_config["api_key"]
                )

            # Call OpenAI TTS API
            response = await client.audio.speech.create(
                model=self.tts_config["model"], voice=voice, input=script
            )

            # Save audio to file
            await response.stream_to_file(audio_path)

            self.logger.info(f"Audio saved to: {audio_path}")

            # Use correct path: co-writer/audio (matching the actual storage directory)
            relative_path = f"co-writer/audio/{audio_filename}"
            audio_access_url = f"/api/outputs/{relative_path}"

            return {
                "audio_path": str(audio_path),
                "audio_url": audio_access_url,
                "audio_id": audio_id,
                "voice": voice,
            }

        except Exception as e:
            self.logger.error(f"TTS generation failed: {type(e).__name__}: {e}", exc_info=True)
            raise ValueError(f"TTS generation failed: {type(e).__name__}: {e}")

    async def narrate(
        self,
        content: str,
        style: str = "friendly",
        voice: str = None,
        skip_audio: bool = False,
    ) -> dict[str, Any]:
        """
        Complete narration flow: generate script + generate audio

        Args:
            content: Note content
            style: Narration style
            voice: Voice role (alloy, echo, fable, onyx, nova, shimmer)
            skip_audio: Whether to skip audio generation (only return script)

        Returns:
            Dict containing script info and optionally audio info
        """
        # Refresh TTS config before starting to avoid stale credentials
        try:
            self.tts_config = get_tts_config()
        except Exception as e:
            self.logger.error(f"Failed to refresh TTS config: {e}")

        script_result = await self.generate_script(content, style)

        # Use default voice if not specified
        if voice is None:
            voice = self.default_voice

        result = {
            "script": script_result["script"],
            "key_points": script_result["key_points"],
            "style": style,
            "original_length": script_result["original_length"],
            "script_length": script_result["script_length"],
        }

        if not skip_audio and self.tts_config:
            try:
                audio_result = await self.generate_audio(script_result["script"], voice=voice)
                result.update(
                    {
                        "audio_url": audio_result["audio_url"],
                        "audio_path": audio_result["audio_path"],
                        "audio_id": audio_result["audio_id"],
                        "voice": voice,
                        "has_audio": True,
                    }
                )
            except Exception as e:
                self.logger.error(f"Audio generation failed: {e}")
                result["has_audio"] = False
                result["audio_error"] = str(e)
        else:
            result["has_audio"] = False
            if not self.tts_config:
                result["audio_error"] = "TTS not configured"

        return result


__all__ = ["NarratorAgent"]
