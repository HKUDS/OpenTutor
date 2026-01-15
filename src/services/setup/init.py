#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Setup and Initialization
Combines user directory initialization and port configuration management.
"""

import json
import os
from pathlib import Path

from src.logging import get_logger
from src.services.config import load_config_with_main

# Initialize logger for setup operations
_setup_logger = None


def _get_setup_logger():
    """Get logger for setup operations"""
    global _setup_logger
    if _setup_logger is None:
        _setup_logger = get_logger("Setup")
    return _setup_logger


# ============================================================================
# User Directory Initialization (from user_dir_init.py)
# ============================================================================


def init_user_directories(project_root: Path | None = None) -> None:
    """
    Initialize user data directories if they don't exist.

    Creates the following directory structure:
    data/user/
    ├── solve/              # Problem solving outputs
    ├── question/           # Question generation outputs
    ├── research/           # Research outputs
    │   ├── cache/          # Research cache
    │   └── reports/        # Research reports
    ├── guide/              # Guided learning outputs
    ├── notebook/           # Notebook data
    ├── co-writer/          # Co-writer outputs
    │   ├── audio/          # TTS audio files
    │   └── tool_calls/     # Tool call history
    ├── logs/               # User logs
    ├── run_code_workspace/ # Code execution workspace
    └── user_history.json   # User history file

    Args:
        project_root: Project root directory (if None, will try to detect)
    """
    if project_root is None:
        # Path(__file__) = src/services/setup/init.py
        # .parent = src/services/setup/
        # .parent.parent = src/services/
        # .parent.parent.parent = src/
        # .parent.parent.parent.parent = DeepTutor/ (project root)
        project_root = Path(__file__).parent.parent.parent.parent

    # Get user data directory from config
    try:
        config = load_config_with_main("solve_config.yaml", project_root)
        user_data_dir = config.get("paths", {}).get("user_data_dir", "./data/user")

        # Convert relative path to absolute
        if not Path(user_data_dir).is_absolute():
            user_data_dir = project_root / user_data_dir
        else:
            user_data_dir = Path(user_data_dir)
    except Exception:
        # Fallback to default
        user_data_dir = project_root / "data" / "user"

    # Required subdirectories (based on actual usage in the codebase)
    required_dirs = [
        "solve",  # Problem solving outputs
        "question",  # Question generation outputs
        "research",  # Research outputs (will have cache/ and reports/ subdirs)
        "guide",  # Guided learning outputs
        "notebook",  # Notebook data
        "co-writer",  # Co-writer outputs
        "logs",  # User logs
        "run_code_workspace",  # Code execution workspace
    ]

    # Additional subdirectories for specific modules
    co_writer_subdirs = [
        "audio",  # TTS audio files
        "tool_calls",  # Tool call history
    ]

    research_subdirs = [
        "cache",  # Research cache
        "reports",  # Research reports
    ]

    # Check if user directory exists and is empty
    user_dir_exists = user_data_dir.exists()
    user_dir_empty = False
    if user_dir_exists:
        try:
            # Check if directory is empty (no files or subdirectories)
            user_dir_empty = not any(user_data_dir.iterdir())
        except (OSError, PermissionError) as e:
            # If we can't check directory contents, assume it's not empty
            logger = _get_setup_logger()
            logger.warning(f"Cannot check if user directory is empty: {e}")
            user_dir_empty = False

    if not user_dir_exists or user_dir_empty:
        logger = _get_setup_logger()
        logger.info("\n" + "=" * 80)
        logger.info("INITIALIZING USER DATA DIRECTORY")
        logger.info("=" * 80)

        if not user_dir_exists:
            logger.info(f"Creating user data directory: {user_data_dir}")
        else:
            logger.info(f"User data directory is empty, initializing: {user_data_dir}")

        # Create main user directory
        user_data_dir.mkdir(parents=True, exist_ok=True)

        # Create all required subdirectories
        for dir_name in required_dirs:
            dir_path = user_data_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.success(f"Created: {dir_name}/")

        # Create co-writer subdirectories
        co_writer_dir = user_data_dir / "co-writer"
        for subdir_name in co_writer_subdirs:
            subdir_path = co_writer_dir / subdir_name
            subdir_path.mkdir(parents=True, exist_ok=True)
            logger.success(f"Created: co-writer/{subdir_name}/")

        # Create research subdirectories
        research_dir = user_data_dir / "research"
        for subdir_name in research_subdirs:
            subdir_path = research_dir / subdir_name
            subdir_path.mkdir(parents=True, exist_ok=True)
            logger.success(f"Created: research/{subdir_name}/")

        # Create user_history.json if it doesn't exist
        user_history_file = user_data_dir / "user_history.json"
        if not user_history_file.exists():
            initial_history = {"version": "1.0", "created_at": None, "sessions": []}
            try:
                with open(user_history_file, "w", encoding="utf-8") as f:
                    json.dump(initial_history, f, indent=2, ensure_ascii=False)
                logger.success("Created: user_history.json")
            except Exception as e:
                logger.warning(f"Failed to create user_history.json: {e}")

        # Create interface.json in settings folder if it doesn't exist
        settings_dir = user_data_dir / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        interface_file = settings_dir / "interface.json"
        if not interface_file.exists():
            initial_settings = {"theme": "light", "language": "en", "output_language": "en"}
            try:
                with open(interface_file, "w", encoding="utf-8") as f:
                    json.dump(initial_settings, f, indent=2, ensure_ascii=False)
                logger.success("Created: settings/interface.json")
            except Exception as e:
                logger.warning(f"Failed to create settings/interface.json: {e}")

        logger.info("=" * 80)
        logger.success("User data directory initialization complete!")
        logger.info("=" * 80 + "\n")
    else:
        # Directory exists and is not empty, just ensure all subdirectories exist
        for dir_name in required_dirs:
            dir_path = user_data_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

        # Ensure co-writer subdirectories exist
        co_writer_dir = user_data_dir / "co-writer"
        for subdir_name in co_writer_subdirs:
            subdir_path = co_writer_dir / subdir_name
            subdir_path.mkdir(parents=True, exist_ok=True)

        # Ensure research subdirectories exist
        research_dir = user_data_dir / "research"
        for subdir_name in research_subdirs:
            subdir_path = research_dir / subdir_name
            subdir_path.mkdir(parents=True, exist_ok=True)

        # Ensure user_history.json exists
        user_history_file = user_data_dir / "user_history.json"
        if not user_history_file.exists():
            initial_history = {"version": "1.0", "created_at": None, "sessions": []}
            try:
                with open(user_history_file, "w", encoding="utf-8") as f:
                    json.dump(initial_history, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # Silent fail if file creation fails but directory exists

        # Ensure interface.json exists in settings folder
        settings_dir = user_data_dir / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        interface_file = settings_dir / "interface.json"
        if not interface_file.exists():
            initial_settings = {"theme": "light", "language": "en", "output_language": "en"}
            try:
                with open(interface_file, "w", encoding="utf-8") as f:
                    json.dump(initial_settings, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # Silent fail if file creation fails but directory exists


# ============================================================================
# Port Configuration Management
# ============================================================================
# Ports are configured via environment variables in .env file:
#   BACKEND_PORT=8001   (default: 8001)
#   FRONTEND_PORT=3782  (default: 3782)
# ============================================================================


def get_backend_port(project_root: Path | None = None) -> int:
    """
    Get backend port from environment variable.

    Configure in .env file: BACKEND_PORT=8001

    Returns:
        Backend port number (default: 8001)
    """
    env_port = os.environ.get("BACKEND_PORT", "8001")
    try:
        return int(env_port)
    except ValueError:
        logger = _get_setup_logger()
        logger.warning(f"Invalid BACKEND_PORT: {env_port}, using default 8001")
        return 8001


def get_frontend_port(project_root: Path | None = None) -> int:
    """
    Get frontend port from environment variable.

    Configure in .env file: FRONTEND_PORT=3782

    Returns:
        Frontend port number (default: 3782)
    """
    env_port = os.environ.get("FRONTEND_PORT", "3782")
    try:
        return int(env_port)
    except ValueError:
        logger = _get_setup_logger()
        logger.warning(f"Invalid FRONTEND_PORT: {env_port}, using default 3782")
        return 3782


def get_ports(project_root: Path | None = None) -> tuple[int, int]:
    """
    Get both backend and frontend ports from configuration.

    Args:
        project_root: Project root directory (if None, will try to detect)

    Returns:
        Tuple of (backend_port, frontend_port)

    Raises:
        SystemExit: If ports are not configured
    """
    backend_port = get_backend_port(project_root)
    frontend_port = get_frontend_port(project_root)
    return (backend_port, frontend_port)


__all__ = [
    # User directory initialization
    "init_user_directories",
    # Port configuration (from .env)
    "get_backend_port",
    "get_frontend_port",
    "get_ports",
]
