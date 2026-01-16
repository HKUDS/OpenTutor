"""
Solver Session Store - Persistent storage for Smart Solver conversations.

This service manages the storage and retrieval of solver sessions,
enabling conversation persistence across page refreshes.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional

from src.logging import get_logger
from src.models.solver_session import SolverSession

logger = get_logger("SolverSessionStore")


class SolverSessionStore:
    """
    Persistent storage for solver sessions using JSON files.

    Each session is stored as a separate JSON file in the storage directory.
    This allows for easy management and atomic operations.
    """

    def __init__(self, storage_dir: Path | str | None = None):
        """
        Initialize the session store.

        Args:
            storage_dir: Directory for storing session files.
                        Defaults to data/solver_sessions/
        """
        if storage_dir is None:
            storage_dir = Path("data/solver_sessions")
        elif isinstance(storage_dir, str):
            storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._active_session_file = self.storage_dir / ".active_session"

        logger.info(f"SolverSessionStore initialized at {self.storage_dir}")

    def _session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_dir / f"{session_id}.json"

    def save_session(self, session: SolverSession) -> None:
        """
        Save a session to disk.

        Args:
            session: The session to save
        """
        try:
            session.updated_at = datetime.now().isoformat()
            session_path = self._session_path(session.id)

            # Write atomically using temp file
            temp_path = session_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(session.to_json())

            # Rename atomically
            os.replace(temp_path, session_path)

            # Update active session marker if needed
            if session.is_active:
                self._set_active_session_id(session.id)

            logger.debug(f"Saved session {session.id}")
        except Exception as e:
            logger.error(f"Failed to save session {session.id}: {e}")
            raise

    def load_session(self, session_id: str) -> Optional[SolverSession]:
        """
        Load a session by ID.

        Args:
            session_id: The session ID to load

        Returns:
            The session if found, None otherwise
        """
        try:
            session_path = self._session_path(session_id)
            if not session_path.exists():
                return None

            with open(session_path, encoding="utf-8") as f:
                data = json.load(f)

            return SolverSession.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(self, limit: int = 50, include_inactive: bool = True) -> list[SolverSession]:
        """
        List all sessions, sorted by updated_at descending.

        Args:
            limit: Maximum number of sessions to return
            include_inactive: Whether to include inactive sessions

        Returns:
            List of sessions
        """
        sessions = []

        try:
            for session_file in self.storage_dir.glob("*.json"):
                if session_file.name.startswith("."):
                    continue

                try:
                    with open(session_file, encoding="utf-8") as f:
                        data = json.load(f)
                    session = SolverSession.from_dict(data)

                    if include_inactive or session.is_active:
                        sessions.append(session)
                except Exception as e:
                    logger.warning(f"Failed to load session file {session_file}: {e}")

            # Sort by updated_at descending
            sessions.sort(key=lambda s: s.updated_at, reverse=True)

            return sessions[:limit]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def get_active_session(self) -> Optional[SolverSession]:
        """
        Get the currently active session.

        Returns:
            The active session if exists, None otherwise
        """
        active_id = self._get_active_session_id()
        if not active_id:
            return None

        session = self.load_session(active_id)
        if session and session.is_active:
            return session

        return None

    def set_active_session(self, session_id: str) -> bool:
        """
        Set a session as the active session.

        Args:
            session_id: The session ID to set as active

        Returns:
            True if successful, False otherwise
        """
        session = self.load_session(session_id)
        if not session:
            return False

        # Deactivate current active session
        current_active = self.get_active_session()
        if current_active and current_active.id != session_id:
            current_active.is_active = False
            self.save_session(current_active)

        # Activate new session
        session.is_active = True
        self.save_session(session)
        self._set_active_session_id(session_id)

        return True

    def create_session(self, knowledge_base: str = "") -> SolverSession:
        """
        Create a new session and set it as active.

        Args:
            knowledge_base: The knowledge base to use

        Returns:
            The new session
        """
        # Deactivate current active session
        current_active = self.get_active_session()
        if current_active:
            current_active.is_active = False
            self.save_session(current_active)

        # Create new session
        session = SolverSession(knowledge_base=knowledge_base, is_active=True)
        self.save_session(session)

        logger.info(f"Created new session {session.id}")
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            session_path = self._session_path(session_id)
            if not session_path.exists():
                return False

            session_path.unlink()

            # Clear active session if it was the deleted one
            if self._get_active_session_id() == session_id:
                self._clear_active_session_id()

            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def add_message(
        self, session_id: str, role: str, content: str, output_dir: Optional[str] = None
    ) -> Optional[SolverSession]:
        """
        Add a message to a session.

        Args:
            session_id: The session ID
            role: Message role ("user" or "assistant")
            content: Message content
            output_dir: Optional output directory for artifacts

        Returns:
            Updated session if successful, None otherwise
        """
        session = self.load_session(session_id)
        if not session:
            return None

        session.add_message(role, content, output_dir)
        self.save_session(session)

        return session

    def update_token_stats(self, session_id: str, stats: dict) -> Optional[SolverSession]:
        """
        Update token statistics for a session.

        Args:
            session_id: The session ID
            stats: Token statistics dictionary

        Returns:
            Updated session if successful, None otherwise
        """
        session = self.load_session(session_id)
        if not session:
            return None

        session.update_token_stats(stats)
        self.save_session(session)

        return session

    def _get_active_session_id(self) -> Optional[str]:
        """Get the active session ID from marker file."""
        try:
            if self._active_session_file.exists():
                return self._active_session_file.read_text().strip()
        except Exception:
            pass
        return None

    def _set_active_session_id(self, session_id: str) -> None:
        """Set the active session ID in marker file."""
        try:
            self._active_session_file.write_text(session_id)
        except Exception as e:
            logger.warning(f"Failed to set active session marker: {e}")

    def _clear_active_session_id(self) -> None:
        """Clear the active session marker."""
        try:
            if self._active_session_file.exists():
                self._active_session_file.unlink()
        except Exception:
            pass


# Singleton instance
_session_store: Optional[SolverSessionStore] = None


def get_session_store() -> SolverSessionStore:
    """Get the singleton session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SolverSessionStore()
    return _session_store
