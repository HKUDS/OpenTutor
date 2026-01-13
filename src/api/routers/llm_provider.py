from typing import Any, Dict, List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.llm import (
    complete as llm_complete,
)
from src.services.llm import (
    fetch_models as llm_fetch_models,
)
from src.services.llm import (
    get_mode_info,
    get_provider_presets,
    sanitize_url,
)
from src.services.llm.provider import LLMProvider, provider_manager

router = APIRouter()


class TestConnectionRequest(BaseModel):
    binding: str
    base_url: str
    api_key: str
    model: str
    requires_key: bool = True  # Default to True for backward compatibility
    provider_type: Literal["api", "local"] = "local"  # New field


@router.get("/", response_model=List[LLMProvider])
async def list_providers():
    """List all configured LLM providers."""
    return provider_manager.list_providers()


@router.post("/", response_model=LLMProvider)
async def add_provider(provider: LLMProvider):
    """Add a new LLM provider."""
    try:
        return provider_manager.add_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}/", response_model=LLMProvider)
async def update_provider(name: str, updates: Dict[str, Any]):
    """Update an existing LLM provider."""
    provider = provider_manager.update_provider(name, updates)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/")
async def delete_provider_by_query(name: str):
    """Delete an LLM provider (query param version)."""
    success = provider_manager.delete_provider(name)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted"}


@router.delete("/{name}/")
async def delete_provider(name: str):
    """Delete an LLM provider."""
    success = provider_manager.delete_provider(name)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted"}


@router.post("/active/", response_model=LLMProvider)
async def set_active_provider(name_payload: Dict[str, str]):
    """Set the active LLM provider."""
    name = name_payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    provider = provider_manager.set_active_provider(name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/test/", response_model=Dict[str, Any])
async def test_connection(request: TestConnectionRequest):
    """Test connection to an LLM provider."""
    try:
        # Use unified sanitize_url for consistent URL handling
        # Handles Ollama, LM Studio, and other local servers
        base_url = sanitize_url(request.base_url)

        # Simple test prompt
        if not request.requires_key and not request.api_key:
            # Inject dummy key if not required and not provided
            # This satisfies the OpenAI client library which demands a key
            api_key_to_use = "sk-no-key-required"
        else:
            api_key_to_use = request.api_key

        response = await llm_complete(
            model=request.model,
            prompt="Hello, are you working?",
            system_prompt="You are a helpful assistant. Reply with 'Yes'.",
            api_key=api_key_to_use,
            base_url=base_url,
            binding=request.binding,
            max_tokens=200,
        )
        return {"success": True, "message": "Connection successful", "response": response}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/models/", response_model=Dict[str, Any])
async def fetch_available_models(request: TestConnectionRequest):
    """Fetch available models from the provider."""
    try:
        # Use unified sanitize_url for consistent URL handling
        base_url = sanitize_url(request.base_url)

        models = await llm_fetch_models(
            binding=request.binding,
            base_url=base_url,
            api_key=request.api_key if request.requires_key else None,
        )
        return {"success": True, "models": models}
    except Exception as e:
        return {"success": False, "message": f"Failed to fetch models: {str(e)}"}


# ==================== LLM Mode Endpoints ====================


@router.get("/mode/", response_model=Dict[str, Any])
async def get_llm_mode_info():
    """
    Get information about the current LLM configuration mode.

    Returns:
        Dict containing:
        - mode: Current deployment mode ('api', 'local', or 'hybrid')
        - active_provider: Active provider info (if any)
        - env_configured: Whether env vars are properly configured
        - effective_source: Which config source is being used ('env' or 'provider')
    """
    return get_mode_info()


@router.get("/presets/", response_model=Dict[str, Any])
async def get_presets():
    """
    Get provider presets for API and Local providers.

    Returns:
        Dict containing:
        - api: API provider presets (OpenAI, Anthropic, DeepSeek, etc.)
        - local: Local provider presets (Ollama, LM Studio, vLLM, etc.)
    """
    return get_provider_presets()
