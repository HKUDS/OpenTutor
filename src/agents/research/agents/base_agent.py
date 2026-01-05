#!/usr/bin/env python
"""
BaseAgent 2.0 - Improved Agent base class
Integrates env_config, prompt_loader, token_tracker, logger
"""

from abc import ABC, abstractmethod
from pathlib import Path
import sys
import time
from typing import Any

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
# Add research directory to path (for importing utils and other local modules)
research_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(research_dir))

try:
    from lightrag.llm.openai import openai_complete_if_cache
except ModuleNotFoundError:
    openai_complete_if_cache = None

from src.core.core import get_agent_params, get_llm_config, parse_language
from ..utils.token_tracker import get_token_tracker


LANGUAGE_MAP = {
    "en": "en",
    "zh": "zh",
    "cn": "cn",
}
DEFAULT_LANGUAGE = "en"


class BaseAgent(ABC):
    """Improved Agent base class"""

    _PROMPT_CACHE: dict[str, dict[str, Any]] = {}

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str | None = None,
        base_url: str | None = None,
        agent_name: str = "base_agent",
    ):
        """
        Initialize Agent

        Args:
            config: Complete configuration dictionary
            api_key: API key (optional, prefers env_config)
            base_url: API endpoint (optional, prefers env_config)
            agent_name: Agent name
        """
        self.config = config
        self.agent_name = agent_name

        # Load agent parameters from unified config (agents.yaml)
        self._agent_params = get_agent_params("research")

        # Load LLM configuration from env_config
        try:
            env_llm = get_llm_config()
            self.api_key = api_key or env_llm.get("api_key")
            self.base_url = base_url or env_llm.get("base_url")
            self.default_model = env_llm.get("model")
        except ValueError as e:
            print(f"⚠️ Environment configuration error: {e}")
            self.api_key = api_key
            self.base_url = base_url
            self.default_model = "gpt-4o"

        # Get Agent-specific configuration
        self.agent_config = config.get("agents", {}).get(agent_name, {})
        self.llm_config = config.get("llm", {})
        self.enabled = self.agent_config.get("enabled", True)

        # Load prompts
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, Any]:
        """Load prompt definitions for current Agent"""

        language = self.config.get("system", {}).get("language", DEFAULT_LANGUAGE)
        lang_code = parse_language(language)

        lang_dir = LANGUAGE_MAP.get(lang_code, DEFAULT_LANGUAGE)

        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompts_dir / lang_dir / f"{self.agent_name}.yaml"

        cache_key = f"{self.agent_name}_{lang_dir}"
        if cache_key in BaseAgent._PROMPT_CACHE:
            return BaseAgent._PROMPT_CACHE[cache_key]

        # Fallback to other languages
        if not prompt_file.exists():
            for fallback_lang in LANGUAGE_MAP.values():
                candidate = prompts_dir / fallback_lang / f"{self.agent_name}.yaml"
                if candidate.exists():
                    prompt_file = candidate
                    lang_dir = fallback_lang
                    cache_key = f"{self.agent_name}_{lang_dir}"
                    break

        if not prompt_file.exists():
            print(f"⚠️ Prompt file not found: {prompt_file}")
            BaseAgent._PROMPT_CACHE[cache_key] = {}
            return {}

        try:
            with open(prompt_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"⚠️ Failed to load prompt file {prompt_file}: {exc}")
            data = {}

        BaseAgent._PROMPT_CACHE[cache_key] = data
        return data

    def get_prompt(self, section: str, field: str, fallback: str = "") -> str:
        """Get specified prompt template"""
        template = self.prompts.get(section, {}).get(field)
        return template if template is not None else fallback

    def get_model(self) -> str:
        """Get model name (only loaded from environment variables, ignore model in config file)"""
        return self.default_model

    def get_temperature(self) -> float:
        """Get temperature parameter from unified config (agents.yaml)"""
        return self._agent_params["temperature"]

    def get_max_tokens(self) -> int:
        """Get maximum token count from unified config (agents.yaml)"""
        return self._agent_params["max_tokens"]

    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: str,
        temperature: float | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        verbose: bool = True,
        stage: str | None = None,
    ) -> str:
        """
        Unified interface for calling LLM
        """
        model = model or self.get_model()
        temperature = temperature if temperature is not None else self.get_temperature()
        max_tokens = max_tokens or self.get_max_tokens()

        start_time = time.time()

        kwargs = {
            "model": model,
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": temperature,
        }

        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if openai_complete_if_cache is None:
            raise RuntimeError(
                "Optional dependency 'lightrag' is not installed. "
                "Install it to enable LLM functionality."
            )


        try:
            response = await openai_complete_if_cache(**kwargs)
        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"LLM call failed: {e}")
            raise

        call_duration = time.time() - start_time

        try:
            tracker = get_token_tracker()
            tracker.add_usage(
                agent_name=self.agent_name,
                stage=stage or "default",
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response,
            )
        except Exception:
            pass

        if hasattr(self, "logger") and self.logger:
            self.logger.debug(
                f"LLM call completed: model={model}, duration={call_duration:.2f}s"
            )

        if verbose:
            print(f"\n{'=' * 70}")
            print(f"🤖 [{self.agent_name}] LLM Output:")
            print(f"{'=' * 70}")
            if len(response) > 2000:
                print(response[:2000] + f"\n... (truncated, total length: {len(response)})")
            else:
                print(response)
            print(f"{'=' * 70}\n")

        return response

    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """Main processing logic of Agent (must be implemented by subclasses)"""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.agent_name}, enabled={self.enabled})"


__all__ = ["BaseAgent"]
