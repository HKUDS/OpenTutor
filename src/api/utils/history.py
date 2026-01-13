from enum import Enum
import json
from pathlib import Path
import time


class ActivityType(str, Enum):
    SOLVE = "solve"
    QUESTION = "question"
    RESEARCH = "research"
    CHAT = "chat"


class HistoryManager:
    def __init__(self, base_dir: str | None = None):
        """
        History record manager

        Args:
            base_dir: History record directory. Default fixed to "project root/user",
                      at the same level as user/question, user/solve, user/research,
                      does not depend on current working directory, avoids path misalignment
                      when uvicorn / IDE start differently.
        """
        if base_dir is None:
            # Current file: DeepTutor/src/api/utils/history.py
            # Project root should be three levels up: DeepTutor/
            project_root = Path(__file__).resolve().parents[3]
            base_dir_path = project_root / "data" / "user"
        else:
            base_dir_path = Path(base_dir)

        self.base_dir = base_dir_path
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.base_dir / "user_history.json"
        self._ensure_file()

    def _ensure_file(self):
        """
        Ensure history file exists with correct format.
        If file exists but has wrong format, it will be fixed on next save.
        """
        if not self.history_file.exists():
            # Create file with correct dict format (matching user_dir_init.py)
            initial_history = {"version": "1.0", "created_at": None, "sessions": []}
            try:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump(initial_history, f, indent=2, ensure_ascii=False)
            except Exception:
                # If we can't create the file, that's okay - it will be handled in _load_history
                pass
        else:
            # File exists, verify it's in correct format
            # If not, it will be fixed on next save operation
            try:
                with open(self.history_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # If file is in old list format, we'll convert it on next save
                    if isinstance(data, list):
                        # File is in old format, but that's okay - _load_history handles it
                        pass
            except Exception:
                # File exists but is corrupted, will be recreated on next save
                pass

    def _load_history(self) -> list[dict]:
        """
        Load history from file. Handles multiple formats for backward compatibility.
        Returns a list of history entries.
        """
        try:
            if not self.history_file.exists():
                return []

            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)

                # Handle both list format and dict format (with 'sessions' key)
                if isinstance(data, dict):
                    # If it's a dict, try to get 'sessions' field
                    sessions = data.get("sessions", [])
                    # Ensure sessions is a list
                    if isinstance(sessions, list):
                        return sessions
                    # If sessions is not a list, return empty list and log warning
                    return []
                if isinstance(data, list):
                    # Legacy format: direct list
                    return data
                # Unknown format, return empty list
                return []
        except json.JSONDecodeError:
            # File exists but is corrupted, return empty list
            # Could log this error in production
            return []
        except Exception:
            # Any other error, return empty list
            return []

    def _save_history(self, history: list[dict]):
        # Load existing file to preserve metadata if it's in dict format
        try:
            with open(self.history_file, encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    # Preserve dict structure, update sessions
                    existing_data["sessions"] = history
                    data_to_save = existing_data
                else:
                    # If it was a list, convert to dict format
                    data_to_save = {
                        "version": "1.0",
                        "created_at": existing_data[0].get("timestamp") if existing_data else None,
                        "sessions": history,
                    }
        except Exception:
            # If file doesn't exist or can't be read, create new dict format
            data_to_save = {
                "version": "1.0",
                "created_at": history[0].get("timestamp") if history else None,
                "sessions": history,
            }

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

    def add_entry(self, activity_type: ActivityType, title: str, content: dict, summary: str = ""):
        """
        Add a new history entry.

        Args:
            activity_type: The type of activity (solve, question, research)
            title: A short title (e.g. the question asked, or topic)
            content: The full result/payload
            summary: A short summary if applicable
        """
        entry = {
            "id": str(int(time.time() * 1000)),
            "timestamp": time.time(),
            "type": activity_type,
            "title": title,
            "summary": summary,
            "content": content,
        }

        history = self._load_history()
        history.insert(0, entry)  # Prepend to show latest first

        # Optional: Limit history size
        if len(history) > 100:
            history = history[:100]

        self._save_history(history)
        return entry

    def get_recent(self, limit: int = 10, type_filter: str | None = None) -> list[dict]:
        history = self._load_history()
        if type_filter:
            history = [h for h in history if h["type"] == type_filter]
        return history[:limit]

    def get_entry(self, entry_id: str) -> dict | None:
        history = self._load_history()
        for entry in history:
            if entry["id"] == entry_id:
                return entry
        return None


# Global instance
history_manager = HistoryManager()
