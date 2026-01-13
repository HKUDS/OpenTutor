# Co-Writer Module

The Co-Writer module provides AI-powered text editing and narration capabilities, including text rewriting, automatic annotation, and text-to-speech (TTS) generation.

## 📋 Overview

The Co-Writer module consists of two main agents:

1. **EditAgent**: AI-powered text editing (rewrite, shorten, expand) with optional RAG/web search context
2. **NarratorAgent**: Converts text content into narration scripts and generates TTS audio

## 🏗️ Architecture

```
co_writer/
├── __init__.py
├── edit_agent.py          # Text editing agent
├── narrator_agent.py      # TTS narration agent
├── prompts/               # Bilingual prompts (YAML)
│   ├── zh/               # Chinese prompts
│   │   ├── edit_agent.yaml
│   │   └── narrator_agent.yaml
│   └── en/               # English prompts
│       ├── edit_agent.yaml
│       └── narrator_agent.yaml
└── README.md
```

## 🔧 Components

### EditAgent

**Purpose**: AI-powered text editing with context enhancement

**Features**:
- **Rewrite**: Rewrite text based on instructions
- **Shorten**: Compress text while preserving key information
- **Expand**: Expand text with additional details
- **Context Enhancement**: Optional RAG or web search for additional context

**Methods**:
```python
async def process(
    text: str,
    instruction: str,
    action: Literal["rewrite", "shorten", "expand"] = "rewrite",
    source: Optional[Literal["rag", "web"]] = None,
    kb_name: Optional[str] = None
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "edited_text": str,        # Edited text content
    "operation_id": str,       # Unique operation ID
    "tool_call_file": str      # Path to tool call history (if source used)
}
```

**Usage Example**:
```python
from src.agents.co_writer.edit_agent import EditAgent

agent = EditAgent()

# Rewrite with RAG context
result = await agent.process(
    text="Original text...",
    instruction="Make it more formal",
    action="rewrite",
    source="rag",
    kb_name="ai_textbook"
)

print(result["edited_text"])
```

### NarratorAgent

**Purpose**: Convert text content into narration scripts and generate TTS audio

**Features**:
- **Script Generation**: Converts text into natural narration scripts
- **TTS Generation**: Generates audio files using DashScope TTS API
- **Voice Selection**: Supports multiple voices (Cherry, Stella, Annie, Cally, Eva, Bella)
- **Language Support**: Supports Chinese and English

**Methods**:
```python
async def generate_narration(
    content: str,
    voice: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "audio_url": str,          # URL to generated audio file
    "audio_path": str,          # Local path to audio file
    "script": str,              # Generated narration script
    "operation_id": str        # Unique operation ID
}
```

**Usage Example**:
```python
from src.agents.co_writer.narrator_agent import NarratorAgent

agent = NarratorAgent()

result = await agent.generate_narration(
    content="Your text content here...",
    voice="Cherry",
    language="English"
)

print(f"Audio URL: {result['audio_url']}")
```

## 📁 Data Storage

All Co-Writer outputs are stored in `data/user/co-writer/`:

```
data/user/co-writer/
├── audio/                    # TTS audio files
│   └── {operation_id}.mp3
├── tool_calls/               # Tool call history
│   └── {operation_id}_{tool_type}.json
└── history.json              # Edit history
```

## ⚙️ Configuration

### TTS Configuration

TTS settings are configured in `config/main.yaml`:

```yaml
tts:
  default_voice: "Cherry"      # Default voice
  default_language: "English"   # Default language
```

### Environment Variables

Required for TTS (in `.env` or `DeepTutor.env`):

```bash
# DashScope TTS API (for NarratorAgent)
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_TTS_MODEL=sambert-zhichu-v1  # or other TTS model
```

### LLM Configuration

Required for EditAgent (same as other modules):

