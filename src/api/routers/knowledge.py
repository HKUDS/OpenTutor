"""
Knowledge Base API Router
=========================

Handles knowledge base CRUD operations, file uploads, and initialization.
"""

import asyncio
from datetime import datetime
from pathlib import Path
import shutil
import sys
import traceback

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from src.api.utils.progress_broadcaster import ProgressBroadcaster
from src.api.utils.task_id_manager import TaskIDManager
from src.knowledge.add_documents import DocumentAdder
from src.knowledge.initializer import KnowledgeBaseInitializer
from src.knowledge.manager import KnowledgeBaseManager
from src.knowledge.progress_tracker import ProgressStage, ProgressTracker
from src.utils.document_validator import DocumentValidator
from src.utils.error_utils import format_exception_message

_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))
from src.logging import get_logger
from src.services.config import load_config_with_main
from src.services.llm import get_llm_config

# Initialize logger with config
project_root = Path(__file__).parent.parent.parent.parent
config = load_config_with_main("solve_config.yaml", project_root)  # Use any config to get main.yaml
log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get("log_dir")
logger = get_logger("Knowledge", level="INFO", log_dir=log_dir)

router = APIRouter()

_kb_base_dir = _project_root / "data" / "knowledge_bases"

# Lazy initialization
kb_manager = None


def get_kb_manager():
    """Get KnowledgeBaseManager instance (lazy init)"""
    global kb_manager
    if kb_manager is None:
        kb_manager = KnowledgeBaseManager(base_dir=str(_kb_base_dir))
    return kb_manager


class KnowledgeBaseInfo(BaseModel):
    name: str
    is_default: bool
    statistics: dict


async def run_initialization_task(initializer: KnowledgeBaseInitializer):
    """Background task for knowledge base initialization"""
    task_manager = TaskIDManager.get_instance()
    task_id = task_manager.generate_task_id("kb_init", initializer.kb_name)

    try:
        if not initializer.progress_tracker:
            initializer.progress_tracker = ProgressTracker(
                initializer.kb_name, initializer.base_dir
            )

        initializer.progress_tracker.task_id = task_id

        logger.info(f"[{task_id}] Initializing KB: {initializer.kb_name}")

        await initializer.process_documents()
        initializer.extract_numbered_items()

        initializer.progress_tracker.update(
            ProgressStage.COMPLETED, "Knowledge base initialization complete!", current=1, total=1
        )

        logger.success(f"[{task_id}] KB '{initializer.kb_name}' initialized")
        task_manager.update_task_status(task_id, "completed")
    except Exception as e:
        error_msg = str(e)

        logger.error(f"[{task_id}] KB '{initializer.kb_name}' init failed: {error_msg}")

        task_manager.update_task_status(task_id, "error", error=error_msg)

        if initializer.progress_tracker:
            initializer.progress_tracker.update(
                ProgressStage.ERROR, f"Initialization failed: {error_msg}", error=error_msg
            )


