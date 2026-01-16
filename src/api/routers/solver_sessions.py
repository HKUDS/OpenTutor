"""
Solver Sessions API Router - REST endpoints for managing solver conversation sessions.

This module provides endpoints for creating, reading, updating, and deleting
solver sessions, enabling conversation persistence across page refreshes.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.logging import get_logger
from src.models.solver_session import SolverSession
from src.services.solver.session_store import get_session_store

logger = get_logger("SolverSessionsAPI")

router = APIRouter(prefix="/api/v1/solver/sessions", tags=["Solver Sessions"])


# --- Request/Response Models ---


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    knowledge_base: str = ""


class AddMessageRequest(BaseModel):
    """Request to add a message to a session."""

    role: str  # "user" | "assistant"
    content: str
    output_dir: Optional[str] = None


class UpdateTokenStatsRequest(BaseModel):
    """Request to update token statistics."""

    model: str = ""
    calls: int = 0
    tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class UpdateSessionRequest(BaseModel):
    """Request to update session fields."""

    title: Optional[str] = None
    knowledge_base: Optional[str] = None
    is_active: Optional[bool] = None


class SessionResponse(BaseModel):
    """Response containing a session."""

    id: str
    title: str
    knowledge_base: str
    messages: list[dict]
    token_stats: dict
    created_at: str
    updated_at: str
    is_active: bool
    message_count: int


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""

    sessions: list[SessionResponse]
    total: int


# --- Helper Functions ---


def session_to_response(session: SolverSession) -> SessionResponse:
    """Convert a SolverSession to SessionResponse."""
    return SessionResponse(
        id=session.id,
        title=session.title,
        knowledge_base=session.knowledge_base,
        messages=[m.to_dict() for m in session.messages],
        token_stats=session.token_stats.to_dict(),
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active,
        message_count=len(session.messages),
    )


# --- Endpoints ---


@router.get("", response_model=SessionListResponse)
async def list_sessions(limit: int = 50, include_inactive: bool = True):
    """
    List all sessions, sorted by updated_at descending.

    Args:
        limit: Maximum number of sessions to return (default: 50)
        include_inactive: Whether to include inactive sessions (default: true)
    """
    try:
        store = get_session_store()
        sessions = store.list_sessions(limit=limit, include_inactive=include_inactive)

        return SessionListResponse(
            sessions=[session_to_response(s) for s in sessions],
            total=len(sessions),
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=Optional[SessionResponse])
async def get_active_session():
    """
    Get the currently active session.

    Returns null if no active session exists.
    """
    try:
        store = get_session_store()
        session = store.get_active_session()

        if not session:
            return None

        return session_to_response(session)
    except Exception as e:
        logger.error(f"Failed to get active session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get a specific session by ID.

    Args:
        session_id: The session ID
    """
    try:
        store = get_session_store()
        session = store.load_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new session and set it as active.

    Args:
        request: Session creation parameters
    """
    try:
        store = get_session_store()
        session = store.create_session(knowledge_base=request.knowledge_base)

        logger.info(f"Created session {session.id}")
        return session_to_response(session)
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    Update session fields.

    Args:
        session_id: The session ID
        request: Fields to update
    """
    try:
        store = get_session_store()
        session = store.load_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Update fields
        if request.title is not None:
            session.title = request.title
        if request.knowledge_base is not None:
            session.knowledge_base = request.knowledge_base
        if request.is_active is not None:
            session.is_active = request.is_active
            if request.is_active:
                store.set_active_session(session_id)

        store.save_session(session)

        return session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session.

    Args:
        session_id: The session ID
    """
    try:
        store = get_session_store()
        deleted = store.delete_session(session_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return {"message": f"Session {session_id} deleted", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/messages", response_model=SessionResponse)
async def add_message(session_id: str, request: AddMessageRequest):
    """
    Add a message to a session.

    Args:
        session_id: The session ID
        request: Message to add
    """
    try:
        store = get_session_store()
        session = store.add_message(
            session_id=session_id,
            role=request.role,
            content=request.content,
            output_dir=request.output_dir,
        )

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}/token-stats", response_model=SessionResponse)
async def update_token_stats(session_id: str, request: UpdateTokenStatsRequest):
    """
    Update token statistics for a session.

    Args:
        session_id: The session ID
        request: Token statistics
    """
    try:
        store = get_session_store()
        session = store.update_token_stats(
            session_id=session_id,
            stats=request.model_dump(),
        )

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update token stats for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/activate", response_model=SessionResponse)
async def activate_session(session_id: str):
    """
    Set a session as the active session.

    Args:
        session_id: The session ID
    """
    try:
        store = get_session_store()
        success = store.set_active_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        session = store.load_session(session_id)
        return session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
