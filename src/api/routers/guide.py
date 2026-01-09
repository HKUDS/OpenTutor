"""
Guided Learning API Router
==========================

Provides session creation, learning progress management, and chat interaction.
"""

from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent
from src.agents.guide.guide_manager import GuideManager
from src.api.utils.notebook_manager import notebook_manager
from src.api.utils.task_id_manager import TaskIDManager
from src.logging import get_logger
from src.services.config import load_config_with_main
from src.services.llm import get_llm_config

router = APIRouter()

# Initialize logger with config
project_root = Path(__file__).parent.parent.parent.parent
config = load_config_with_main("guide_config.yaml", project_root)
log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get("log_dir")
logger = get_logger("Guide", level="INFO", log_dir=log_dir)


# === Request/Response Models ===


class CreateSessionRequest(BaseModel):
    """Create session request"""

    notebook_id: str | None = None  # Optional, single notebook mode
    records: list[dict] | None = None  # Optional, cross-notebook mode with direct records


class ChatRequest(BaseModel):
    """Chat request"""

    session_id: str
    message: str


class FixHtmlRequest(BaseModel):
    """Fix HTML request"""

    session_id: str
    bug_description: str


class NextKnowledgeRequest(BaseModel):
    """Next knowledge point request"""

    session_id: str


# === Helper Functions ===


def get_guide_manager():
    """Get GuideManager instance"""
    try:
        llm_config = get_llm_config()
        api_key = llm_config.api_key
        base_url = llm_config.base_url
        api_version = getattr(llm_config, "api_version", None)
        binding = llm_config.binding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM config error: {e!s}")

    return GuideManager(
        api_key=api_key,
        base_url=base_url,
        api_version=api_version,
        language=None,
        binding=binding,
    )  # Read from config file


# === REST API Endpoints ===


@router.post("/create_session")
async def create_session(request: CreateSessionRequest):
    """
    Create a new guided learning session.

    Returns:
        Session creation result with knowledge point list.
    """
    task_manager = TaskIDManager.get_instance()

    try:
        records = []
        notebook_name = "Unknown"

        # Mode 1: Cross-notebook mode - use provided records directly
        if request.records and isinstance(request.records, list):
            records = request.records
            notebook_name = f"Cross-notebook ({len(records)} records)"
        # Mode 2: Single notebook mode - get records from notebook
        elif request.notebook_id:
            notebook = notebook_manager.get_notebook(request.notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

            records = notebook.get("records", [])
            notebook_name = notebook.get("name", "Unknown")
        else:
            raise HTTPException(status_code=400, detail="Must provide notebook_id or records")

        if not records:
            raise HTTPException(status_code=400, detail="No available records")

        # Reset LLM stats for new session
        BaseAgent.reset_stats("guide")

        manager = get_guide_manager()
        result = await manager.create_session(
            notebook_id=request.notebook_id or "cross_notebook",
            notebook_name=notebook_name,
            records=records,
        )

        if result and "session_id" in result:
            session_id = result["session_id"]
            task_id = task_manager.generate_task_id("guide", session_id)
            logger.info(f"[{task_id}] Session created: {session_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_learning(request: NextKnowledgeRequest):
    """
    Start learning (get the first knowledge point).
    """
    try:
        manager = get_guide_manager()
        result = await manager.start_learning(request.session_id)
        return result
    except Exception as e:
        logger.error(f"Start learning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next")
async def next_knowledge(request: NextKnowledgeRequest):
    """
    Move to the next knowledge point.
    """
    try:
        manager = get_guide_manager()
        result = await manager.next_knowledge(request.session_id)

        # Print stats if learning completed
        if result.get("learning_complete", False):
            BaseAgent.print_stats("guide")

        return result
    except Exception as e:
        logger.error(f"Next knowledge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Send a chat message.
    """
    try:
        manager = get_guide_manager()
        result = await manager.chat(request.session_id, request.message)
        return result
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix_html")
async def fix_html(request: FixHtmlRequest):
    """
    Fix HTML page bugs.
    """
    try:
        manager = get_guide_manager()
        result = await manager.fix_html(request.session_id, request.bug_description)
        return result
    except Exception as e:
        logger.error(f"Fix HTML failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get session information.
    """
    try:
        manager = get_guide_manager()
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/html")
async def get_current_html(session_id: str):
    """
    Get the current HTML page.
    """
    try:
        manager = get_guide_manager()
        html = manager.get_current_html(session_id)
        if html is None:
            raise HTTPException(status_code=404, detail="Session not found or no HTML content")
        return {"html": html}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get HTML failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === WebSocket Endpoint ===


@router.websocket("/ws/{session_id}")
async def websocket_guide(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time interaction.

    Message types:
    - start: Start learning
    - next: Next knowledge point
    - chat: Send chat message
    - fix_html: Fix HTML
    - get_session: Get session state
    """
    await websocket.accept()

    task_manager = TaskIDManager.get_instance()
    task_id = task_manager.generate_task_id("guide", session_id)

    try:
        await websocket.send_json({"type": "task_id", "task_id": task_id})
    except (RuntimeError, WebSocketDisconnect, ConnectionError) as e:
        logger.debug(f"Failed to send task_id: {e}")

    try:
        manager = get_guide_manager()

        session = manager.get_session(session_id)
        if not session:
            await websocket.send_json({"type": "error", "content": "Session not found"})
            await websocket.close()
            return

        logger.info(f"[{task_id}] Guide session started: {session_id}")

        await websocket.send_json({"type": "session_info", "data": session})

        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "start":
                    logger.debug(f"[{task_id}] Start learning")
                    result = await manager.start_learning(session_id)
                    await websocket.send_json({"type": "start_result", "data": result})

                elif msg_type == "next":
                    logger.debug(f"[{task_id}] Next knowledge point")
                    result = await manager.next_knowledge(session_id)
                    await websocket.send_json({"type": "next_result", "data": result})

                elif msg_type == "chat":
                    message = data.get("message", "")
                    if message:
                        logger.debug(f"[{task_id}] User message: {message[:50]}...")
                        result = await manager.chat(session_id, message)
                        await websocket.send_json({"type": "chat_result", "data": result})

                elif msg_type == "fix_html":
                    bug_desc = data.get("bug_description", "")
                    logger.debug(f"[{task_id}] Fix HTML: {bug_desc[:50]}...")
                    result = await manager.fix_html(session_id, bug_desc)
                    await websocket.send_json({"type": "fix_result", "data": result})

                elif msg_type == "get_session":
                    session = manager.get_session(session_id)
                    await websocket.send_json({"type": "session_info", "data": session})

                else:
                    await websocket.send_json(
                        {"type": "error", "content": f"Unknown message type: {msg_type}"}
                    )

            except WebSocketDisconnect:
                logger.debug(f"WebSocket disconnected: {session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({"type": "error", "content": str(e)})

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close()
        except (RuntimeError, WebSocketDisconnect, ConnectionError):
            pass  # Connection already closed


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "guide"}
