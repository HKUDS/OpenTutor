#!/usr/bin/env python
"""
BaseGuideAgent - Base class for guided learning agents.
Uses unified PromptManager for prompt loading.
"""

from abc import ABC, abstractmethod
import os
from pathlib import Path
import sys
from typing import Any

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logging import LLMStats, get_logger
from src.services.config import get_agent_params, load_config_with_main
from src.services.llm import complete as llm_complete
from src.services.llm import get_token_limit_kwargs
from src.services.prompt import get_prompt_manager


class BaseGuideAgent(ABC):
    """Base class for Guided Learning Agents."""

    # Shared stats tracker for all guide agents
    _shared_stats: LLMStats | None = None

    def __init__(
        self,
        api_key: str,
        base_url: str,
        agent_name: str,
        language: str = "zh",
        binding: str = "openai",
    ):
        """
        Initialize base Agent.

        Args:
            api_key: API key
            base_url: API endpoint
            agent_name: Agent name
            language: Language setting ('zh' | 'en')
            binding: LLM provider binding
        """
        self.api_key = api_key
        self.base_url = base_url
        self.agent_name = agent_name
        self.language = language
        self.binding = binding

        # Load agent parameters from unified config (agents.yaml)
        self._agent_params = get_agent_params("guide")

        # Initialize logger (from config)
        try:
            config = load_config_with_main("guide_config.yaml", _project_root)
            log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get(
                "log_dir"
            )
            self.logger = get_logger(f"Guide.{agent_name}", log_dir=log_dir)
        except Exception:
            # Fallback logger
            self.logger = get_logger(f"Guide.{agent_name}")

        # Load prompts using unified PromptManager
        self.prompts = get_prompt_manager().load_prompts(
            module_name="guide",
            agent_name=self.agent_name,
            language=self.language,
        )
        if self.prompts:
            self.logger.info(f"Loaded prompts: {self.agent_name} ({self.language})")

    @classmethod
    def get_stats(cls) -> LLMStats:
        """Get or create shared stats tracker."""
        if cls._shared_stats is None:
            cls._shared_stats = LLMStats(module_name="GuidedLearning")
        return cls._shared_stats

    @classmethod
    def reset_stats(cls):
        """Reset shared stats."""
        if cls._shared_stats:
            cls._shared_stats.reset()

    @classmethod
    def print_stats(cls):
        """Print stats summary."""
        if cls._shared_stats:
            cls._shared_stats.print_summary()

    def get_model(self) -> str:
        """Get model name."""
        model = os.getenv("LLM_MODEL")
        if not model:
            raise ValueError("Environment variable LLM_MODEL not set")
        return model

    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: str,
        response_format: dict[str, str] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Unified LLM call interface.

        Args:
            user_prompt: User prompt
            system_prompt: System prompt
            response_format: Response format
            temperature: Temperature parameter (uses config default if None)
            max_tokens: Maximum tokens (uses config default if None)

        Returns:
            LLM response text
        """
        model = self.get_model()

        # Use parameters from unified config (agents.yaml) if not explicitly provided
        if temperature is None:
            temperature = self._agent_params["temperature"]
        if max_tokens is None:
            max_tokens = self._agent_params["max_tokens"]

        kwargs = {
            "model": model,
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": temperature,
            "binding": self.binding,
        }

        if max_tokens:
            kwargs.update(get_token_limit_kwargs(model, max_tokens))

        if response_format:
            kwargs["response_format"] = response_format

        response = await llm_complete(**kwargs)

        # Track token usage
        stats = self.get_stats()
        stats.add_call(
            model=model, system_prompt=system_prompt, user_prompt=user_prompt, response=response
        )

        return response

    def get_prompt(self, prompt_type: str = "system") -> str | None:
        """Get prompt"""
        if self.prompts and prompt_type in self.prompts:
            return self.prompts[prompt_type]
        return None

    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """Main processing logic of the agent (must be implemented by subclasses)"""
