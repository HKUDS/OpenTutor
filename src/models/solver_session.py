"""
Solver Session Models - Data models for persisting Smart Solver conversations.

This module provides dataclasses for storing and managing solver conversation
sessions, enabling persistence across page refreshes and browser sessions.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from typing import Optional
import uuid


@dataclass
class SolverMessage:
    """A single message in a solver conversation."""

    role: str  # "user" | "assistant"
    content: str
    output_dir: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SolverMessage":
        """Create from dictionary."""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            output_dir=data.get("output_dir"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class TokenStats:
    """Token usage statistics for a session."""

    model: str = ""
    calls: int = 0
    tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenStats":
        return cls(
            model=data.get("model", ""),
            calls=data.get("calls", 0),
            tokens=data.get("tokens", 0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cost=data.get("cost", 0.0),
        )


@dataclass
class SolverSession:
    """A complete solver conversation session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""  # Auto-generated from first user message
    knowledge_base: str = ""
    messages: list[SolverMessage] = field(default_factory=list)
    token_stats: TokenStats = field(default_factory=TokenStats)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True  # Current session flag

    def add_message(
        self, role: str, content: str, output_dir: Optional[str] = None
    ) -> SolverMessage:
        """Add a new message to the session."""
        message = SolverMessage(role=role, content=content, output_dir=output_dir)
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

        # Auto-generate title from first user message
        if not self.title and role == "user" and content:
            self.title = content[:100] + ("..." if len(content) > 100 else "")

        return message

    def update_token_stats(self, stats: dict) -> None:
        """Update token statistics."""
        self.token_stats = TokenStats.from_dict(stats)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "knowledge_base": self.knowledge_base,
            "messages": [m.to_dict() for m in self.messages],
            "token_stats": self.token_stats.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "SolverSession":
        """Create from dictionary."""
        messages = [SolverMessage.from_dict(m) for m in data.get("messages", [])]
        token_stats = TokenStats.from_dict(data.get("token_stats", {}))

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            knowledge_base=data.get("knowledge_base", ""),
            messages=messages,
            token_stats=token_stats,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            is_active=data.get("is_active", True),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SolverSession":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
