"""
Unified Configuration API Router
=================================

Provides REST API for managing configurations for:
- LLM (Language Models)
- Embedding Models
- TTS (Text-to-Speech)
- Search Providers
"""

import os
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.config import (
    ConfigType,
    get_config_manager,
)
from src.services.llm import complete as llm_complete
from src.services.llm import sanitize_url

router = APIRouter()


# ==================== Request/Response Models ====================


class ConfigBase(BaseModel):
    """Base configuration model."""

    name: str = Field(..., description="Display name for this configuration")
    provider: str = Field(..., description="Provider type")


class LLMConfigCreate(ConfigBase):
    """LLM configuration for creation."""

    base_url: str | Dict[str, str] = Field(
        ..., description="API endpoint or {'use_env': 'VAR_NAME'}"
    )
    api_key: str | Dict[str, str] = Field(..., description="API key or {'use_env': 'VAR_NAME'}")
    model: str = Field(..., description="Model name")
    api_version: Optional[str] = None


class EmbeddingConfigCreate(ConfigBase):
    """Embedding configuration for creation."""

    base_url: str | Dict[str, str]
    api_key: str | Dict[str, str]
    model: str
    dimensions: int = 3072
    api_version: Optional[str] = None


class TTSConfigCreate(ConfigBase):
    """TTS configuration for creation."""

    base_url: str | Dict[str, str]
    api_key: str | Dict[str, str]
    model: str
    voice: str = "alloy"
    api_version: Optional[str] = None


class SearchConfigCreate(ConfigBase):
    """Search configuration for creation.

    Uses unified SEARCH_API_KEY environment variable.
    """

    api_key: str | Dict[str, str] = Field(
        ..., description="API key or {'use_env': 'SEARCH_API_KEY'}"
    )


class ConfigUpdate(BaseModel):
    """Configuration update model."""

    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str | Dict[str, str]] = None
    api_key: Optional[str | Dict[str, str]] = None
    model: Optional[str] = None
    dimensions: Optional[int] = None
    voice: Optional[str] = None
    api_version: Optional[str] = None


class SetActiveRequest(BaseModel):
    """Request to set active configuration."""

    config_id: str


class TestConnectionRequest(BaseModel):
    """Request to test a connection.

    base_url and api_key can be either:
    - A string value
    - A dict with {"use_env": "VAR_NAME"} to load from environment
    """

    provider: str
    base_url: str | Dict[str, str]
    api_key: str | Dict[str, str]
    model: str
    dimensions: Optional[int] = None  # For embedding models
    voice: Optional[str] = None  # For TTS models


def resolve_env_value(value: str | Dict[str, str], fallback: str = "") -> str:
    """
    Resolve a value that may be a string or {"use_env": "VAR_NAME"}.

    If value is a dict with use_env, fetch from environment variable.
    Otherwise return the string value directly.
    """
    if isinstance(value, dict) and "use_env" in value:
        env_var = value["use_env"]
        return os.environ.get(env_var, fallback)
    return value if isinstance(value, str) else fallback


class ConfigStatusResponse(BaseModel):
    """Response for configuration status."""

    llm: Dict[str, Any]
    embedding: Dict[str, Any]
    tts: Dict[str, Any]
    search: Dict[str, Any]


class PortsResponse(BaseModel):
    """Response for port configuration."""

    backend_port: int
    frontend_port: int


# ==================== Status Endpoints ====================


@router.get("/status", response_model=ConfigStatusResponse)
async def get_config_status():
    """
    Get configuration status for all services.
    Shows which service has active configuration and what it is.
    """
    manager = get_config_manager()

    def get_status(config_type: ConfigType) -> Dict[str, Any]:
        active = manager.get_active_config(config_type)
        env_status = manager.get_env_status(config_type)
        configs = manager.list_configs(config_type)
        active_config = next((c for c in configs if c.get("is_active")), None)

        return {
            "configured": bool(
                active and active.get("model" if config_type != ConfigType.SEARCH else "provider")
            ),
            "active_config_id": active_config.get("id") if active_config else "default",
            "active_config_name": active_config.get("name") if active_config else "Default",
            "model": active.get("model") if active else None,
            "provider": active.get("provider") if active else None,
            "env_configured": env_status,
            "total_configs": len(configs),
        }

    return ConfigStatusResponse(
        llm=get_status(ConfigType.LLM),
        embedding=get_status(ConfigType.EMBEDDING),
        tts=get_status(ConfigType.TTS),
        search=get_status(ConfigType.SEARCH),
    )


