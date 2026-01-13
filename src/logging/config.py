"""
Logging Configuration
=====================

Configuration settings for the logging system.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LoggingConfig:
    """Configuration for the logging system."""

    # Output settings
    console_output: bool = True
    file_output: bool = True

    # Log levels
    console_level: str = "INFO"
    file_level: str = "DEBUG"

    # Log directory (relative to project root or absolute)
    log_dir: Optional[str] = None

    # File rotation settings
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    # WebSocket streaming
    websocket_enabled: bool = True
    websocket_queue_size: int = 1000

    # LightRAG forwarding
    lightrag_forwarding_enabled: bool = True
    lightrag_min_level: str = "INFO"
    lightrag_add_prefix: bool = True


def get_default_log_dir() -> Path:
    """Get the default log directory."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "user" / "logs"


def load_logging_config() -> LoggingConfig:
    """
    Load logging configuration from config files.

    Returns:
        LoggingConfig instance with loaded or default values.
    """
    try:
        from src.services.config import get_path_from_config, load_config_with_main

        project_root = Path(__file__).resolve().parent.parent.parent
        config = load_config_with_main("solve_config.yaml", project_root)

        logging_config = config.get("logging", {})

        return LoggingConfig(
            console_output=logging_config.get("console_output", True),
            file_output=logging_config.get("file_output", True),
            console_level=logging_config.get("console_level", "INFO"),
            file_level=logging_config.get("file_level", "DEBUG"),
            log_dir=get_path_from_config(config, "user_log_dir"),
            lightrag_forwarding_enabled=logging_config.get("lightrag_forwarding", {}).get(
                "enabled", True
            ),
            lightrag_min_level=logging_config.get("lightrag_forwarding", {}).get(
                "min_level", "INFO"
            ),
            lightrag_add_prefix=logging_config.get("lightrag_forwarding", {}).get(
                "add_prefix", True
            ),
        )
    except Exception:
        return LoggingConfig()
