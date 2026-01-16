"""
Tests for Solver Session Store

Unit tests for the session storage service.
"""

import json
from pathlib import Path
import shutil
import tempfile

import pytest

from src.models.solver_session import SolverMessage, SolverSession
from src.services.solver.session_store import SolverSessionStore


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def session_store(temp_storage_dir):
    """Create a session store with temporary storage."""
    return SolverSessionStore(temp_storage_dir)


class TestSolverMessage:
    """Tests for SolverMessage dataclass."""

    def test_create_message(self):
        msg = SolverMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.output_dir is None
        assert msg.timestamp is not None

    def test_message_serialization(self):
        msg = SolverMessage(role="assistant", content="Response", output_dir="/path")
        data = msg.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "Response"
        assert data["output_dir"] == "/path"

    def test_message_deserialization(self):
        data = {"role": "user", "content": "Test", "timestamp": "2026-01-16T00:00:00"}
        msg = SolverMessage.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test"


class TestSolverSession:
    """Tests for SolverSession dataclass."""

    def test_create_session(self):
        session = SolverSession(knowledge_base="test_kb")

        assert session.id is not None
        assert session.knowledge_base == "test_kb"
        assert session.messages == []
        assert session.is_active is True

    def test_add_message(self):
        session = SolverSession()
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_auto_title_generation(self):
        session = SolverSession()
        session.add_message("user", "This is my question about calculus")

        assert session.title == "This is my question about calculus"

    def test_title_truncation(self):
        session = SolverSession()
        long_question = "A" * 150
        session.add_message("user", long_question)

        assert len(session.title) == 103  # 100 chars + "..."
        assert session.title.endswith("...")

    def test_session_serialization(self):
        session = SolverSession(knowledge_base="test")
        session.add_message("user", "Hello")

        json_str = session.to_json()
        data = json.loads(json_str)

        assert data["knowledge_base"] == "test"
        assert len(data["messages"]) == 1

    def test_session_deserialization(self):
        data = {
            "id": "test-id",
            "knowledge_base": "my_kb",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        session = SolverSession.from_dict(data)

        assert session.id == "test-id"
        assert session.knowledge_base == "my_kb"
        assert len(session.messages) == 1


class TestSolverSessionStore:
    """Tests for SolverSessionStore service."""

    def test_create_session(self, session_store):
        session = session_store.create_session(knowledge_base="test_kb")

        assert session.id is not None
        assert session.knowledge_base == "test_kb"
        assert session.is_active is True

    def test_save_and_load_session(self, session_store):
        session = session_store.create_session()
        session.add_message("user", "Hello")
        session_store.save_session(session)

        loaded = session_store.load_session(session.id)

        assert loaded is not None
        assert loaded.id == session.id
        assert len(loaded.messages) == 1

    def test_list_sessions(self, session_store):
        session1 = session_store.create_session()
        session2 = session_store.create_session()

        sessions = session_store.list_sessions()

        assert len(sessions) >= 2
        # Most recent should be first
        assert sessions[0].id == session2.id

    def test_get_active_session(self, session_store):
        session1 = session_store.create_session()
        session2 = session_store.create_session()  # This becomes active

        active = session_store.get_active_session()

        assert active is not None
        assert active.id == session2.id

    def test_set_active_session(self, session_store):
        session1 = session_store.create_session()
        session2 = session_store.create_session()

        # session2 is active, now activate session1
        session_store.set_active_session(session1.id)

        active = session_store.get_active_session()
        assert active.id == session1.id

    def test_delete_session(self, session_store):
        session = session_store.create_session()
        session_id = session.id

        deleted = session_store.delete_session(session_id)

        assert deleted is True
        assert session_store.load_session(session_id) is None

    def test_add_message_to_session(self, session_store):
        session = session_store.create_session()

        updated = session_store.add_message(session.id, "user", "Test message")

        assert updated is not None
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Test message"

    def test_update_token_stats(self, session_store):
        session = session_store.create_session()

        stats = {"model": "gpt-4", "calls": 5, "tokens": 1000, "cost": 0.05}
        updated = session_store.update_token_stats(session.id, stats)

        assert updated is not None
        assert updated.token_stats.model == "gpt-4"
        assert updated.token_stats.cost == 0.05

    def test_load_nonexistent_session(self, session_store):
        result = session_store.load_session("nonexistent-id")
        assert result is None

    def test_delete_nonexistent_session(self, session_store):
        result = session_store.delete_session("nonexistent-id")
        assert result is False
