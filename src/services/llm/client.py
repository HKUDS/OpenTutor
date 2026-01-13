"""
LLM Client
==========

Unified LLM client for all DeepTutor services.
"""

from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .config import LLMConfig, get_llm_config


class LLMClient:
    """
    Unified LLM client for all services.

    Wraps the underlying LLM API (OpenAI-compatible) with a consistent interface.
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
        Call LLM completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            history: Optional conversation history
            **kwargs: Additional arguments passed to the API

        Returns:
            LLM response text
        """
        from lightrag.llm.openai import openai_complete_if_cache

        return await openai_complete_if_cache(
            self.config.model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history or [],
            api_key=self.config.api_key,
            base_url=self.config.base_url,
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
        from lightrag.llm.openai import openai_complete_if_cache

        def llm_model_func(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: Optional[List[Dict]] = None,
            **kwargs: Any,
        ):
            return openai_complete_if_cache(
                self.config.model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                **kwargs,
            )

        return llm_model_func

    def get_vision_model_func(self):
        """
        Get a function compatible with RAG-Anything's vision_model_func parameter.

        Returns:
            Callable that can be used as vision_model_func
        """
        from lightrag.llm.openai import openai_complete_if_cache

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
                return openai_complete_if_cache(
                    self.config.model,
                    prompt="",
                    messages=messages,
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    **clean_kwargs,
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
                return openai_complete_if_cache(
                    self.config.model,
                    prompt="",
                    messages=[image_message],
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    **kwargs,
                )

            # Fallback to regular completion
            return openai_complete_if_cache(
                self.config.model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                **kwargs,
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
