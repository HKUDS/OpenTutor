from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers import (
    agent_config,
    chat,
    co_writer,
    dashboard,
    embedding_provider,
    guide,
    ideagen,
    knowledge,
    llm_provider,
    notebook,
    question,
    research,
    settings,
    solve,
    system,
)
from src.logging import get_logger

logger = get_logger("API")


def validate_tool_consistency():
    """
    Validate that the tools configured for agents are consistent with the main application
    configuration.

    This function loads the main configuration (``main.yaml``) and the agents configuration
    (``agents.yaml``) from the project root and compares:

    * ``solve.valid_tools`` in ``main.yaml``
    * ``investigate.valid_tools`` in ``agents.yaml``

    All tools referenced by agents must be present in the main configuration. If any tools are
    defined for agents that are not listed in the main configuration, a ``RuntimeError`` is
    raised describing the drift. The error is logged and re-raised, which causes the FastAPI
    application startup to fail when this function is called from the ``lifespan`` handler.

    Impact on startup
    ------------------
    This validation runs during application startup. Any configuration drift will:

    * Be logged as an error with details about the unknown tools.
    * Prevent the API from starting until the configuration is corrected.

    How to resolve configuration drift
    ----------------------------------
    If startup fails with a configuration drift error:

    1. Inspect the set of tools reported in the error message.
    2. Either:
       * Add the missing tools to ``solve.valid_tools`` in ``main.yaml``, **or**
       * Remove or rename the offending tools from ``investigate.valid_tools`` in ``agents.yaml``.
    3. Restart the application after updating the configuration files.

    Example of aligned configuration
    --------------------------------
    ``main.yaml``::

        solve:
          valid_tools:
            - web_search
            - code_execution

    ``agents.yaml``::

        investigate:
          valid_tools:
            - web_search

    In this case, validation passes because ``investigate.valid_tools`` is a subset of
    ``solve.valid_tools``.

    Example of configuration drift
    ------------------------------
    ``agents.yaml``::

        investigate:
          valid_tools:
            - web_search
            - unknown_tool

    Here, ``unknown_tool`` is not present in ``solve.valid_tools`` in ``main.yaml``, so
    validation will fail and prevent the application from starting until the configurations
    are aligned.
    """
    try:
        from src.services.config import load_config_with_main

        project_root = Path(__file__).parent.parent.parent
        main_config = load_config_with_main("main.yaml", project_root)
        agent_config = load_config_with_main("agents.yaml", project_root)

        main_tools = set(main_config.get("solve", {}).get("valid_tools", []))
        agent_tools = set(agent_config.get("investigate", {}).get("valid_tools", []))

        if not agent_tools.issubset(main_tools):
            drift = agent_tools - main_tools
            raise RuntimeError(
                "Configuration Drift Detected: Tools "
                f"{drift} found in agents.yaml investigate.valid_tools but missing from main.yaml solve.valid_tools. "
                "Add these tools to main.yaml solve.valid_tools or remove them from agents.yaml investigate.valid_tools."
            )
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management
    Gracefully handle startup and shutdown events, avoid CancelledError
    """
    # Execute on startup
    logger.info("Application startup")

    # Validate configuration consistency
    validate_tool_consistency()

    yield
    # Execute on shutdown
    logger.info("Application shutdown")


app = FastAPI(title="DeepTutor API", version="1.0.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount user directory as static root for generated artifacts
# This allows frontend to access generated artifacts (images, PDFs, etc.)
# URL: /api/outputs/solve/solve_xxx/artifacts/image.png
# Physical Path: DeepTutor/data/user/solve/solve_xxx/artifacts/image.png
project_root = Path(__file__).parent.parent.parent
user_dir = project_root / "data" / "user"

# Initialize user directories on startup
try:
    from src.services.setup import init_user_directories

    init_user_directories(project_root)
except Exception:
    # Fallback: just create the main directory if it doesn't exist
    if not user_dir.exists():
        user_dir.mkdir(parents=True)

app.mount("/api/outputs", StaticFiles(directory=str(user_dir)), name="outputs")

# Include routers
app.include_router(solve.router, prefix="/api/v1", tags=["solve"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(question.router, prefix="/api/v1/question", tags=["question"])
app.include_router(research.router, prefix="/api/v1/research", tags=["research"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(co_writer.router, prefix="/api/v1/co_writer", tags=["co_writer"])
app.include_router(notebook.router, prefix="/api/v1/notebook", tags=["notebook"])
app.include_router(guide.router, prefix="/api/v1/guide", tags=["guide"])
app.include_router(ideagen.router, prefix="/api/v1/ideagen", tags=["ideagen"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(llm_provider.router, prefix="/api/v1/config/llm", tags=["config"])
app.include_router(embedding_provider.router, prefix="/api/v1/config/embedding", tags=["config"])
app.include_router(agent_config.router, prefix="/api/v1/config", tags=["config"])


@app.get("/")
async def root():
    return {"message": "Welcome to DeepTutor API"}


if __name__ == "__main__":
    from pathlib import Path

    import uvicorn

    # Get project root directory
    project_root = Path(__file__).parent.parent.parent

    # Ensure project root is in Python path
    import sys

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Get port from configuration
    from src.services.setup import get_backend_port

    backend_port = get_backend_port(project_root)

    # Configure reload_excludes with absolute paths to properly exclude directories
    venv_dir = project_root / "venv"
    data_dir = project_root / "data"
    reload_excludes = [
        str(d)
        for d in [
            venv_dir,
            project_root / ".venv",
            data_dir,
            project_root / "web" / "node_modules",
            project_root / "web" / ".next",
            project_root / ".git",
        ]
        if d.exists()
    ]

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=backend_port,
        reload=True,
        reload_excludes=reload_excludes,
    )
