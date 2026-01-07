#!/usr/bin/env python
"""
BaseAgent - Base class for research module agents.
Uses unified PromptManager for prompt loading.
"""

from abc import ABC, abstractmethod
from pathlib import Path
import sys
import time
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lightrag.llm.openai import openai_complete_if_cache

from src.core.core import get_agent_params, get_llm_config
from src.core.prompt_manager import get_prompt_manager

from ..utils.token_tracker import get_token_tracker


class BaseAgent(ABC):
    """Base class for research module agents."""

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

        # Load prompts using unified PromptManager
        language = self.config.get("system", {}).get("language", "zh")
        self.prompts = get_prompt_manager().load_prompts(
            module_name="research",
            agent_name=self.agent_name,
            language=language,
        )

    def get_prompt(self, section: str, field: str = None, fallback: str = "") -> str:
        """Get prompt template from loaded prompts."""
        return get_prompt_manager().get_prompt(self.prompts, section, field, fallback)

    def get_model(self) -> str:
        """Get model name (only loaded from environment variables, ignore model in config file)"""
        # If config accidentally contains model field, ignore it (can log one-time warning here)
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

        Args:
            user_prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature parameter
            model: Model name
            max_tokens: Maximum token count
            verbose: Whether to print output
            stage: Stage marker (for logging)

        Returns:
            LLM response
        """
        model = model or self.get_model()
        temperature = temperature if temperature is not None else self.get_temperature()
        max_tokens = max_tokens or self.get_max_tokens()

        # Record call start time
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

        # Call LLM and record errors
        response = None
        error = None
        try:
            response = await openai_complete_if_cache(**kwargs)
        except Exception as e:
            error = e
            # Log error
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"LLM call failed: {e}")
            raise

        # Calculate call duration
        call_duration = time.time() - start_time

        # Record token usage (optional)
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

        # Log LLM call info
        if hasattr(self, "logger") and self.logger:
            self.logger.debug(f"LLM call completed: model={model}, duration={call_duration:.2f}s")

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
