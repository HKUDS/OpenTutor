import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict

import yaml


class ConfigManager:
    """Thread-safe manager for config/main.yaml and .env."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = self.project_root / "config" / "main.yaml"
        self._config_cache = None
        self._last_mtime = 0
        self._initialized = True

    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load config/main.yaml with file-mtime caching."""
        if not self.config_path.exists():
            return {}

        current_mtime = self.config_path.stat().st_mtime

        if self._config_cache is None or force_reload or current_mtime > self._last_mtime:
            with self._lock:
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        self._config_cache = yaml.safe_load(f) or {}
                    self._last_mtime = current_mtime
                except Exception as e:
                    print(f"Error loading config: {e}")
                    return {}

        return self._config_cache.copy()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save config to main.yaml with deep merge."""
        try:
            current_config = self.load_config(force_reload=True)

            def deep_update(target, source):
                for key, value in source.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        deep_update(target[key], value)
                    else:
                        target[key] = value

            deep_update(current_config, config)

            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with self._lock:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        current_config,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

                self._config_cache = current_config
                self._last_mtime = self.config_path.stat().st_mtime

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_env_info(self) -> Dict[str, str]:
        """
        Get actual LLM and Embedding configuration.

        Strategy:
        1. Try initialized services (most accurate)
        2. Fallback to .env file parsing
        3. Last resort: os.environ
        """
        env_vars = self._read_env_file()
        llm_config = self._get_safe_llm_config(env_vars)
        emb_config = self._get_safe_embedding_config(env_vars)

        return {
            "llm_model": llm_config["model"],
            "llm_binding": llm_config["binding"],
            "embedding_model": emb_config["model"],
            "embedding_binding": emb_config["binding"],
            "embedding_dim": str(emb_config["dim"]),
        }

    def _read_env_file(self) -> Dict[str, str]:
        """Parse .env file directly."""
        env_vars = {}
        env_path = self.project_root / ".env"

        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            env_vars[key.strip()] = val.strip().strip('"').strip("'")
            except Exception as e:
                print(f"Warning: Error reading .env: {e}")

        return env_vars

    def _get_safe_llm_config(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Get LLM config with fallback chain."""
        try:
            from src.services.llm import get_llm_config

            cfg = get_llm_config()
            return {"model": cfg.model, "binding": cfg.binding}
        except Exception as e:
            # Fallback to env_vars (parsed from .env file)
            model = env_vars.get("LLM_MODEL") or os.environ.get("LLM_MODEL", "unknown")
            binding = env_vars.get("LLM_BINDING") or os.environ.get("LLM_BINDING", "openai")
            return {"model": model, "binding": binding}

    def _get_safe_embedding_config(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Get Embedding config with fallback chain."""
        try:
            from src.services.embedding import get_embedding_config

            cfg = get_embedding_config()
            return {
                "model": cfg.model,
                "binding": cfg.binding,
                "dim": cfg.dim,
            }
        except Exception as e:
            # Fallback to env_vars (parsed from .env file)
            dim_str = env_vars.get("EMBEDDING_DIM") or os.environ.get("EMBEDDING_DIM", "1536")
            try:
                dim = int(dim_str)
            except (ValueError, TypeError):
                dim = 1536

            model = env_vars.get("EMBEDDING_MODEL") or os.environ.get("EMBEDDING_MODEL", "unknown")
            binding = env_vars.get("EMBEDDING_BINDING") or os.environ.get(
                "EMBEDDING_BINDING", "openai"
            )

            return {
                "model": model,
                "binding": binding,
                "dim": dim,
            }
