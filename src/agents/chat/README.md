# Chat Module

Lightweight conversational AI module with multi-turn dialogue support and session management.

## Features

- **Multi-turn Conversation**: Maintains conversation history as context for LLM
- **Token Management**: Automatic truncation of history to fit within token limits
- **RAG Integration**: Optional knowledge base retrieval
- **Web Search**: Optional web search for up-to-date information
- **Session Management**: Persistent storage of chat sessions
- **Streaming Support**: Real-time response streaming via WebSocket

## Components

### ChatAgent

The main conversational agent that:
- Inherits from `BaseAgent` for unified LLM access
- Supports RAG and Web Search augmentation
- Manages conversation history with token limits
- Provides streaming responses

### SessionManager

Manages chat sessions:
- Create, update, retrieve, and delete sessions
- Store sessions in `data/user/chat_sessions.json`
- List recent sessions for history display

## Usage

```python
from src.agents.chat import ChatAgent, SessionManager

# Initialize agent
agent = ChatAgent(language="en")

# Process a message
response = await agent.process(
    message="What is backpropagation?",
    history=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ],
    kb_name="ai_textbook",
    enable_rag=True,
    enable_web_search=False
)

# Session management
session_mgr = SessionManager()
session = session_mgr.create_session("First question")
session_mgr.update_session(session["session_id"], messages)
```

## Configuration

The agent uses prompts from:
- `prompts/en/chat_agent.yaml` (English)
- `prompts/zh/chat_agent.yaml` (Chinese)

Token limits and other parameters are configured in `config/agents.yaml`.
