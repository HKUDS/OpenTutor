# API Module

The API module provides REST and WebSocket endpoints for the DeepTutor system, enabling frontend-backend communication and real-time streaming.

## 📋 Overview

The API module is built on FastAPI and provides:
- REST API endpoints for standard HTTP requests
- WebSocket endpoints for real-time streaming
- Static file serving for generated artifacts
- CORS middleware for cross-origin requests
- Unified error handling and logging

## 🏗�?Architecture

```
api/
├── __init__.py
├── main.py                  # FastAPI application setup
├── run_server.py            # Server startup script
├── routers/                 # API route modules
�?  ├── solve.py            # Problem solving endpoints
�?  ├── question.py         # Question generation endpoints
�?  ├── research.py         # Research endpoints
�?  ├── knowledge.py        # Knowledge base endpoints
�?  ├── guide.py            # Guided learning endpoints
�?  ├── co_writer.py        # Co-Writer endpoints
�?  ├── notebook.py         # Notebook endpoints
�?  ├── ideagen.py          # Idea generation endpoints
�?  ├── dashboard.py        # Dashboard endpoints
�?  ├── settings.py         # Settings endpoints
�?  └── system.py           # System endpoints
└── utils/                   # API utilities
    ├── history.py          # Activity history management
    ├── log_interceptor.py  # Log interception for streaming
    ├── notebook_manager.py # Notebook management
    ├── progress_broadcaster.py  # Progress broadcasting
    └── task_id_manager.py  # Task ID management
```

## 🔧 Main Components

### main.py

**FastAPI Application Setup**

- Creates FastAPI app instance
- Configures CORS middleware
- Mounts static file directory for artifacts
- Includes all router modules
- Initializes user directories on startup

**Key Features**:
- Static file serving: `/api/outputs/` serves files from `data/user/`
- CORS enabled for all origins (configurable for production)
- Lifecycle management for graceful startup/shutdown

### Routers

Each router module handles endpoints for a specific feature:

#### solve.py
- `WS /api/v1/solve` - WebSocket endpoint for real-time problem solving

#### question.py
- `WS /api/v1/question/generate` - WebSocket endpoint for question generation

#### research.py
- `WS /api/v1/research/run` - WebSocket endpoint for research execution

#### knowledge.py
- `GET /api/v1/knowledge/list` - List knowledge bases
- `GET /api/v1/knowledge/{kb_name}` - Get knowledge base details
- `POST /api/v1/knowledge/create` - Create knowledge base
- `POST /api/v1/knowledge/{kb_name}/upload` - Upload documents

#### guide.py
- `POST /api/v1/guide/create_session` - Create learning session
- `POST /api/v1/guide/start` - Start learning
- `POST /api/v1/guide/next` - Move to next knowledge point
- `POST /api/v1/guide/chat` - Send chat message

#### co_writer.py
- `POST /api/v1/co_writer/edit` - Text editing
- `POST /api/v1/co_writer/automark` - Automatic annotation
- `POST /api/v1/co_writer/narrate` - Generate narration

#### notebook.py
- `GET /api/v1/notebook/list` - List notebooks
- `POST /api/v1/notebook/create` - Create notebook
- `GET /api/v1/notebook/{id}` - Get notebook details
- `PUT /api/v1/notebook/{id}` - Update notebook
- `DELETE /api/v1/notebook/{id}` - Delete notebook

#### dashboard.py
- `GET /api/v1/dashboard/recent` - Get recent activities

### Utilities

#### history.py
**Activity History Management**

Tracks user activities across modules:
- Solve activities
- Question generation activities
- Research activities
- Automatic history saving and retrieval

#### log_interceptor.py
**Log Interception for Streaming**

Intercepts logs from agents and broadcasts them via WebSocket for real-time updates.

#### progress_broadcaster.py
**Progress Broadcasting**

Broadcasts progress updates during long-running operations.

#### task_id_manager.py
**Task ID Management**

Manages unique task IDs for tracking operations.

## 🔌 API Endpoints

### WebSocket Endpoints

All WebSocket endpoints follow a similar pattern:

1. **Connection**: Client connects to WebSocket endpoint
2. **Initial Message**: Client sends initial request with parameters
3. **Streaming**: Server streams progress updates and results
4. **Completion**: Server sends final result and closes connection

**Example (Solve)**:
```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/solve');
ws.onopen = () => {
  ws.send(JSON.stringify({
    question: "Your question here",
    kb_name: "ai_textbook"
  }));
};
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### REST Endpoints

Standard REST API endpoints return JSON responses:

**Example (Knowledge Base List)**:
```bash
curl http://localhost:8001/api/v1/knowledge/list
```

## 📁 Static File Serving

The API serves static files from `data/user/` via `/api/outputs/`:

- **URL Pattern**: `/api/outputs/{module}/{path}`
- **Physical Path**: `data/user/{module}/{path}`

**Example**:
- URL: `/api/outputs/solve/solve_20250101_120000/final_answer.md`
- Path: `data/user/solve/solve_20250101_120000/final_answer.md`

## ⚙️ Configuration

### Server Port

Configured in `config/main.yaml`:

```yaml
server:
  backend_port: 8001
  frontend_port: 3782
```

### CORS

Currently allows all origins. For production, update in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific frontend URL
    ...
)
```

## 🚀 Running the Server

### Using run_server.py

```bash
python src/api/run_server.py
```

### Using uvicorn directly

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Using main.py

```bash
python src/api/main.py
```

## 🔗 Related Modules

- **Core**: `src/core/` - Configuration and logging
- **Agents**: `src/agents/` - Agent implementations
- **Tools**: `src/tools/` - Tool implementations
- **Frontend**: `web/` - Next.js frontend

## 🛠�?Development

### Adding a New Endpoint

1. Create or update router in `routers/`
2. Import and include in `main.py`:
   ```python
   from src.api.routers import my_router
   app.include_router(my_router.router, prefix="/api/v1", tags=["my_module"])
   ```

### Adding WebSocket Support

1. Create WebSocket endpoint in router:
   ```python
   @router.websocket("/my_endpoint")
   async def websocket_handler(websocket: WebSocket):
       await websocket.accept()
       # Handle messages
   ```

2. Use `LogInterceptor` for streaming logs:
   ```python
   from src.api.utils.log_interceptor import LogInterceptor
   interceptor = LogInterceptor(websocket)
   ```

### Error Handling

All endpoints should handle errors gracefully:

```python
try:
    # Operation
    await websocket.send_json({"type": "success", "data": result})
except Exception as e:
    logger.error(f"Error: {e}")
    await websocket.send_json({"type": "error", "content": str(e)})
```

## 📊 Logging

API endpoints use the core logging system:

```python
from src.logging import get_logger
logger = get_logger("MyAPI")
```

## ⚠️ Notes

1. **WebSocket Timeout**: WebSocket connections may timeout for long operations
2. **Static Files**: Ensure proper file permissions for static file serving
3. **CORS**: Configure CORS properly for production environments
4. **Error Handling**: Always handle WebSocket disconnections gracefully
