"""
System Status API Router
Manages system status checks and model connection tests
"""

from datetime import datetime
import re
import time

from fastapi import APIRouter
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from pydantic import BaseModel

from src.core.core import get_embedding_config, get_llm_config, get_tts_config

router = APIRouter()


def _uses_max_completion_tokens(model: str) -> bool:
    """
    Check if the model uses max_completion_tokens instead of max_tokens.

    Newer OpenAI models (o1, o3, gpt-4o, gpt-5.x, etc.) require max_completion_tokens
    while older models use max_tokens.
    """
    model_lower = model.lower()

    # Models that require max_completion_tokens:
    # - o1, o3 series (reasoning models)
    # - gpt-4o series
    # - gpt-5.x and later
    patterns = [
        r"^o[13]",  # o1, o3 models
        r"^gpt-4o",  # gpt-4o models
        r"^gpt-[5-9]",  # gpt-5.x and later
        r"^gpt-\d{2,}",  # gpt-10+ (future proofing)
    ]

    for pattern in patterns:
        if re.match(pattern, model_lower):
            return True

    return False


def _get_token_limit_kwargs(model: str, max_tokens: int) -> dict:
    """
    Get the appropriate token limit parameter for the model.

    Args:
        model: The model name
        max_tokens: The desired token limit

    Returns:
        Dictionary with either max_tokens or max_completion_tokens
    """
    if _uses_max_completion_tokens(model):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


class TestResponse(BaseModel):
    success: bool
    message: str
    model: str | None = None
    response_time_ms: float | None = None
    error: str | None = None


@router.get("/status")
async def get_system_status():
    """
    Get overall system status including backend and model configurations

    Returns:
        Dictionary containing status of backend, LLM, embeddings, and TTS
    """
    result = {
        "backend": {"status": "online", "timestamp": datetime.now().isoformat()},
        "llm": {"status": "unknown", "model": None, "testable": True},
        "embeddings": {"status": "unknown", "model": None, "testable": True},
        "tts": {"status": "unknown", "model": None, "testable": True},
    }

    # Check backend status (this endpoint itself proves backend is online)
    result["backend"]["status"] = "online"

    # Check LLM configuration
    try:
        llm_config = get_llm_config()
        result["llm"]["model"] = llm_config.get("model")
        result["llm"]["status"] = "configured"
    except ValueError as e:
        result["llm"]["status"] = "not_configured"
        result["llm"]["error"] = str(e)
    except Exception as e:
        result["llm"]["status"] = "error"
        result["llm"]["error"] = str(e)

    # Check Embeddings configuration
    try:
        embedding_config = get_embedding_config()
        result["embeddings"]["model"] = embedding_config.get("model")
        result["embeddings"]["status"] = "configured"
    except ValueError as e:
        result["embeddings"]["status"] = "not_configured"
        result["embeddings"]["error"] = str(e)
    except Exception as e:
        result["embeddings"]["status"] = "error"
        result["embeddings"]["error"] = str(e)

    # Check TTS configuration
    try:
        tts_config = get_tts_config()
        result["tts"]["model"] = tts_config.get("model")
        result["tts"]["status"] = "configured"
    except ValueError as e:
        result["tts"]["status"] = "not_configured"
        result["tts"]["error"] = str(e)
    except Exception as e:
        result["tts"]["status"] = "error"
        result["tts"]["error"] = str(e)

    return result


