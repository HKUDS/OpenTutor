"""
LLM Client
==========

Unified LLM client for all DeepTutor services.

Note: This is a legacy interface. Prefer using the factory functions directly:
    from src.services.llm import complete, stream
"""

from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .capabilities import system_in_messages
from .config import LLMConfig, get_llm_config


class LLMClient:
    """
    Unified LLM client for all services.

    Wraps the LLM Factory with a class-based interface.
    Prefer using factory functions (complete, stream) directly for new code.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM client.

        Args:
            config: LLM configuration. If None, loads from environment.
        """
        self.config = config or get_llm_config()
        self.logger = get_logger("LLMClient")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call LLM completion via Factory.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            history: Optional conversation history
            **kwargs: Additional arguments passed to the API

        Returns:
            LLM response text
        """
        from . import factory

        # Delegate to factory for unified routing and retry handling
        return await factory.complete(
            prompt=prompt,
            system_prompt=system_prompt or "You are a helpful assistant.",
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            api_version=getattr(self.config, "api_version", None),
            binding=getattr(self.config, "binding", "openai"),
            **kwargs,
        )

    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Synchronous wrapper for complete().

        Use this when you need to call from non-async context.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in an async context, we need to use a different approach
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self.complete(prompt, system_prompt, history, **kwargs)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.complete(prompt, system_prompt, history, **kwargs)
                )
        except RuntimeError:
            return asyncio.run(self.complete(prompt, system_prompt, history, **kwargs))

    def get_model_func(self):
        """
        Get a function compatible with LightRAG's llm_model_func parameter.

        Returns:
            Callable that can be used as llm_model_func
        """
        binding = getattr(self.config, "binding", "openai")

        # Use capabilities to determine if provider uses OpenAI-style messages
        uses_openai_style = system_in_messages(binding, self.config.model)

        # For non-OpenAI-compatible providers (e.g., Anthropic), use Factory
        if not uses_openai_style:
            from . import factory

            def llm_model_func_via_factory(
                prompt: str,
                system_prompt: Optional[str] = None,
                history_messages: Optional[List[Dict]] = None,
                **kwargs: Any,
            ):
                return factory.complete(
                    prompt=prompt,
                    system_prompt=system_prompt or "You are a helpful assistant.",
                    model=self.config.model,
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    binding=binding,
                    **kwargs,
                )

            return llm_model_func_via_factory

        # OpenAI-compatible bindings use lightrag (has caching)
        from lightrag.llm.openai import openai_complete_if_cache

        def llm_model_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: Optional[List[Dict]] = None,
            **kwargs: Any,
        ):
            # Only pass api_version if set (for Azure OpenAI)
            lightrag_kwargs = {
                "system_prompt": system_prompt,
                "history_messages": history_messages or [],
                "api_key": self.config.api_key,
                "base_url": self.config.base_url,
                **kwargs,
            }
            api_version = getattr(self.config, "api_version", None)
            if api_version:
                lightrag_kwargs["api_version"] = api_version
            return openai_complete_if_cache(
                self.config.model,
                prompt,
                **lightrag_kwargs,
            )

        return llm_model_func

    def get_vision_model_func(self):
        """
        Get a function compatible with RAG-Anything's vision_model_func parameter.

        Returns:
            Callable that can be used as vision_model_func
        """
        binding = getattr(self.config, "binding", "openai")

        # Use capabilities to determine if provider uses OpenAI-style messages
        uses_openai_style = system_in_messages(binding, self.config.model)

        # For non-OpenAI-compatible providers, use Factory
        if not uses_openai_style:
            from . import factory

            def vision_model_func_via_factory(
                prompt: str,
                system_prompt: Optional[str] = None,
                history_messages: Optional[List[Dict]] = None,
                image_data: Optional[str] = None,
                messages: Optional[List[Dict]] = None,
                **kwargs: Any,
            ):
                # Use factory for unified handling
                return factory.complete(
                    prompt=prompt,
                    system_prompt=system_prompt or "You are a helpful assistant.",
                    model=self.config.model,
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    binding=binding,
                    messages=messages,
                    **kwargs,
                )

            return vision_model_func_via_factory

        # OpenAI-compatible bindings
        from lightrag.llm.openai import openai_complete_if_cache

        # Get api_version once for reuse
        api_version = getattr(self.config, "api_version", None)

        def vision_model_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: Optional[List[Dict]] = None,
            image_data: Optional[str] = None,
            messages: Optional[List[Dict]] = None,
            **kwargs: Any,
        ):
            # Handle multimodal messages
            if messages:
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["messages", "prompt", "system_prompt", "history_messages"]
                }
                lightrag_kwargs = {
                    "messages": messages,
                    "api_key": self.config.api_key,
                    "base_url": self.config.base_url,
                    **clean_kwargs,
                }
                if api_version:
                    lightrag_kwargs["api_version"] = api_version
                return openai_complete_if_cache(
                    self.config.model,
                    prompt="",
                    **lightrag_kwargs,
                )

            # Handle image data
            if image_data:
                # Build image message
                image_message = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                        },
                    ],
                }
                lightrag_kwargs = {
                    "messages": [image_message],
                    "api_key": self.config.api_key,
                    "base_url": self.config.base_url,
                    **kwargs,
                }
                if api_version:
                    lightrag_kwargs["api_version"] = api_version
                return openai_complete_if_cache(
                    self.config.model,
                    prompt="",
                    **lightrag_kwargs,
                )

            # Fallback to regular completion
            lightrag_kwargs = {
                "system_prompt": system_prompt,
                "history_messages": history_messages or [],
                "api_key": self.config.api_key,
                "base_url": self.config.base_url,
                **kwargs,
            }
            if api_version:
                lightrag_kwargs["api_version"] = api_version
            return openai_complete_if_cache(
                self.config.model,
                prompt,
                **lightrag_kwargs,
            )

        return vision_model_func


# Singleton instance
_client: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """
    Get or create the singleton LLM client.

    Args:
        config: Optional configuration. Only used on first call.

    Returns:
        LLMClient instance
    """
    global _client
    if _client is None:
        _client = LLMClient(config)
    return _client


def reset_llm_client():
    """Reset the singleton LLM client."""
    global _client
    _client = None