async def run_upload_processing_task(
    kb_name: str, base_dir: str, api_key: str, base_url: str, uploaded_file_paths: list[str]
):
    """Background task for processing uploaded files"""
    task_manager = TaskIDManager.get_instance()
    task_key = f"{kb_name}_upload_{len(uploaded_file_paths)}"
    task_id = task_manager.generate_task_id("kb_upload", task_key)

    progress_tracker = ProgressTracker(kb_name, Path(base_dir))
    progress_tracker.task_id = task_id

    try:
        logger.info(f"[{task_id}] Processing {len(uploaded_file_paths)} files to KB '{kb_name}'")
        progress_tracker.update(
            ProgressStage.PROCESSING_DOCUMENTS,
            f"Processing {len(uploaded_file_paths)} files...",
            current=0,
            total=len(uploaded_file_paths),
        )

        adder = DocumentAdder(
            kb_name=kb_name,
            base_dir=base_dir,
            api_key=api_key,
            base_url=base_url,
            progress_tracker=progress_tracker,
        )

        new_files = [Path(path) for path in uploaded_file_paths]
        processed_files = await adder.process_new_documents(new_files)

        if processed_files:
            progress_tracker.update(
                ProgressStage.EXTRACTING_ITEMS,
                "Extracting numbered items...",
                current=0,
                total=len(processed_files),
            )
            adder.extract_numbered_items_for_new_docs(processed_files, batch_size=20)

        adder.update_metadata(len(new_files))

        progress_tracker.update(
            ProgressStage.COMPLETED,
            f"Successfully processed {len(processed_files)} files!",
            current=len(processed_files),
            total=len(processed_files),
        )

        logger.success(f"[{task_id}] Processed {len(processed_files)} files to KB '{kb_name}'")
        task_manager.update_task_status(task_id, "completed")
    except Exception as e:
        error_msg = f"Upload processing failed (KB '{kb_name}'): {e}"
        logger.error(f"[{task_id}] {error_msg}")

        task_manager.update_task_status(task_id, "error", error=error_msg)

        progress_tracker.update(
            ProgressStage.ERROR, f"Processing failed: {error_msg}", error=error_msg
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        manager = get_kb_manager()
        config_exists = manager.config_file.exists()
        kb_count = len(manager.list_knowledge_bases())
        return {
            "status": "ok",
            "config_file": str(manager.config_file),
            "config_exists": config_exists,
            "base_dir": str(manager.base_dir),
            "base_dir_exists": manager.base_dir.exists(),
            "knowledge_bases_count": kb_count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@router.get("/list", response_model=list[KnowledgeBaseInfo])
async def list_knowledge_bases():
    """List all available knowledge bases with their details."""
    try:
        manager = get_kb_manager()
        kb_names = manager.list_knowledge_bases()

        logger.info(f"Found {len(kb_names)} knowledge bases: {kb_names}")

        if not kb_names:
            logger.info("No knowledge bases found, returning empty list")
            return []

        result = []
        errors = []

        for name in kb_names:
            try:
                info = manager.get_info(name)
                logger.debug(f"Successfully got info for KB '{name}': {info.get('statistics', {})}")
                result.append(
                    KnowledgeBaseInfo(
                        name=info["name"],
                        is_default=info["is_default"],
                        statistics=info.get("statistics", {}),
                    )
                )
            except Exception as e:
                error_msg = f"Error getting info for KB '{name}': {e}"
                errors.append(error_msg)
                logger.warning(f"{error_msg}\n{traceback.format_exc()}")
                try:
                    kb_dir = manager.base_dir / name
                    if kb_dir.exists():
                        logger.info(f"KB '{name}' directory exists, creating fallback info")
                        result.append(
                            KnowledgeBaseInfo(
                                name=name,
                                is_default=name == manager.get_default(),
                                statistics={
                                    "raw_documents": 0,
                                    "images": 0,
                                    "content_lists": 0,
                                    "rag_initialized": False,
                                },
                            )
                        )
                except Exception as fallback_err:
                    logger.error(f"Fallback also failed for KB '{name}': {fallback_err}")

        if errors and not result:
            error_detail = f"Failed to load knowledge bases. Errors: {'; '.join(errors)}"
            logger.error(error_detail)
            raise HTTPException(status_code=500, detail=error_detail)

        if errors:
            logger.warning(
                f"Some KBs had errors, returning {len(result)} results. Errors: {errors}"
            )

        logger.info(f"Returning {len(result)} knowledge bases")
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error listing knowledge bases: {e}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge bases: {e!s}")


@router.get("/{kb_name}")
async def get_knowledge_base_details(kb_name: str):
    """Get detailed info for a specific KB."""
    try:
        manager = get_kb_manager()
        return manager.get_info(kb_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{kb_name}")
async def delete_knowledge_base(kb_name: str):
    """Delete a knowledge base."""
    try:
        manager = get_kb_manager()
        success = manager.delete_knowledge_base(kb_name, confirm=True)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete knowledge base")
        logger.info(f"KB '{kb_name}' deleted")
        return {"message": f"Knowledge base '{kb_name}' deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kb_name}/upload")
async def upload_files(
    kb_name: str, background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)
):
    """Upload files to a knowledge base and process them in background."""
    try:
        # 1. Validate immediately upon receipt using DocumentValidator
        validator = DocumentValidator()
        for file in files:
            try:
                await validator.validate(file)
            except Exception as e:
                error_message = (
                    f"Validation failed for file '{file.filename}': {format_exception_message(e)}"
                )
                # Log the full exception with traceback for server-side diagnostics
                logger.error(error_message, exc_info=True)
                # Return a client error with file-specific validation details
                raise HTTPException(status_code=400, detail=error_message)

        manager = get_kb_manager()
        kb_path = manager.get_knowledge_base_path(kb_name)
        raw_dir = kb_path / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        try:
            llm_config = get_llm_config()
            api_key = llm_config.api_key
            base_url = llm_config.base_url
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"LLM config error: {e!s}")

        uploaded_files = []
        uploaded_file_paths = []
        for file in files:
            file_path = raw_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)
            uploaded_file_paths.append(str(file_path))

        logger.info(f"Uploading {len(uploaded_files)} files to KB '{kb_name}'")

        background_tasks.add_task(
            run_upload_processing_task,
            kb_name=kb_name,
            base_dir=str(_kb_base_dir),
            api_key=api_key,
            base_url=base_url,
            uploaded_file_paths=uploaded_file_paths,
        )

        return {
            "message": f"Uploaded {len(uploaded_files)} files. Processing in background.",
            "files": uploaded_files,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found")
    except Exception as e:
        # Unexpected failure (Server error)
        formatted_error = format_exception_message(e)
        raise HTTPException(status_code=500, detail=formatted_error)


@router.post("/create")
async def create_knowledge_base(
    background_tasks: BackgroundTasks, name: str = Form(...), files: list[UploadFile] = File(...)
):
    """Create a new knowledge base and initialize it with files."""
    try:
        manager = get_kb_manager()
        if name in manager.list_knowledge_bases():
            raise HTTPException(status_code=400, detail=f"Knowledge base '{name}' already exists")

        try:
            llm_config = get_llm_config()
            api_key = llm_config.api_key
            base_url = llm_config.base_url
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"LLM config error: {e!s}")

        progress_tracker = ProgressTracker(name, _kb_base_dir)

        logger.info(f"Creating KB: {name}")

        progress_tracker.update(
            ProgressStage.INITIALIZING, "Initializing knowledge base...", current=0, total=0
        )

        initializer = KnowledgeBaseInitializer(
            kb_name=name,
            base_dir=str(_kb_base_dir),
            api_key=api_key,
            base_url=base_url,
            progress_tracker=progress_tracker,
        )

        initializer.create_directory_structure()

        manager = get_kb_manager()
        if name not in manager.list_knowledge_bases():
            logger.warning(f"KB {name} not found in config, registering manually")
            initializer._register_to_config()

        uploaded_files = []
        for file in files:
            file_path = initializer.raw_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(file.filename)

        progress_tracker.update(
            ProgressStage.PROCESSING_DOCUMENTS,
            f"Saved {len(uploaded_files)} files, preparing to process...",
            current=0,
            total=len(uploaded_files),
        )

        background_tasks.add_task(run_initialization_task, initializer)

        logger.success(f"KB '{name}' created, processing {len(uploaded_files)} files in background")

        return {
            "message": f"Knowledge base '{name}' created. Processing {len(uploaded_files)} files in background.",
            "name": name,
            "files": uploaded_files,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create KB: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kb_name}/progress")
