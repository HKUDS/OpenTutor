"""
Embedding Provider Configuration Management
============================================

Manages embedding provider configurations, persisting them to a JSON file.
Similar to LLM provider management but for embedding services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

USER_DATA_DIR = Path("./data/user")
PROVIDERS_FILE = USER_DATA_DIR / "embedding_providers.json"


class EmbeddingProvider(BaseModel):
    """
    Configuration model for a single embedding provider.
    """

    name: str = Field(..., description="Unique name for the provider configuration")
    binding: str = Field(..., description="Provider type (openai, jina, cohere, ollama, etc.)")
    base_url: str = Field(..., description="API endpoint URL")
    api_key: str = Field(default="", description="API Key (optional for local providers)")
    api_version: Optional[str] = Field(
        default=None, description="API Version (required for Azure OpenAI)"
    )
    model: str = Field(..., description="Model name to use")
    dimensions: int = Field(..., description="Embedding vector dimensions")
    is_active: bool = Field(default=False, description="Whether this provider is currently active")

    # Optional advanced settings for some specific providers, view each api references for details
    input_type: Optional[str] = Field(
        default=None, description="Input type for task-aware embeddings"
    )
    normalized: bool = Field(default=True, description="L2 normalization")
    truncate: bool = Field(default=True, description="Truncate long texts")

    class Config:
        populate_by_name = True


class EmbeddingProviderConfigManager:
    """
    Manages embedding provider configurations, persisting them to a JSON file.
    """

    def __init__(self, storage_path: Path = PROVIDERS_FILE):
        self.storage_path = storage_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Ensure the storage directory and file exist."""
        if not self.storage_path.parent.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.storage_path.exists():
            self._save_providers([])

    def _load_providers(self) -> List[Dict[str, Any]]:
        """Load raw provider data from JSON."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_providers(self, providers: List[Dict[str, Any]]):
        """Save raw provider data to JSON."""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(providers, f, indent=2, ensure_ascii=False)

    def list_providers(self) -> List[EmbeddingProvider]:
        """List all configured providers."""
        raw_list = self._load_providers()
        return [EmbeddingProvider(**p) for p in raw_list]

    def get_provider(self, name: str) -> Optional[EmbeddingProvider]:
        """Get a specific provider by name."""
        providers = self.list_providers()
        for p in providers:
            if p.name == name:
                return p
        return None

    def get_active_provider(self) -> Optional[EmbeddingProvider]:
        """Get the currently active provider."""
        providers = self.list_providers()
        for p in providers:
            if p.is_active:
                return p
        return None

    def add_provider(self, provider: EmbeddingProvider) -> EmbeddingProvider:
        """Add a new provider. If name exists, raises ValueError."""
        providers = self.list_providers()
        if any(p.name == provider.name for p in providers):
            raise ValueError(f"Provider with name '{provider.name}' already exists.")

        # If this is the first provider or set as active, handle activation logic
        if not providers or provider.is_active:
            # Deactivate others if this one is active
            if provider.is_active:
                for p in providers:
                    p.is_active = False
            else:
                # If it's the only one, make it active by default
                if not providers:
                    provider.is_active = True

        providers.append(provider)
        self._save_providers([p.model_dump() for p in providers])
        return provider

    def update_provider(self, name: str, updates: Dict[str, Any]) -> Optional[EmbeddingProvider]:
        """Update an existing provider."""
        providers = self.list_providers()
        target_idx = -1

        for i, p in enumerate(providers):
            if p.name == name:
                target_idx = i
                break

        if target_idx == -1:
            return None

        # Update fields
        current_data = providers[target_idx].model_dump()
        current_data.update(updates)
        updated_provider = EmbeddingProvider(**current_data)

        # Handle activation logic if changing is_active
        if updated_provider.is_active:
            for i, p in enumerate(providers):
                if i != target_idx:
                    p.is_active = False

        providers[target_idx] = updated_provider
        self._save_providers([p.model_dump() for p in providers])
        return updated_provider

    def delete_provider(self, name: str) -> bool:
        """Delete a provider."""
        providers = self.list_providers()
        initial_len = len(providers)
        providers = [p for p in providers if p.name != name]

        if len(providers) < initial_len:
            self._save_providers([p.model_dump() for p in providers])
            return True
        return False

    def set_active_provider(self, name: str) -> Optional[EmbeddingProvider]:
        """Set a provider as active and deactivate others."""
        providers = self.list_providers()
        activated = None

        found = False
        for p in providers:
            if p.name == name:
                p.is_active = True
                activated = p
                found = True
            else:
                p.is_active = False

        if found:
            self._save_providers([p.model_dump() for p in providers])
            return activated
        return None


# Global instance
embedding_provider_config_manager = EmbeddingProviderConfigManager()


__all__ = [
    "EmbeddingProvider",
    "EmbeddingProviderConfigManager",
    "embedding_provider_config_manager",
]
