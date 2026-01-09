import asyncio
import base64
from datetime import datetime
from pathlib import Path
import re
import sys
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.agents.question import AgentCoordinator
from src.agents.question.tools.exam_mimic import mimic_exam_questions
from src.api.utils.history import ActivityType, history_manager
from src.api.utils.log_interceptor import LogInterceptor
from src.api.utils.task_id_manager import TaskIDManager

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import get_logger
from src.services.config import load_config_with_main
from src.services.llm.config import get_llm_config

# Setup module logger with unified logging system (from config)
project_root = Path(__file__).parent.parent.parent.parent
config = load_config_with_main("question_config.yaml", project_root)
log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get("log_dir")
logger = get_logger("QuestionAPI", log_dir=log_dir)

router = APIRouter()

# Output directory for mimic mode - use data/user/question
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MIMIC_OUTPUT_DIR = PROJECT_ROOT / "data" / "user" / "question" / "mimic_papers"


@router.websocket("/mimic")
async def websocket_mimic_generate(websocket: WebSocket):
    """
    WebSocket endpoint for mimic exam paper question generation.

    Supports two modes:
    1. Upload PDF directly via WebSocket (base64 encoded)
    2. Use a pre-parsed paper directory path

    Message format for PDF upload:
    {
        "mode": "upload",
        "pdf_data": "base64_encoded_pdf_content",
        "pdf_name": "exam.pdf",
        "kb_name": "knowledge_base_name",
        "max_questions": 5  // optional
    }

    Message format for pre-parsed:
    {
        "mode": "parsed",
        "paper_path": "directory_name",
        "kb_name": "knowledge_base_name",
        "max_questions": 5  // optional
    }
    """
    await websocket.accept()

    pusher_task = None
    original_stdout = sys.stdout

    try:
        # 1. Wait for config
        data = await websocket.receive_json()
        mode = data.get("mode", "parsed")  # "upload" or "parsed"
        kb_name = data.get("kb_name", "ai_textbook")
        max_questions = data.get("max_questions")

        logger.info(f"Starting mimic generation (mode: {mode}, kb: {kb_name})")

        # 2. Setup Log Queue
        log_queue = asyncio.Queue()

        async def log_pusher():
            while True:
                entry = await log_queue.get()
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
                log_queue.task_done()

        pusher_task = asyncio.create_task(log_pusher())

        # 3. Stdout interceptor for capturing prints
        # ANSI escape sequence pattern for stripping color codes
        ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

        class StdoutInterceptor:
            def __init__(self, queue):
                self.queue = queue
                self.original_stdout = sys.stdout

            def write(self, message):
                # Write to terminal first (with ANSI codes for color)
                self.original_stdout.write(message)
                # Strip ANSI escape codes before sending to frontend
                clean_message = ANSI_ESCAPE_PATTERN.sub("", message).strip()
                # Then send to frontend (non-blocking)
                if clean_message:
                    try:
                        self.queue.put_nowait(
                            {
                                "type": "log",
                                "content": clean_message,
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        )
                    except (asyncio.QueueFull, RuntimeError):
                        pass

            def flush(self):
                self.original_stdout.flush()

        sys.stdout = StdoutInterceptor(log_queue)

        try:
            await websocket.send_json(
                {"type": "status", "stage": "init", "content": "Initializing..."}
            )

            pdf_path = None
            paper_dir = None

            # Handle PDF upload mode
            if mode == "upload":
                pdf_data = data.get("pdf_data")
                pdf_name = data.get("pdf_name", "exam.pdf")

                if not pdf_data:
                    await websocket.send_json(
                        {"type": "error", "content": "PDF data is required for upload mode"}
                    )
                    return

                # Create batch directory for this mimic session
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_stem = Path(pdf_name).stem
                batch_dir = MIMIC_OUTPUT_DIR / f"mimic_{timestamp}_{pdf_stem}"
                batch_dir.mkdir(parents=True, exist_ok=True)

                # Save uploaded PDF in batch directory
                pdf_path = batch_dir / pdf_name

                await websocket.send_json(
                    {"type": "status", "stage": "upload", "content": f"Saving PDF: {pdf_name}"}
                )

                # Decode and save PDF
                pdf_bytes = base64.b64decode(pdf_data)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                await websocket.send_json(
                    {
                        "type": "status",
                        "stage": "parsing",
                        "content": "Parsing PDF exam paper (MinerU)...",
                    }
                )
                logger.info(f"Saved uploaded PDF to: {pdf_path}")

                # Pass batch_dir as output directory
                pdf_path = str(pdf_path)
                output_dir = str(batch_dir)

            elif mode == "parsed":
                paper_path = data.get("paper_path")
                if not paper_path:
                    await websocket.send_json(
                        {"type": "error", "content": "paper_path is required for parsed mode"}
                    )
                    return
                paper_dir = paper_path

                # Create batch directory for parsed mode too
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                batch_dir = MIMIC_OUTPUT_DIR / f"mimic_{timestamp}_{Path(paper_path).name}"
                batch_dir.mkdir(parents=True, exist_ok=True)
                output_dir = str(batch_dir)

            else:
                await websocket.send_json({"type": "error", "content": f"Unknown mode: {mode}"})
                return

            # Create WebSocket callback for real-time progress updates
            async def ws_callback(event_type: str, data: dict):
                """Send progress updates to the frontend via WebSocket."""
                try:
                    message = {"type": event_type, **data}
                    await websocket.send_json(message)
                except Exception as e:
                    logger.debug(f"WebSocket send failed: {e}")

            # Run the complete mimic workflow with callback
            await websocket.send_json(
                {
                    "type": "status",
                    "stage": "processing",
                    "content": "Executing question generation workflow...",
                }
            )

            result = await mimic_exam_questions(
                pdf_path=pdf_path,
                paper_dir=paper_dir,
                kb_name=kb_name,
                output_dir=output_dir,
                max_questions=max_questions,
                ws_callback=ws_callback,
            )

            if result.get("success"):
                # Results are already sent via ws_callback during generation
                # Just send the final complete signal
                total_ref = result.get("total_reference_questions", 0)
                generated = result.get("generated_questions", [])
                failed = result.get("failed_questions", [])

                logger.success(
                    f"Mimic generation complete: {len(generated)} succeeded, {len(failed)} failed"
                )

                await websocket.send_json({"type": "complete"})
            else:
                error_msg = result.get("error", "Unknown error")
                await websocket.send_json({"type": "error", "content": error_msg})
                logger.error(f"Mimic generation failed: {error_msg}")

        finally:
            sys.stdout = original_stdout

    except WebSocketDisconnect:
        logger.debug("Client disconnected during mimic generation")
    except Exception as e:
        logger.error(f"Mimic generation error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass
    finally:
        sys.stdout = original_stdout
        if pusher_task:
            try:
                pusher_task.cancel()
                await pusher_task
            except:
                pass
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/generate")
async def websocket_question_generate(websocket: WebSocket):
    await websocket.accept()

    # Get task ID manager
    task_manager = TaskIDManager.get_instance()

    try:
        # 1. Wait for config
        data = await websocket.receive_json()
        requirement = data.get("requirement")
        kb_name = data.get("kb_name", "ai_textbook")
        count = data.get("count", 1)

        if not requirement:
            try:
                await websocket.send_json({"type": "error", "content": "Requirement is required"})
            except (RuntimeError, WebSocketDisconnect):
                pass
            return

        # Generate task ID
        task_key = f"question_{kb_name}_{hash(str(requirement))}"
        task_id = task_manager.generate_task_id("question_gen", task_key)

        # Send task ID to frontend
        try:
            await websocket.send_json({"type": "task_id", "task_id": task_id})
        except (RuntimeError, WebSocketDisconnect):
            logger.debug("WebSocket closed, cannot send task_id")
            return

        logger.info(
            f"[{task_id}] Starting question generation: {requirement.get('knowledge_point', 'Unknown')}"
        )

        # 2. Initialize Coordinator
        # Define unified output directory (DeepTutor/data/user/question)
        root_dir = Path(__file__).parent.parent.parent.parent
        output_base = root_dir / "data" / "user" / "question"

        try:
            llm_config = get_llm_config()
            api_key = llm_config.api_key
            base_url = llm_config.base_url
            api_version = getattr(llm_config, "api_version", None)
        except Exception:
            api_key = None
            base_url = None
            api_version = None

        coordinator = AgentCoordinator(
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            kb_name=kb_name,
            max_rounds=10,
            output_dir=str(output_base),
        )

        # 3. Setup Log Queue for WebSocket streaming
        log_queue = asyncio.Queue()

        # WebSocket callback for coordinator to send structured updates
        async def ws_callback(data: dict):
            try:
                await log_queue.put(data)
            except Exception:
                pass

        coordinator.set_ws_callback(ws_callback)

        # 4. Define background pusher for logs
        async def log_pusher():
            while True:
                entry = await log_queue.get()
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
                log_queue.task_done()

        pusher_task = asyncio.create_task(log_pusher())

        # 5. Setup LogInterceptor for capturing logger output (same as solve.py)
        # Get the coordinator's logger to intercept
        target_logger = coordinator.logger.logger
        interceptor = LogInterceptor(target_logger, log_queue)

        # 6. Run Generation with LogInterceptor
        try:
            with interceptor:
                try:
                    await websocket.send_json({"type": "status", "content": "started"})
                except (RuntimeError, WebSocketDisconnect):
                    logger.debug("WebSocket closed, stopping question generation")
                    return

                # Send initial agent status
                try:
                    await websocket.send_json(
                        {"type": "agent_status", "all_agents": coordinator.agent_status}
                    )
                except (RuntimeError, WebSocketDisconnect):
                    logger.debug("WebSocket closed, stopping question generation")
                    return

                # Use custom mode generation (new streamlined flow)
                logger.info(f"Starting custom mode generation for {count} question(s)")

                # Use the new custom generation method
                batch_result = await coordinator.generate_questions_custom(
                    base_requirement=requirement,
                    num_questions=count,
                )

                # Results are already sent via WebSocket callbacks in the coordinator
                # Just need to save to history for successful results
                for result in batch_result.get("results", []):
                    # Save to history
                    history_manager.add_entry(
                        activity_type=ActivityType.QUESTION,
                        title=f"{requirement.get('knowledge_point', 'Question')} ({requirement.get('question_type')})",
                        content={
                            "requirement": requirement,
                            "question": result.get("question", {}),
                            "validation": result.get("validation", {}),
                            "kb_name": kb_name,
                        },
                        summary=result.get("question", {}).get("question", "")[:100],
                    )

                # Send final token stats
                try:
                    await websocket.send_json(
                        {"type": "token_stats", "stats": coordinator.token_stats}
                    )
                except (RuntimeError, WebSocketDisconnect):
                    logger.debug("WebSocket closed, stopping question generation")

                # Send batch summary
                try:
                    await websocket.send_json(
                        {
                            "type": "batch_summary",
                            "requested": batch_result.get("requested", count),
                            "completed": batch_result.get("completed", 0),
                            "failed": batch_result.get("failed", 0),
                            "plan": batch_result.get("plan", {}),
                        }
                    )
                except (RuntimeError, WebSocketDisconnect):
                    pass

                if not batch_result.get("success"):
                    logger.warning(
                        f"Question generation had failures: {batch_result.get('failed', 0)} failed"
                    )

                # Wait for any pending messages in the queue to be sent
                # Give the pusher a moment to process remaining messages
                await asyncio.sleep(0.1)
                while not log_queue.empty():
                    await asyncio.sleep(0.05)

                # Send complete signal
                try:
                    await websocket.send_json({"type": "complete"})
                    logger.info(f"[{task_id}] Question generation completed")
                    task_manager.update_task_status(task_id, "completed")
                except (RuntimeError, WebSocketDisconnect):
                    logger.debug("WebSocket closed, cannot send complete signal")

        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Question generation error: {e}")
            logger.error(f"Error traceback:\n{error_traceback}")

            # Log additional context if available
            try:
                if "result" in locals():
                    logger.error(
                        f"Result type: {type(result)}, result keys: {result.keys() if isinstance(result, dict) else 'N/A'}"
                    )
                    if isinstance(result, dict) and "validation" in result:
                        validation = result["validation"]
                        logger.error(f"Validation type: {type(validation)}")
                        if isinstance(validation, dict):
                            logger.error(f"Validation keys: {validation.keys()}")
                            logger.error(
                                f"Issues type: {type(validation.get('issues'))}, value: {validation.get('issues')}"
                            )
                            logger.error(
                                f"Suggestions type: {type(validation.get('suggestions'))}, value: {validation.get('suggestions')}"
                            )
            except Exception as context_error:
                logger.warning(f"Failed to log error context: {context_error}")

            try:
                await websocket.send_json({"type": "error", "content": str(e)})
            except (RuntimeError, WebSocketDisconnect):
                logger.debug("WebSocket closed, cannot send error message")
            task_manager.update_task_status(task_id, "error", error=str(e))

        finally:
            pusher_task.cancel()
            try:
                await pusher_task
            except asyncio.CancelledError:
                pass
            await websocket.close()

    except WebSocketDisconnect:
        logger.debug("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
