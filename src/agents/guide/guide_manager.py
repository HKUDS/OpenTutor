#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GuideManager - Guided Learning Session Manager
Manages the complete lifecycle of learning sessions
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any
import uuid

import yaml

from src.logging import get_logger
from src.services.config import load_config_with_main, parse_language

from .agents import ChatAgent, InteractiveAgent, LocateAgent, SummaryAgent


@dataclass
class GuidedSession:
    """Guided learning session"""

    session_id: str
    notebook_id: str
    notebook_name: str
    created_at: float
    knowledge_points: list[dict[str, Any]] = field(default_factory=list)
    current_index: int = 0
    chat_history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "initialized"  # initialized, learning, completed
    current_html: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuidedSession":
        return cls(**data)


class GuideManager:
    """Guided learning manager"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        api_version: str | None = None,
        language: str | None = None,
        output_dir: str | None = None,
        config_path: str | None = None,
        binding: str = "openai",
    ):
        """
        Initialize manager

        Args:
            api_key: API key
            base_url: API endpoint
            api_version: API version (for Azure OpenAI)
            language: Language setting (if None, read from config file)
            output_dir: Output directory
            config_path: Configuration file path (if None, use default path)
            binding: LLM provider binding
        """
        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
        self.binding = binding

        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config = load_config_with_main("guide_config.yaml", project_root)
        else:
            config_path = Path(config_path)
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                except Exception:
                    config = {}
            else:
                config = {}

        # Initialize logger (from config)
        log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get(
            "log_dir"
        )
        self.logger = get_logger("Guide", log_dir=log_dir)

        if language is None:
            # Get language config (unified in config/main.yaml system.language)
            lang_config = config.get("system", {}).get("language", "zh")
            self.language = parse_language(lang_config)
            self.logger.info(f"Language setting loaded from config: {self.language}")
        else:
            # If explicitly specified, also parse it to ensure consistency
            self.language = parse_language(language)
            self.logger.info(f"Using explicitly specified language setting: {self.language}")

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Get output_dir from config (already loaded above)
            output_dir_from_config = config.get("system", {}).get("output_dir")
            if output_dir_from_config:
                self.output_dir = Path(output_dir_from_config)
            else:
                # Fallback to default path
                project_root = Path(__file__).parent.parent.parent.parent
                self.output_dir = project_root / "data" / "user" / "guide"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.locate_agent = LocateAgent(
            api_key,
            base_url,
            language=self.language,
            api_version=self.api_version,
            binding=self.binding,
        )
        self.interactive_agent = InteractiveAgent(
            api_key,
            base_url,
            language=self.language,
            api_version=self.api_version,
            binding=self.binding,
        )
        self.chat_agent = ChatAgent(
            api_key,
            base_url,
            language=self.language,
            api_version=self.api_version,
            binding=self.binding,
        )
        self.summary_agent = SummaryAgent(
            api_key,
            base_url,
            language=self.language,
            api_version=self.api_version,
            binding=self.binding,
        )

        self._sessions: dict[str, GuidedSession] = {}

    def _get_session_file(self, session_id: str) -> Path:
        """Get session file path"""
        return self.output_dir / f"session_{session_id}.json"

    def _save_session(self, session: GuidedSession):
        """Save session to file"""
        filepath = self._get_session_file(session.session_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        self._sessions[session.session_id] = session

    def _load_session(self, session_id: str) -> GuidedSession | None:
        """Load session from file"""
        if session_id in self._sessions:
            return self._sessions[session_id]

        filepath = self._get_session_file(session_id)
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            session = GuidedSession.from_dict(data)
            self._sessions[session_id] = session
            return session
        return None

    async def create_session(
        self, notebook_id: str, notebook_name: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Create new learning session

        Args:
            notebook_id: Notebook ID
            notebook_name: Notebook name
            records: Notebook records

        Returns:
            Session creation result
        """
        session_id = str(uuid.uuid4())[:8]

        locate_result = await self.locate_agent.process(
            notebook_id=notebook_id, notebook_name=notebook_name, records=records
        )

        if not locate_result.get("success"):
            return {
                "success": False,
                "error": locate_result.get("error", "Failed to analyze knowledge points"),
                "session_id": None,
            }

        knowledge_points = locate_result.get("knowledge_points", [])

        if not knowledge_points:
            return {
                "success": False,
                "error": "No knowledge points identified from notebook",
                "session_id": None,
            }

        session = GuidedSession(
            session_id=session_id,
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            created_at=time.time(),
            knowledge_points=knowledge_points,
            current_index=0,
            status="initialized",
        )

        self._save_session(session)

        return {
            "success": True,
            "session_id": session_id,
            "knowledge_points": knowledge_points,
            "total_points": len(knowledge_points),
            "message": f"Learning plan created with {len(knowledge_points)} knowledge points",
        }

    def _get_learning_state(
        self, knowledge_points: list[dict[str, Any]], current_index: int
    ) -> dict[str, Any]:
        """
        Get learning state information (internal helper method)

        Args:
            knowledge_points: Knowledge point list
            current_index: Current knowledge point index

        Returns:
            Learning state information
        """
        total_points = len(knowledge_points)

        if total_points == 0:
            return {"success": False, "error": "No knowledge points to learn", "status": "empty"}

        if current_index >= total_points:
            return {
                "success": True,
                "current_index": current_index,
                "current_knowledge": None,
                "status": "completed",
                "progress_percentage": 100,
                "total_points": total_points,
                "message": "🎉 Congratulations! You have completed learning all knowledge points!",
            }

        current_knowledge = knowledge_points[current_index]
        progress = int((current_index / total_points) * 100)

        message = f"📚 Starting to learn knowledge point {current_index + 1}: {current_knowledge.get('knowledge_title', '')}"

        return {
            "success": True,
            "current_index": current_index,
            "current_knowledge": current_knowledge,
            "status": "learning",
            "progress_percentage": progress,
            "total_points": total_points,
            "remaining_points": total_points - current_index - 1,
            "message": message,
        }

    async def start_learning(self, session_id: str) -> dict[str, Any]:
        """
        Start learning the first knowledge point

        Args:
            session_id: Session ID

        Returns:
            First knowledge point information and interactive page
        """
        session = self._load_session(session_id)
        if not session:
            return {"success": False, "error": "Session does not exist"}

        state = self._get_learning_state(session.knowledge_points, 0)

        if not state.get("success"):
            return state

        current_knowledge = state.get("current_knowledge")

        interactive_result = await self.interactive_agent.process(knowledge=current_knowledge)

        session.current_index = 0
        session.status = "learning"
        session.current_html = interactive_result.get("html", "")

        session.chat_history.append(
            {
                "role": "system",
                "content": state.get("message", ""),
                "knowledge_index": 0,
                "timestamp": time.time(),
            }
        )

        self._save_session(session)

        return {
            "success": True,
            "current_index": 0,
            "current_knowledge": current_knowledge,
            "html": interactive_result.get("html", ""),
            "progress": state.get("progress_percentage", 0),
            "total_points": len(session.knowledge_points),
            "message": state.get("message", ""),
        }

    async def next_knowledge(self, session_id: str) -> dict[str, Any]:
        """
        Move to next knowledge point

        Args:
            session_id: Session ID

        Returns:
            Next knowledge point information and interactive page, or completion summary
        """
        session = self._load_session(session_id)
        if not session:
            return {"success": False, "error": "Session does not exist"}

        new_index = session.current_index + 1

        state = self._get_learning_state(session.knowledge_points, new_index)

        if not state.get("success"):
            return state

        if state.get("status") == "completed":
            summary_result = await self.summary_agent.process(
                notebook_name=session.notebook_name,
                knowledge_points=session.knowledge_points,
                chat_history=session.chat_history,
            )

            session.status = "completed"
            session.summary = summary_result.get("summary", "")
            session.current_index = new_index

            session.chat_history.append(
                {
                    "role": "system",
                    "content": state.get(
                        "message", "Congratulations on completing all knowledge points!"
                    ),
                    "timestamp": time.time(),
                }
            )

            self._save_session(session)

            return {
                "success": True,
                "status": "completed",
                "summary": session.summary,
                "progress": 100,
                "message": state.get("message", ""),
            }

        current_knowledge = state.get("current_knowledge")

        interactive_result = await self.interactive_agent.process(knowledge=current_knowledge)

        session.current_index = new_index
        session.current_html = interactive_result.get("html", "")

        message = f"→ Entering knowledge point {new_index + 1}: {current_knowledge.get('knowledge_title', '')}"

        session.chat_history.append(
            {
                "role": "system",
                "content": message,
                "knowledge_index": new_index,
                "timestamp": time.time(),
            }
        )

        self._save_session(session)

        return {
            "success": True,
            "current_index": new_index,
            "current_knowledge": current_knowledge,
            "html": interactive_result.get("html", ""),
            "progress": state.get("progress_percentage", 0),
            "total_points": len(session.knowledge_points),
            "remaining_points": state.get("remaining_points", 0),
            "message": message,
        }

    async def chat(self, session_id: str, user_message: str) -> dict[str, Any]:
        """
        Process user chat message

        Args:
            session_id: Session ID
            user_message: User message

        Returns:
            Assistant's answer
        """
        session = self._load_session(session_id)
        if not session:
            return {"success": False, "error": "Session does not exist"}

        if session.status != "learning":
            return {"success": False, "error": "Not currently in learning state"}

        current_knowledge = session.knowledge_points[session.current_index]

        current_history = [
            msg
            for msg in session.chat_history
            if msg.get("knowledge_index") == session.current_index
        ]

        user_msg = {
            "role": "user",
            "content": user_message,
            "knowledge_index": session.current_index,
            "timestamp": time.time(),
        }
        session.chat_history.append(user_msg)

        chat_result = await self.chat_agent.process(
            knowledge=current_knowledge, chat_history=current_history, user_question=user_message
        )

        assistant_msg = {
            "role": "assistant",
            "content": chat_result.get("answer", ""),
            "knowledge_index": session.current_index,
            "timestamp": time.time(),
        }
        session.chat_history.append(assistant_msg)

        self._save_session(session)

        return {
            "success": True,
            "answer": chat_result.get("answer", ""),
            "knowledge_index": session.current_index,
        }

    async def fix_html(self, session_id: str, bug_description: str) -> dict[str, Any]:
        """
        Fix HTML page bug

        Args:
            session_id: Session ID
            bug_description: Bug description

        Returns:
            Fixed HTML
        """
        session = self._load_session(session_id)
        if not session:
            return {"success": False, "error": "Session does not exist"}

        current_knowledge = session.knowledge_points[session.current_index]

        result = await self.interactive_agent.process(
            knowledge=current_knowledge, retry_with_bug=bug_description
        )

        if result.get("success"):
            session.current_html = result.get("html", "")
            self._save_session(session)

        return result

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session information"""
        session = self._load_session(session_id)
        if session:
            return session.to_dict()
        return None

    def get_current_html(self, session_id: str) -> str | None:
        """Get current HTML page"""
        session = self._load_session(session_id)
        if session:
            return session.current_html
        return None