@router.post("/test/llm", response_model=TestResponse)
async def test_llm_connection():
    """
    Test LLM model connection by sending a simple completion request

    Returns:
        Test result with success status and response time
    """
    start_time = time.time()

    try:
        llm_config = get_llm_config()
        model = llm_config["model"]
        base_url = llm_config["base_url"].rstrip("/")

        # Sanitize Base URL (remove /chat/completions suffix if present)
        for suffix in ["/chat/completions", "/completions"]:
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]

        # Handle API Key (inject dummy if missing for local LLMs)
        api_key = llm_config["api_key"]
        if not api_key:
            api_key = "sk-no-key-required"

        # Send a minimal test request with a prompt that guarantees output
        test_prompt = "Say 'OK' to confirm you are working."
        token_kwargs = _get_token_limit_kwargs(model, max_tokens=20)
        response = await openai_complete_if_cache(
            model=model,
            prompt=test_prompt,
            system_prompt="You are a helpful assistant. Respond briefly.",
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
            **token_kwargs,  # Use appropriate token param for model
        )

        response_time = (time.time() - start_time) * 1000

        if response and len(response.strip()) > 0:
            return TestResponse(
                success=True,
                message="LLM connection successful",
                model=model,
                response_time_ms=round(response_time, 2),
            )
        return TestResponse(
            success=False,
            message="LLM connection failed: Empty response",
            model=model,
            error="Empty response from API",
        )

    except ValueError as e:
        return TestResponse(success=False, message=f"LLM configuration error: {e!s}", error=str(e))
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return TestResponse(
            success=False,
            message=f"LLM connection failed: {e!s}",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )


@router.post("/test/embeddings", response_model=TestResponse)
async def test_embeddings_connection():
    """
    Test Embeddings model connection by sending a simple embedding request

    Returns:
        Test result with success status and response time
    """
    start_time = time.time()

    try:
        embedding_config = get_embedding_config()
        model = embedding_config["model"]
        base_url = embedding_config["base_url"].rstrip("/")

        # Sanitize Base URL (remove /embeddings suffix if present, though less common)
        # OpenAI client handles /embeddings automatically

        # Handle API Key
        api_key = embedding_config["api_key"]
        if not api_key:
            api_key = "sk-no-key-required"

        # Send a minimal test request
        test_texts = ["test"]
        # openai_embed returns a coroutine, so we need to await it
        embeddings = await openai_embed(
            texts=test_texts, model=model, api_key=api_key, base_url=base_url
        )

        response_time = (time.time() - start_time) * 1000

        if embeddings is not None and len(embeddings) > 0 and len(embeddings[0]) > 0:
            return TestResponse(
                success=True,
                message="Embeddings connection successful",
                model=model,
                response_time_ms=round(response_time, 2),
            )
        return TestResponse(
            success=False,
            message="Embeddings connection failed: Empty response",
            model=model,
            error="Empty embedding vector",
        )

    except ValueError as e:
        return TestResponse(
            success=False, message=f"Embeddings configuration error: {e!s}", error=str(e)
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return TestResponse(
            success=False,
            message=f"Embeddings connection failed: {e!s}",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )


@router.post("/test/tts", response_model=TestResponse)
async def test_tts_connection():
    """
    Test TTS model connection by checking configuration

    Note: We don't actually generate audio for testing to avoid unnecessary API calls.
    We only verify the configuration is valid.

    Returns:
        Test result with success status
    """
    start_time = time.time()

    try:
        tts_config = get_tts_config()
        model = tts_config["model"]
        api_key = tts_config["api_key"]
        base_url = tts_config["base_url"]

        # Verify configuration is complete
        if not model or not api_key or not base_url:
            return TestResponse(
                success=False,
                message="TTS configuration incomplete",
                model=model,
                error="Missing required configuration",
            )

        # For TTS, we just verify the config is valid
        # Actual audio generation would be expensive, so we skip it
        response_time = (time.time() - start_time) * 1000

        return TestResponse(
            success=True,
            message="TTS configuration valid",
            model=model,
            response_time_ms=round(response_time, 2),
        )

    except ValueError as e:
        return TestResponse(success=False, message=f"TTS configuration error: {e!s}", error=str(e))
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return TestResponse(
            success=False,
            message=f"TTS connection check failed: {e!s}",
            response_time_ms=round(response_time, 2),
            error=str(e),
        )
