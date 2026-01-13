"""
Embedding Provider API Router
==============================

Manages embedding provider configurations via REST API.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.embedding.provider_config import (
    EmbeddingProvider,
    embedding_provider_config_manager,
)

router = APIRouter()


class TestConnectionRequest(BaseModel):
    """Request model for testing embedding provider connection."""

    binding: str
    base_url: str
    api_key: str = ""  # Optional for local providers
    model: str
    dimensions: int = 1024
    requires_key: bool = True


@router.get("/", response_model=List[EmbeddingProvider])
async def list_providers():
    """
    List all configured embedding providers.
    If no providers exist, auto-create one from current .env configuration.
    """
    providers = embedding_provider_config_manager.list_providers()

    if not providers:
        try:
            from src.services.embedding import get_embedding_config

            current_config = get_embedding_config()

            default_provider = EmbeddingProvider(
                name=f"Current ({current_config.binding})",
                binding=current_config.binding,
                base_url=current_config.base_url or "",
                api_key=current_config.api_key or "",
                model=current_config.model,
                dimensions=current_config.dim,
                is_active=True,
                input_type=current_config.input_type,
                normalized=current_config.normalized,
                truncate=current_config.truncate,
            )

            embedding_provider_config_manager.add_provider(default_provider)
            providers = [default_provider]
        except Exception as e:
            print(f"Warning: Could not auto-create provider from .env: {e}")

    return providers


@router.post("/", response_model=EmbeddingProvider)
async def add_provider(provider: EmbeddingProvider):
    """Add a new embedding provider."""
    try:
        return embedding_provider_config_manager.add_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}", response_model=EmbeddingProvider)
async def update_provider(name: str, updates: Dict[str, Any]):
    """Update an existing embedding provider."""
    provider = embedding_provider_config_manager.update_provider(name, updates)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/{name}")
async def delete_provider(name: str):
    """Delete an embedding provider."""
    success = embedding_provider_config_manager.delete_provider(name)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted"}


@router.post("/active", response_model=EmbeddingProvider)
async def set_active_provider(name_payload: Dict[str, str]):
    """Set the active embedding provider."""
    name = name_payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    provider = embedding_provider_config_manager.set_active_provider(name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/test", response_model=Dict[str, Any])
async def test_connection(request: TestConnectionRequest):
    """Test connection to an embedding provider."""
    try:
        from src.services.embedding import reset_embedding_client
        from src.services.embedding.config import EmbeddingConfig

        base_url = request.base_url.rstrip("/")

        api_key_to_use = request.api_key
        if not request.requires_key and not api_key_to_use:
            api_key_to_use = "no-key-required"

        test_config = EmbeddingConfig(
            binding=request.binding,
            model=request.model,
            api_key=api_key_to_use,
            base_url=base_url,
            dim=request.dimensions,
        )

        reset_embedding_client()

        from src.services.embedding.client import EmbeddingClient

        test_client = EmbeddingClient(config=test_config)

        embeddings = await test_client.embed(["Hello, testing embedding service"])

        if not embeddings or not embeddings[0]:
            return {
                "success": False,
                "message": "Connection succeeded but received empty embeddings",
            }

        reset_embedding_client()

        return {
            "success": True,
            "message": "Connection successful",
            "dimensions": len(embeddings[0]),
            "expected_dimensions": request.dimensions,
        }

    except Exception as e:
        from src.services.embedding import reset_embedding_client

        reset_embedding_client()

        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.get("/current/info", response_model=Dict[str, Any])
async def get_current_model_info():
    """Get information about the currently active embedding model."""
    try:
        from src.services.embedding import get_embedding_client, get_embedding_config

        config = get_embedding_config()
        client = get_embedding_client()

        # Get adapter info
        adapter = client.manager.get_active_adapter()
        model_info = adapter.get_model_info()

        return {
            "binding": config.binding,
            "model": config.model,
            "dimensions": config.dim,
            "base_url": config.base_url,
            "max_tokens": config.max_tokens,
            "request_timeout": config.request_timeout,
            "input_type": config.input_type,
            "adapter_info": model_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@router.get("/{name}/models", response_model=Dict[str, Any])
async def list_available_models(name: str):
    """
    List available models for a provider (supports Ollama and LM Studio).

    Args:
        name: Provider name to query

    Returns:
        Dictionary with available models and their information
    """
    try:
        provider = embedding_provider_config_manager.get_provider(name)
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")

        if provider.binding == "ollama":
            import httpx

            base_url = provider.base_url.rstrip("/")

            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    response = await client.get(f"{base_url}/api/tags")
                    response.raise_for_status()
                    data = response.json()

                    embedding_models = []
                    for model in data.get("models", []):
                        model_name = model.get("name", "")
                        if any(
                            keyword in model_name.lower()
                            for keyword in [
                                "embed",
                                "nomic",
                                "minilm",
                                "mpnet",
                                "bge",
                                "mxbai",
                                "snowflake",
                                "arctic",
                            ]
                        ):
                            embedding_models.append(
                                {
                                    "name": model_name,
                                    "size": model.get("size", 0),
                                    "modified": model.get("modified_at", ""),
                                    "digest": model.get("digest", ""),
                                }
                            )

                    return {
                        "provider": name,
                        "binding": provider.binding,
                        "models": embedding_models,
                        "total": len(embedding_models),
                    }

                except httpx.ConnectError:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Cannot connect to Ollama at {base_url}. Ensure Ollama is running.",
                    )
                except httpx.HTTPError as e:
                    raise HTTPException(
                        status_code=503, detail=f"Failed to connect to Ollama: {str(e)}"
                    )

        elif provider.binding == "lm_studio":
            import httpx

            base_url = provider.base_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]

            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    response = await client.get(f"{base_url}/v1/models")
                    response.raise_for_status()
                    data = response.json()

                    models = []
                    for model in data.get("data", []):
                        models.append(
                            {
                                "name": model.get("id", ""),
                                "owned_by": model.get("owned_by", ""),
                                "created": model.get("created", 0),
                            }
                        )

                    return {
                        "provider": name,
                        "binding": provider.binding,
                        "models": models,
                        "total": len(models),
                    }

                except httpx.ConnectError:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Cannot connect to LM Studio at {base_url}. Ensure LM Studio is running.",
                    )
                except httpx.HTTPError as e:
                    raise HTTPException(
                        status_code=503, detail=f"Failed to connect to LM Studio: {str(e)}"
                    )
        else:
            from src.services.embedding.provider import get_embedding_provider_manager

            manager = get_embedding_provider_manager()
            adapter_class = manager.ADAPTER_MAPPING.get(provider.binding)

            if adapter_class and hasattr(adapter_class, "MODELS_INFO"):
                models_info = adapter_class.MODELS_INFO
                models = []

                for model_name, info in models_info.items():
                    if isinstance(info, dict):
                        models.append(
                            {
                                "name": model_name,
                                "dimensions": info.get("default", info.get("dimensions", [])),
                                "info": info,
                            }
                        )
                    else:
                        models.append(
                            {
                                "name": model_name,
                                "dimensions": info,
                            }
                        )

                return {
                    "provider": name,
                    "binding": provider.binding,
                    "models": models,
                    "total": len(models),
                    "note": "These are known models. Provider may support additional models.",
                }

            return {
                "provider": name,
                "binding": provider.binding,
                "models": [],
                "total": 0,
                "note": f"Model listing not supported for {provider.binding}",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_provider_config(provider: EmbeddingProvider):
    """
    Validate a provider configuration without saving it.

    Checks:
    - Server connectivity
    - Model availability
    - Dimension compatibility
    """
    try:
        import httpx

        base_url = provider.base_url.rstrip("/")

        results = {
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        # Check 1: Server connectivity
        try:
            if provider.binding == "ollama":
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{base_url}/api/tags")
                    response.raise_for_status()
                    results["checks"]["server_reachable"] = True
            else:
                results["checks"]["server_reachable"] = True
        except Exception as e:
            results["checks"]["server_reachable"] = False
            results["errors"].append(f"Cannot reach server at {base_url}: {str(e)}")
            results["valid"] = False

        # Check 2: Model availability (Ollama only)
        if provider.binding == "ollama" and results["checks"]["server_reachable"]:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{base_url}/api/tags")
                    data = response.json()

                    available_models = [m.get("name", "") for m in data.get("models", [])]
                    model_available = any(provider.model in m for m in available_models)

                    results["checks"]["model_available"] = model_available

                    if not model_available:
                        results["warnings"].append(
                            f"Model '{provider.model}' not found. Available: {', '.join(available_models[:5])}"
                        )
            except Exception as e:
                results["checks"]["model_available"] = False
                results["warnings"].append(f"Could not verify model availability: {str(e)}")

        # Check 3: Dimension compatibility
        from src.services.embedding.provider import get_embedding_provider_manager

        manager = get_embedding_provider_manager()
        adapter_class = manager.ADAPTER_MAPPING.get(provider.binding)

        if adapter_class and hasattr(adapter_class, "MODELS_INFO"):
            models_info = adapter_class.MODELS_INFO

            if provider.model in models_info:
                expected_dims = models_info[provider.model]

                if isinstance(expected_dims, dict):
                    supported_dims = expected_dims.get("dimensions", [])
                    if isinstance(supported_dims, list):
                        if provider.dimensions not in supported_dims:
                            results["warnings"].append(
                                f"Dimension {provider.dimensions} not in supported list: {supported_dims}"
                            )
                    else:
                        expected = expected_dims.get("default", supported_dims)
                        if provider.dimensions != expected:
                            results["warnings"].append(
                                f"Expected {expected} dimensions, got {provider.dimensions}"
                            )
                else:
                    if provider.dimensions != expected_dims:
                        results["warnings"].append(
                            f"Expected {expected_dims} dimensions, got {provider.dimensions}"
                        )

                results["checks"]["dimensions_compatible"] = len(results["warnings"]) == 0

        # Check 4: API key requirement
        requires_key = provider.binding not in [
            "ollama",
            "lollms",
            "lm_studio",
            "text_generation_webui",
            "localai",
        ]

        if requires_key and not provider.api_key:
            results["errors"].append(f"API key required for {provider.binding}")
            results["valid"] = False

        results["checks"]["api_key_valid"] = not requires_key or bool(provider.api_key)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
