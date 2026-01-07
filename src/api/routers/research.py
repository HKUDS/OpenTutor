import asyncio
import logging
from pathlib import Path
import sys
import traceback
from typing import Any

from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from src.agents.research.agents import RephraseAgent
from src.agents.research.research_pipeline import ResearchPipeline
from src.api.utils.history import ActivityType, history_manager
from src.api.utils.task_id_manager import TaskIDManager
from src.core.core import get_llm_config, load_config_with_main
from src.core.logging import get_logger

# Force stdout to use utf-8 to prevent encoding errors with emojis on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

router = APIRouter()


# Helper to load config (with main.yaml merge)
def load_config():
    project_root = Path(__file__).parent.parent.parent.parent
    return load_config_with_main("research_config.yaml", project_root)


# Initialize logger with config
config = load_config()
log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get("log_dir")
logger = get_logger("ResearchAPI", log_dir=log_dir)


class OptimizeRequest(BaseModel):
    topic: str
    iteration: int = 0
    previous_result: dict[str, Any] | None = None
    kb_name: str | None = "ai_textbook"


@router.post("/optimize_topic")
async def optimize_topic(request: OptimizeRequest):
    try:
        config = load_config()

        # Inject API keys
        try:
            llm_config = get_llm_config()
            api_key = llm_config["api_key"]
            base_url = llm_config["base_url"]
        except Exception as e:
            return {"error": f"LLM config error: {e!s}"}

        # Init Agent
        agent = RephraseAgent(config=config, api_key=api_key, base_url=base_url)

        # Process
        # If iteration > 0, topic is treated as feedback
        if request.iteration == 0:
            result = await agent.process(request.topic, iteration=0)
        else:
            result = await agent.process(
                request.topic, iteration=request.iteration, previous_result=request.previous_result
            )

        return result

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@router.websocket("/run")
async def websocket_research_run(websocket: WebSocket):
    await websocket.accept()

    # Get task ID manager
    task_manager = TaskIDManager.get_instance()

    pusher_task = None
    progress_pusher_task = None
    original_stdout = sys.stdout  # Save original stdout at the start

    try:
        # 1. Wait for config
        data = await websocket.receive_json()
        topic = data.get("topic")
        kb_name = data.get("kb_name", "ai_textbook")
        # New unified parameters
        plan_mode = data.get("plan_mode", "medium")  # quick, medium, deep, auto
        enabled_tools = data.get("enabled_tools", ["RAG"])  # RAG, Paper, Web
        skip_rephrase = data.get("skip_rephrase", False)
        # Legacy support
        preset = data.get("preset")  # For backward compatibility
        research_mode = data.get("research_mode")

        if not topic:
            await websocket.send_json({"type": "error", "content": "Topic is required"})
            return

        # Generate task ID
        task_key = f"research_{kb_name}_{hash(str(topic))}"
        task_id = task_manager.generate_task_id("research", task_key)

        # Send task ID to frontend
        await websocket.send_json({"type": "task_id", "task_id": task_id})

        # Use unified logger
        config = load_config()
        try:
            # Get log_dir from config
            log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get(
                "log_dir"
            )
            research_logger = get_logger("Research", log_dir=log_dir)
            research_logger.info(f"[{task_id}] Starting research flow: {topic[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to initialize research logger: {e}")

        # 2. Initialize Pipeline
        # Initialize nested config structures from research.* (main.yaml structure)
        # This ensures all research module configs are properly inherited from main.yaml
        research_config = config.get("research", {})

        # Initialize planning config from research.planning
        if "planning" not in config:
            config["planning"] = research_config.get("planning", {}).copy()
        else:
            # Merge with research.planning defaults
            default_planning = research_config.get("planning", {})
            for key, value in default_planning.items():
                if key not in config["planning"]:
                    config["planning"][key] = value if not isinstance(value, dict) else value.copy()
                elif isinstance(value, dict) and isinstance(config["planning"][key], dict):
                    # Deep merge for nested dicts like decompose, rephrase
                    for k, v in value.items():
                        if k not in config["planning"][key]:
                            config["planning"][key][k] = v

        # Ensure decompose and rephrase exist
        if "decompose" not in config["planning"]:
            config["planning"]["decompose"] = {}
        if "rephrase" not in config["planning"]:
            config["planning"]["rephrase"] = {}

        # Initialize researching config from research.researching
        # This ensures execution_mode, max_parallel_topics etc. are properly inherited
        if "researching" not in config:
            config["researching"] = research_config.get("researching", {}).copy()
        else:
            # Merge with research.researching defaults (research.researching has lower priority)
            default_researching = research_config.get("researching", {})
            for key, value in default_researching.items():
                if key not in config["researching"]:
                    config["researching"][key] = value

        # Initialize reporting config from research.reporting
        # This ensures enable_citation_list, enable_inline_citations etc. are properly inherited
        if "reporting" not in config:
            config["reporting"] = research_config.get("reporting", {}).copy()
        else:
            # Merge with research.reporting defaults
            default_reporting = research_config.get("reporting", {})
            for key, value in default_reporting.items():
                if key not in config["reporting"]:
                    config["reporting"][key] = value

        # Apply plan_mode configuration (unified approach affecting both planning and researching)
        # Each mode defines:
        # - Planning: tree depth (subtopics count) and mode (manual/auto)
        # - Researching: max iterations per topic and iteration_mode (fixed/flexible)
        plan_mode_config = {
            "quick": {
                "planning": {"decompose": {"initial_subtopics": 2, "mode": "manual"}},
                "researching": {"max_iterations": 2, "iteration_mode": "fixed"},
            },
            "medium": {
                "planning": {"decompose": {"initial_subtopics": 5, "mode": "manual"}},
                "researching": {"max_iterations": 4, "iteration_mode": "fixed"},
            },
            "deep": {
                "planning": {"decompose": {"initial_subtopics": 8, "mode": "manual"}},
                "researching": {"max_iterations": 7, "iteration_mode": "fixed"},
            },
            "auto": {
                "planning": {"decompose": {"mode": "auto", "auto_max_subtopics": 8}},
                "researching": {"max_iterations": 6, "iteration_mode": "flexible"},
            },
        }
        if plan_mode in plan_mode_config:
            mode_cfg = plan_mode_config[plan_mode]
            # Apply planning configuration
            if "planning" in mode_cfg:
                for key, value in mode_cfg["planning"].items():
                    if key not in config["planning"]:
                        config["planning"][key] = {}
                    config["planning"][key].update(value)
            # Apply researching configuration
            if "researching" in mode_cfg:
                config["researching"].update(mode_cfg["researching"])

        # Legacy preset support (for backward compatibility)
        if preset and "presets" in config and preset in config["presets"]:
            preset_config = config["presets"][preset]
            for key, value in preset_config.items():
                if key in config and isinstance(value, dict):
                    config[key].update(value)

        # Apply enabled_tools configuration
        # RAG includes: rag_naive, rag_hybrid, query_item
        # Paper includes: paper_search
        # Web includes: web_search
        # run_code is always enabled
        config["researching"]["enable_rag_naive"] = "RAG" in enabled_tools
        config["researching"]["enable_rag_hybrid"] = "RAG" in enabled_tools
        config["researching"]["enable_query_item"] = "RAG" in enabled_tools
        config["researching"]["enable_paper_search"] = "Paper" in enabled_tools
        config["researching"]["enable_web_search"] = "Web" in enabled_tools
        config["researching"]["enable_run_code"] = True  # Always enabled

        # Store enabled_tools for prompt generation
        config["researching"]["enabled_tools"] = enabled_tools

        # Legacy research_mode support
        if research_mode:
            config["researching"]["research_mode"] = research_mode

        # If skip_rephrase is True, disable the internal rephrase step
        if skip_rephrase:
            config["planning"]["rephrase"]["enabled"] = False

        # Define unified output directory
        # Use project root directory user/research as unified output directory
        root_dir = Path(__file__).parent.parent.parent.parent
        output_base = root_dir / "data" / "user" / "research"

        # Update config with unified output paths
        if "system" not in config:
            config["system"] = {}

        config["system"]["output_base_dir"] = str(output_base / "cache")
        config["system"]["reports_dir"] = str(output_base / "reports")

        # Inject API keys from env if not in config
        try:
            llm_config = get_llm_config()
            api_key = llm_config["api_key"]
            base_url = llm_config["base_url"]
        except ValueError as e:
            await websocket.send_json({"error": f"LLM configuration error: {e!s}"})
            await websocket.close()
            return

        # 3. Setup Queues for log and progress
        log_queue = asyncio.Queue()
        progress_queue = asyncio.Queue()

        # Progress callback function
        def progress_callback(event: dict[str, Any]):
            """Progress callback function, puts progress events into queue"""
            try:
                asyncio.get_event_loop().call_soon_threadsafe(progress_queue.put_nowait, event)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

        pipeline = ResearchPipeline(
            config=config,
            api_key=api_key,
            base_url=base_url,
            kb_name=kb_name,
            progress_callback=progress_callback,
        )

        # 4. Background log pusher
        async def log_pusher():
            while True:
                try:
                    log = await log_queue.get()
                    if log is None:
                        break
                    await websocket.send_json({"type": "log", "content": log})
                    log_queue.task_done()
                except Exception as e:
                    logger.error(f"Log pusher error: {e}")
                    break

        # 5. Background progress pusher
        async def progress_pusher():
            while True:
                try:
                    event = await progress_queue.get()
                    if event is None:
                        break
                    await websocket.send_json(event)
                    progress_queue.task_done()
                except Exception as e:
                    logger.error(f"Progress pusher error: {e}")
                    break

        pusher_task = asyncio.create_task(log_pusher())
        progress_pusher_task = asyncio.create_task(progress_pusher())

        # 6. Run Pipeline with stdout interception
        class ResearchStdoutInterceptor:
            def __init__(self, queue):
                self.queue = queue
                self.original_stdout = sys.stdout

            def write(self, message):
                # Write to terminal first to ensure terminal output is not blocked
                self.original_stdout.write(message)
                # Then try to send to frontend (non-blocking, failure doesn't affect terminal output)
                if message.strip():
                    try:
                        # Use call_soon_threadsafe for thread safety
                        loop = asyncio.get_event_loop()
                        loop.call_soon_threadsafe(self.queue.put_nowait, message)
                    except (asyncio.QueueFull, RuntimeError, AttributeError):
                        # Queue full, event loop closed, or no event loop, ignore error, doesn't affect terminal output
                        pass

            def flush(self):
                self.original_stdout.flush()

        sys.stdout = ResearchStdoutInterceptor(log_queue)

        try:
            await websocket.send_json(
                {"type": "status", "content": "started", "research_id": pipeline.research_id}
            )

            result = await pipeline.run(topic)

            # Send final report content
            with open(result["final_report_path"], encoding="utf-8") as f:
                report_content = f.read()

            # Save to history
            history_manager.add_entry(
                activity_type=ActivityType.RESEARCH,
                title=topic,
                content={"topic": topic, "report": report_content, "kb_name": kb_name},
                summary=f"Research ID: {result['research_id']}",
            )

            await websocket.send_json(
                {
                    "type": "result",
                    "report": report_content,
                    "metadata": result["metadata"],
                    "research_id": result["research_id"],
                }
            )

            # Update task status to completed
            try:
                log_dir = config.get("paths", {}).get("user_log_dir") or config.get(
                    "logging", {}
                ).get("log_dir")
                research_logger = get_logger("Research", log_dir=log_dir)
                research_logger.success(f"[{task_id}] Research flow completed: {topic[:50]}...")
                task_manager.update_task_status(task_id, "completed")
            except Exception as e:
                logger.warning(f"Failed to log completion: {e}")

        finally:
            sys.stdout = original_stdout  # Safely restore using saved reference

    except Exception as e:
        await websocket.send_json({"type": "error", "content": str(e)})
        logging.error(f"Research error: {e}", exc_info=True)

        # Update task status to error
        try:
            log_dir = config.get("paths", {}).get("user_log_dir") or config.get("logging", {}).get(
                "log_dir"
            )
            research_logger = get_logger("Research", log_dir=log_dir)
            research_logger.error(f"[{task_id}] Research flow failed: {e}")
            task_manager.update_task_status(task_id, "error", error=str(e))
        except Exception as log_err:
            logger.warning(f"Failed to log error: {log_err}")
    finally:
        if pusher_task:
            pusher_task.cancel()
        if progress_pusher_task:
            progress_pusher_task.cancel()