async def get_progress(kb_name: str):
    """Get initialization progress for a knowledge base"""
    try:
        progress_tracker = ProgressTracker(kb_name, _kb_base_dir)
        progress = progress_tracker.get_progress()

        if progress is None:
            return {"status": "not_started", "message": "Initialization not started"}

        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{kb_name}/progress/clear")
async def clear_progress(kb_name: str):
    """Clear progress file for a knowledge base (useful for stuck states)"""
    try:
        progress_tracker = ProgressTracker(kb_name, _kb_base_dir)
        progress_tracker.clear()
        return {"status": "success", "message": f"Progress cleared for {kb_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/{kb_name}/progress/ws")
async def websocket_progress(websocket: WebSocket, kb_name: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()

    broadcaster = ProgressBroadcaster.get_instance()

    try:
        await broadcaster.connect(kb_name, websocket)

        progress_tracker = ProgressTracker(kb_name, _kb_base_dir)
        initial_progress = progress_tracker.get_progress()

        # Check if KB is already ready (has rag_storage)
        kb_dir = _kb_base_dir / kb_name
        rag_storage_dir = kb_dir / "rag_storage"
        kb_is_ready = rag_storage_dir.exists() and rag_storage_dir.is_dir()

        # Only send non-completed progress if KB is not ready
        # or if progress is recent (within 5 minutes)
        if initial_progress:
            stage = initial_progress.get("stage")
            timestamp = initial_progress.get("timestamp")

            should_send = False
            if stage in ["completed", "error"] or not kb_is_ready:
                should_send = True
            elif timestamp:
                # Check if progress is recent
                try:
                    progress_time = datetime.fromisoformat(timestamp)
                    now = datetime.now()
                    age_seconds = (now - progress_time).total_seconds()
                    if age_seconds < 300:  # 5 minutes
                        should_send = True
                except:
                    pass

            if should_send:
                await websocket.send_json({"type": "progress", "data": initial_progress})

        last_progress = initial_progress
        last_timestamp = initial_progress.get("timestamp") if initial_progress else None

        while True:
            try:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                except asyncio.TimeoutError:
                    current_progress = progress_tracker.get_progress()
                    if current_progress:
                        current_timestamp = current_progress.get("timestamp")
                        if current_timestamp != last_timestamp:
                            await websocket.send_json(
                                {"type": "progress", "data": current_progress}
                            )
                            last_progress = current_progress
                            last_timestamp = current_timestamp

                            if current_progress.get("stage") in ["completed", "error"]:
                                await asyncio.sleep(3)
                                break
                    continue

            except WebSocketDisconnect:
                break
            except Exception:
                break

    except Exception as e:
        logger.debug(f"Progress WS error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        await broadcaster.disconnect(kb_name, websocket)
        try:
            await websocket.close()
        except:
            pass
