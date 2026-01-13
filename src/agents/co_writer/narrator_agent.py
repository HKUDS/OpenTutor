#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NarratorAgent - Note narration agent.
Uses unified PromptManager for prompt loading.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse
import uuid

from openai import OpenAI

# Add project root for imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logging import get_logger
from src.services.config import get_agent_params, load_config_with_main
from src.services.llm import complete as llm_complete
from src.services.llm import get_llm_config
from src.services.prompt import get_prompt_manager
from src.services.tts import get_tts_config

# Initialize logger with config
try:
    config = load_config_with_main(
        "solve_config.yaml", _project_root
    )  # Use any config to get main.yaml
    log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get(
        "log_dir"
    )
    logger = get_logger("Narrator", log_dir=log_dir)
except Exception:
    # Fallback to standard logging
    logger = logging.getLogger(__name__)

# Import shared stats from edit_agent
from .edit_agent import get_stats

# Define storage path (unified under user/co-writer/ directory)
# Notes:
# - Consistent with EditAgent's history records, both use user/co-writer as root directory
# - Audio files are stored separately in audio subdirectory for static access via /api/outputs
USER_DIR = Path(__file__).parent.parent.parent.parent / "data" / "user" / "co-writer" / "audio"


def ensure_dirs():
    """Ensure directories exist"""
    USER_DIR.mkdir(parents=True, exist_ok=True)


class NarratorAgent:
    """Note Narration Agent - Generate narration script and convert to audio"""

    def __init__(self, language: str = "en"):
        # Load agent parameters from unified config (agents.yaml)
        self._agent_params = get_agent_params("narrator")
        self.language = language

        # Load prompts using unified PromptManager
        self._prompts = get_prompt_manager().load_prompts(
            module_name="co_writer",
            agent_name="narrator_agent",
            language=language,
        )

        try:
            self.llm_config = get_llm_config()
        except Exception as e:
            logger.error(f"Failed to load LLM config: {e}")
            self.llm_config = None

        # Load main config file to get TTS default settings
        try:
            config = load_config_with_main("solve_config.yaml", _project_root)
            self.tts_settings = config.get("tts", {})
            self.default_voice = self.tts_settings.get("default_voice", "alloy")
            logger.info(f"TTS settings loaded from config: voice={self.default_voice}")
        except Exception as e:
            logger.warning(f"Failed to load TTS settings from config, using defaults: {e}")
            self.default_voice = "alloy"

        try:
            self.tts_config = get_tts_config()
            # Validate TTS configuration
            self._validate_tts_config()
        except Exception as e:
            logger.error(f"Failed to load TTS config: {e}", exc_info=True)
            self.tts_config = None

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
        logger.info("TTS Configuration Loaded (OpenAI API):")
        logger.info(f"  Model: {model}")
        logger.info(f"  Base URL: {base_url}")
        logger.info(f"  API Key: {api_key_preview}")
        logger.info(f"  Default Voice: {self.default_voice}")

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
        # Always refresh LLM config before starting to avoid stale credentials
        try:
            self.llm_config = get_llm_config()
        except Exception as e:
            logger.error(f"Failed to refresh LLM config: {e}")

        if not self.llm_config:
            raise ValueError("LLM configuration not available")

        # Estimate target length: OpenAI TTS supports up to 4096 characters
        # We target 4000 characters to leave some margin
        target_length = 4000
        is_long_content = len(content) > 5000

        style_prompts = {
            "friendly": self._prompts.get("style_friendly", ""),
            "academic": self._prompts.get("style_academic", ""),
            "concise": self._prompts.get("style_concise", ""),
        }

        length_instruction = (
            self._prompts.get("length_instruction_long", "")
            if is_long_content
            else self._prompts.get("length_instruction_short", "")
        )

        system_template = self._prompts.get("generate_script_system_template", "")
        system_prompt = system_template.format(
            style_prompt=style_prompts.get(style, style_prompts["friendly"]),
            length_instruction=length_instruction,
        )

        if is_long_content:
            user_template = self._prompts.get("generate_script_user_long", "")
            user_prompt = user_template.format(content=content[:8000] + "...")
        else:
            user_template = self._prompts.get("generate_script_user_short", "")
            user_prompt = user_template.format(content=content)

        logger.info(f"Generating narration script with style: {style}")

        model = self.llm_config.model
        response = await llm_complete(
            binding=self.llm_config.binding,
            model=model,
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_key=self.llm_config.api_key,
            base_url=self.llm_config.base_url,
            max_tokens=self._agent_params["max_tokens"],
            temperature=self._agent_params["temperature"],
        )

        # Track token usage
        stats = get_stats()
        stats.add_call(
            model=model, system_prompt=system_prompt, user_prompt=user_prompt, response=response
        )

        # Clean and truncate response, ensure it doesn't exceed 4000 characters
        script = response.strip()
        if len(script) > 4000:
            logger.warning(
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
        if not self.llm_config:
            return []

        system_prompt = self._prompts.get("extract_key_points_system", "")
        user_template = self._prompts.get(
            "extract_key_points_user",
            "Please extract key points from the following notes:\n\n{content}",
        )
        user_prompt = user_template.format(content=content[:4000])

        try:
            model = self.llm_config.model
            response = await llm_complete(
                binding=self.llm_config.binding,
                model=model,
                prompt=user_prompt,
                system_prompt=system_prompt,
                api_key=self.llm_config.api_key,
                base_url=self.llm_config.base_url,
                max_tokens=self._agent_params["max_tokens"],
                temperature=self._agent_params["temperature"],
            )

            # Track token usage
            stats = get_stats()
            stats.add_call(
                model=model, system_prompt=system_prompt, user_prompt=user_prompt, response=response
            )

            # Try to parse JSON
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []
        except Exception as e:
            logger.warning(f"Failed to extract key points: {e}")
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
            logger.warning(f"Script length {len(script)} exceeds 4096 limit. Truncating...")
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
            logger.info(
                f"Script truncated from {original_script_length} to {len(script)} characters"
            )

        audio_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        audio_filename = f"narration_{audio_id}.mp3"
        audio_path = USER_DIR / audio_filename

        logger.info(f"Starting TTS audio generation - ID: {audio_id}, Voice: {voice}")

        try:
            # Create OpenAI client with custom base_url
            client = OpenAI(
                base_url=self.tts_config["base_url"], api_key=self.tts_config["api_key"]
            )

            # Call OpenAI TTS API
            response = client.audio.speech.create(
                model=self.tts_config["model"], voice=voice, input=script
            )

            # Save audio to file
            response.stream_to_file(audio_path)

            logger.info(f"Audio saved to: {audio_path}")

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
            logger.error(f"TTS generation failed: {type(e).__name__}: {e}", exc_info=True)
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
            # Also refresh LLM config since narrate calls generate_script
            self.llm_config = get_llm_config()
        except Exception as e:
            logger.error(f"Failed to refresh configs: {e}")

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
                logger.error(f"Audio generation failed: {e}")
                result["has_audio"] = False
                result["audio_error"] = str(e)
        else:
            result["has_audio"] = False
            if not self.tts_config:
                result["audio_error"] = "TTS not configured"

        return result


__all__ = ["NarratorAgent"]