```bash
LLM_API_KEY=your_api_key
LLM_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

## 🔌 API Integration

The Co-Writer module is exposed via FastAPI routes in `src/api/routers/co_writer.py`:

### Endpoints

- `POST /api/v1/co_writer/edit` - Text editing
- `POST /api/v1/co_writer/automark` - Automatic annotation
- `POST /api/v1/co_writer/narrate` - Generate narration and TTS

### Request Format

**Edit Request**:
```json
{
  "text": "Original text...",
  "instruction": "Make it more formal",
  "action": "rewrite",
  "source": "rag",
  "kb_name": "ai_textbook"
}
```

**Narrate Request**:
```json
{
  "content": "Text to narrate...",
  "voice": "Cherry",
  "language": "English"
}
```

## 🎯 Use Cases

### 1. Text Rewriting

Rewrite text with specific instructions:

```python
result = await edit_agent.process(
    text="The quick brown fox jumps over the lazy dog.",
    instruction="Make it more academic and formal",
    action="rewrite"
)
```

### 2. Text Compression

Shorten text while preserving key information:

```python
result = await edit_agent.process(
    text="Long text content...",
    instruction="Summarize to 50 words",
    action="shorten"
)
```

### 3. Text Expansion

Expand text with additional details:

```python
result = await edit_agent.process(
    text="Brief description...",
    instruction="Add more technical details",
    action="expand",
    source="rag",
    kb_name="ai_textbook"
)
```

### 4. Audio Narration

Convert text to audio:

```python
result = await narrator_agent.generate_narration(
    content="Your educational content...",
    voice="Cherry",
    language="English"
)
```

## 📊 Statistics Tracking

Both agents track LLM usage statistics:

```python
from src.agents.co_writer.edit_agent import get_stats, print_stats

# Print statistics
print_stats()
```

## 🔗 Related Modules

- **API Routes**: `src/api/routers/co_writer.py` - REST API endpoints
- **RAG Tool**: `src/tools/rag_tool.py` - Knowledge base retrieval
- **Web Search**: `src/tools/web_search.py` - Web search for context
- **Core Config**: `src/core/core.py` - Configuration management

## 🛠️ Development

### Adding New Actions

To add a new editing action:

1. Add the action type to `Literal` type hint in `edit_agent.py`
2. Add the corresponding prompts to YAML files in `prompts/en/` and `prompts/zh/`
3. Test with various inputs

### Prompts Configuration

Prompts are stored in YAML files under `prompts/` directory with bilingual support:

```yaml
# prompts/en/edit_agent.yaml
system: |
  You are an expert editor and writing assistant.

auto_mark_system: |
  You are a professional academic reading annotation assistant...
```

The `language` parameter (default: "en") determines which prompts directory to use.

### Adding New Voices

To add support for new TTS voices:

1. Check DashScope TTS API documentation for available voices
2. Update voice validation in `narrator_agent.py`
3. Update `config/main.yaml` if needed

## ⚠️ Notes

1. **TTS API Key**: NarratorAgent requires DashScope API key (different from LLM API key)
2. **Audio Storage**: Audio files are stored in `data/user/co-writer/audio/` and served via `/api/outputs/`
3. **Tool Call History**: All RAG/web search calls are logged in `tool_calls/` directory
4. **History Management**: Edit history is automatically saved to `history.json`

## 📝 Example Workflow

```python
from src.agents.co_writer.edit_agent import EditAgent
from src.agents.co_writer.narrator_agent import NarratorAgent

# 1. Edit text with RAG context
edit_agent = EditAgent()
edited = await edit_agent.process(
    text="Original content...",
    instruction="Make it clearer and more detailed",
    action="rewrite",
    source="rag",
    kb_name="ai_textbook"
)

# 2. Generate narration
narrator = NarratorAgent()
audio = await narrator.generate_narration(
    content=edited["edited_text"],
    voice="Cherry",
    language="English"
)

print(f"Edited text: {edited['edited_text']}")
print(f"Audio URL: {audio['audio_url']}")
```