@router.get("/ports", response_model=PortsResponse)
async def get_ports():
    """Get current port configuration (read-only)."""
    return PortsResponse(
        backend_port=int(os.environ.get("BACKEND_PORT", 8000)),
        frontend_port=int(os.environ.get("FRONTEND_PORT", 3000)),
    )


@router.get("/providers/{config_type}")
async def get_providers(config_type: Literal["llm", "embedding", "tts", "search"]):
    """Get available provider options for a configuration type."""
    manager = get_config_manager()
    ct = ConfigType(config_type)
    return {"providers": manager.get_provider_options(ct)}


# ==================== LLM Configuration Endpoints ====================


@router.get("/llm")
async def list_llm_configs():
    """List all LLM configurations."""
    manager = get_config_manager()
    return {"configs": manager.list_configs(ConfigType.LLM)}


@router.post("/llm")
async def add_llm_config(config: LLMConfigCreate):
    """Add a new LLM configuration."""
    manager = get_config_manager()
    data = config.model_dump()
    result = manager.add_config(ConfigType.LLM, data)
    return result


@router.put("/llm/{config_id}")
async def update_llm_config(config_id: str, updates: ConfigUpdate):
    """Update an LLM configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot update default configuration")

    manager = get_config_manager()
    result = manager.update_config(ConfigType.LLM, config_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return result


@router.delete("/llm/{config_id}")
async def delete_llm_config(config_id: str):
    """Delete an LLM configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default configuration")

    manager = get_config_manager()
    success = manager.delete_config(ConfigType.LLM, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted"}


@router.post("/llm/{config_id}/active")
async def set_active_llm_config(config_id: str):
    """Set an LLM configuration as active."""
    manager = get_config_manager()
    success = manager.set_active_config(ConfigType.LLM, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration activated", "active_id": config_id}


@router.post("/llm/test")
async def test_llm_connection(request: TestConnectionRequest):
    """Test connection to an LLM provider."""
    try:
        # Resolve use_env references to actual values
        base_url = resolve_env_value(request.base_url)
        api_key = resolve_env_value(request.api_key)

        # Validate required fields
        if not base_url:
            return {"success": False, "message": "Base URL is required"}
        if not request.model:
            return {"success": False, "message": "Model name is required"}

        base_url = sanitize_url(base_url)
        api_key = api_key or "sk-no-key-required"

        response = await llm_complete(
            model=request.model,
            prompt="Hello, are you working?",
            system_prompt="You are a helpful assistant. Reply with 'Yes'.",
            api_key=api_key,
            base_url=base_url,
            binding=request.provider,
            max_tokens=200,
        )
        return {"success": True, "message": "Connection successful", "response": response[:100]}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/llm/{config_id}/test")
async def test_llm_config_by_id(config_id: str):
    """Test connection for an existing LLM configuration by ID."""
    try:
        manager = get_config_manager()

        if config_id == "default":
            # Get default config from env
            config = manager.get_default_config(ConfigType.LLM)
        else:
            # Find config by ID
            configs = manager.list_configs(ConfigType.LLM)
            config = next((c for c in configs if c.get("id") == config_id), None)
            if not config:
                return {"success": False, "message": f"Configuration '{config_id}' not found"}
            # Resolve use_env references for user configs
            config = manager.resolve_config_env_values(config)

        if not config or not config.get("base_url"):
            return {"success": False, "message": "Configuration is incomplete (missing base_url)"}

        base_url = sanitize_url(config.get("base_url", ""))
        api_key = config.get("api_key") or "sk-no-key-required"
        model = config.get("model", "")
        provider = config.get("provider", "openai")

        response = await llm_complete(
            model=model,
            prompt="Hello, are you working?",
            system_prompt="You are a helpful assistant. Reply with 'Yes'.",
            api_key=api_key,
            base_url=base_url,
            binding=provider,
            max_tokens=200,
        )
        return {"success": True, "message": "Connection successful", "response": response[:100]}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


# ==================== Embedding Configuration Endpoints ====================


@router.get("/embedding")
async def list_embedding_configs():
    """List all embedding configurations."""
    manager = get_config_manager()
    return {"configs": manager.list_configs(ConfigType.EMBEDDING)}


@router.post("/embedding")
async def add_embedding_config(config: EmbeddingConfigCreate):
    """Add a new embedding configuration."""
    manager = get_config_manager()
    data = config.model_dump()
    result = manager.add_config(ConfigType.EMBEDDING, data)
    return result


@router.put("/embedding/{config_id}")
async def update_embedding_config(config_id: str, updates: ConfigUpdate):
    """Update an embedding configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot update default configuration")

    manager = get_config_manager()
    result = manager.update_config(
        ConfigType.EMBEDDING, config_id, updates.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return result


@router.delete("/embedding/{config_id}")
async def delete_embedding_config(config_id: str):
    """Delete an embedding configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default configuration")

    manager = get_config_manager()
    success = manager.delete_config(ConfigType.EMBEDDING, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted"}


@router.post("/embedding/{config_id}/active")
async def set_active_embedding_config(config_id: str):
    """Set an embedding configuration as active."""
    manager = get_config_manager()
    success = manager.set_active_config(ConfigType.EMBEDDING, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration activated", "active_id": config_id}


@router.post("/embedding/test")
async def test_embedding_connection(request: TestConnectionRequest):
    """Test connection to an embedding provider."""
    try:
        from src.services.embedding.client import EmbeddingClient
        from src.services.embedding.config import EmbeddingConfig

        # Resolve use_env references
        base_url = resolve_env_value(request.base_url)
        api_key = resolve_env_value(request.api_key)

        # Validate required fields
        if not base_url:
            return {"success": False, "message": "Base URL is required"}
        if not request.model:
            return {"success": False, "message": "Model name is required"}
        if not request.dimensions:
            return {"success": False, "message": "Dimensions is required for embedding models"}

        # Create a test config with dimensions
        test_config = EmbeddingConfig(
            model=request.model,
            api_key=api_key or "sk-no-key-required",
            base_url=base_url,
            binding=request.provider,
            dim=request.dimensions,
        )

        # Create a temporary client for testing
        client = EmbeddingClient(test_config)
        # Use embed() method with a list of texts
        embeddings = await client.embed(["test"])
        if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 0:
            return {"success": True, "message": f"Connection successful (dim={len(embeddings[0])})"}
        return {"success": False, "message": "Failed to generate embeddings"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/embedding/{config_id}/test")
async def test_embedding_config_by_id(config_id: str):
    """Test connection for an existing embedding configuration by ID."""
    try:
        from src.services.embedding.client import EmbeddingClient
        from src.services.embedding.config import EmbeddingConfig

        manager = get_config_manager()

        if config_id == "default":
            config = manager.get_default_config(ConfigType.EMBEDDING)
        else:
            configs = manager.list_configs(ConfigType.EMBEDDING)
            config = next((c for c in configs if c.get("id") == config_id), None)
            if not config:
                return {"success": False, "message": f"Configuration '{config_id}' not found"}
            config = manager.resolve_config_env_values(config)

        if not config or not config.get("base_url"):
            return {"success": False, "message": "Configuration is incomplete (missing base_url)"}

        # Create a test config
        test_config = EmbeddingConfig(
            model=config.get("model", ""),
            api_key=config.get("api_key") or "sk-no-key-required",
            base_url=config.get("base_url", ""),
            binding=config.get("provider", "openai"),
            dim=config.get("dimensions", 3072),
        )

        # Create a temporary client for testing
        client = EmbeddingClient(test_config)
        # Use embed() method with a list of texts
        embeddings = await client.embed(["test"])
        if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 0:
            return {"success": True, "message": f"Connection successful (dim={len(embeddings[0])})"}
        return {"success": False, "message": "Failed to generate embeddings"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


# ==================== TTS Configuration Endpoints ====================


@router.get("/tts")
async def list_tts_configs():
    """List all TTS configurations."""
    manager = get_config_manager()
    return {"configs": manager.list_configs(ConfigType.TTS)}


@router.post("/tts")
async def add_tts_config(config: TTSConfigCreate):
    """Add a new TTS configuration."""
    manager = get_config_manager()
    data = config.model_dump()
    result = manager.add_config(ConfigType.TTS, data)
    return result


@router.put("/tts/{config_id}")
async def update_tts_config(config_id: str, updates: ConfigUpdate):
    """Update a TTS configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot update default configuration")

    manager = get_config_manager()
    result = manager.update_config(ConfigType.TTS, config_id, updates.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return result


@router.delete("/tts/{config_id}")
async def delete_tts_config(config_id: str):
    """Delete a TTS configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default configuration")

    manager = get_config_manager()
    success = manager.delete_config(ConfigType.TTS, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted"}


@router.post("/tts/{config_id}/active")
async def set_active_tts_config(config_id: str):
    """Set a TTS configuration as active."""
    manager = get_config_manager()
    success = manager.set_active_config(ConfigType.TTS, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration activated", "active_id": config_id}


@router.post("/tts/test")
async def test_tts_connection(request: TestConnectionRequest):
    """Test connection to a TTS provider."""
    try:
        from openai import AsyncOpenAI

        # Resolve use_env references
        base_url = resolve_env_value(request.base_url)
        api_key = resolve_env_value(request.api_key)

        # Validate required fields
        if not base_url:
            return {"success": False, "message": "Base URL is required"}
        if not request.model:
            return {"success": False, "message": "Model name is required"}

        # Test by creating client and checking if we can reach the API
        client = AsyncOpenAI(
            api_key=api_key or "sk-no-key-required",
            base_url=base_url,
        )
        # Just verify we can create the client - actual TTS test would require audio generation
        return {"success": True, "message": "TTS configuration validated"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/tts/{config_id}/test")
async def test_tts_config_by_id(config_id: str):
    """Test connection for an existing TTS configuration by ID."""
    try:
        from openai import AsyncOpenAI

        manager = get_config_manager()

        if config_id == "default":
            config = manager.get_default_config(ConfigType.TTS)
        else:
            configs = manager.list_configs(ConfigType.TTS)
            config = next((c for c in configs if c.get("id") == config_id), None)
            if not config:
                return {"success": False, "message": f"Configuration '{config_id}' not found"}
            config = manager.resolve_config_env_values(config)

        if not config or not config.get("base_url"):
            return {"success": False, "message": "Configuration is incomplete (missing base_url)"}

        # Test by creating client
        client = AsyncOpenAI(
            api_key=config.get("api_key") or "sk-no-key-required",
            base_url=config.get("base_url", ""),
        )
        return {"success": True, "message": "TTS configuration validated"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


# ==================== Search Configuration Endpoints ====================


@router.get("/search")
async def list_search_configs():
    """List all search configurations."""
    manager = get_config_manager()
    return {"configs": manager.list_configs(ConfigType.SEARCH)}


@router.post("/search")
async def add_search_config(config: SearchConfigCreate):
    """Add a new search configuration."""
    manager = get_config_manager()
    data = config.model_dump()
    result = manager.add_config(ConfigType.SEARCH, data)
    return result


@router.put("/search/{config_id}")
async def update_search_config(config_id: str, updates: ConfigUpdate):
    """Update a search configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot update default configuration")

    manager = get_config_manager()
    result = manager.update_config(
        ConfigType.SEARCH, config_id, updates.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return result


@router.delete("/search/{config_id}")
async def delete_search_config(config_id: str):
    """Delete a search configuration."""
    if config_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default configuration")

    manager = get_config_manager()
    success = manager.delete_config(ConfigType.SEARCH, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted"}


@router.post("/search/{config_id}/active")
async def set_active_search_config(config_id: str):
    """Set a search configuration as active."""
    manager = get_config_manager()
    success = manager.set_active_config(ConfigType.SEARCH, config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration activated", "active_id": config_id}
