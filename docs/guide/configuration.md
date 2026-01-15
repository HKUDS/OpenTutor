# Configuration

DeepTutor uses YAML configuration files and environment variables for easy customization.

## 📁 Configuration Files

```
config/
├── main.yaml              # Main system configuration (paths, tools, module settings)
├── agents.yaml            # Unified agent parameters (temperature, max_tokens)
└── README.md              # Full documentation
```

| File | Purpose |
|:-----|:--------|
| `.env` | API keys, server ports, and service configuration |
| `config/agents.yaml` | LLM parameters for each agent module |
| `config/main.yaml` | Paths, tools, module settings |

## 🔧 Server Configuration

Server ports are configured in `.env` file:

```bash
# Server ports (defaults: 8001/3782)
BACKEND_PORT=8001
FRONTEND_PORT=3782

# Remote access
NEXT_PUBLIC_API_BASE=http://your-server-ip:8001

# Web search (unified API key)
SEARCH_PROVIDER=perplexity  # Options: perplexity, tavily, serper, jina, exa, baidu
SEARCH_API_KEY=your_search_api_key

# TTS
TTS_MODEL=
TTS_URL=
TTS_API_KEY=
```

### ☁️ Azure OpenAI Configuration

When using Azure OpenAI, you must set the `LLM_API_VERSION` and provide the correct endpoint URL including the deployment name.

```bash
LLM_BINDING=azure_openai
LLM_MODEL=gpt-4o  # Your Azure deployment name
LLM_HOST=https://{your-resource}.openai.azure.com/openai/deployments/{deployment-id}
LLM_API_KEY=your_azure_api_key
LLM_API_VERSION=2024-02-15-preview  # Required for Azure
```

Similarly for embeddings:

```bash
EMBEDDING_BINDING=azure_openai
EMBEDDING_MODEL=text-embedding-3-large  # Your Azure deployment name
EMBEDDING_HOST=https://{your-resource}.openai.azure.com/openai/deployments/{deployment-id}
EMBEDDING_API_KEY=your_azure_api_key
EMBEDDING_API_VERSION=2024-02-15-preview
```

## Agent Parameters

Edit `config/agents.yaml`:

```yaml
# Solve Module - Problem solving agents
solve:
  temperature: 0.3
  max_tokens: 8192

# Research Module - Deep research agents
research:
  temperature: 0.5
  max_tokens: 12000

# Question Module - Question generation agents
question:
  temperature: 0.7
  max_tokens: 4096

# Guide Module - Learning guidance agents
guide:
  temperature: 0.5
  max_tokens: 8192

# IdeaGen Module - Idea generation agents
ideagen:
  temperature: 0.7
  max_tokens: 4096

# CoWriter Module - Collaborative writing agents
co_writer:
  temperature: 0.7
  max_tokens: 4096
```

## 🔑 Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# ============================================================================
# Server Configuration
# ============================================================================
BACKEND_PORT=8001                         # Backend API port
FRONTEND_PORT=3782                        # Frontend web port

# For remote/LAN access - set to your server's IP address
# Example: http://192.168.1.100:8001 (if not set, defaults to localhost)
# NEXT_PUBLIC_API_BASE=http://your-server-ip:8001

# ============================================================================
# LLM (Large Language Model) Configuration - Required
# ============================================================================
LLM_BINDING=openai                        # Provider type (see supported list below)
LLM_MODEL=gpt-4o                          # e.g., gpt-4o, deepseek-chat, qwen-plus
LLM_HOST=https://api.openai.com/v1
LLM_API_KEY=your_api_key
DISABLE_SSL_VERIFY=false                  # Set true for self-signed certificates

# ============================================================================
# Embedding Model Configuration - Required for Knowledge Base
# ============================================================================
EMBEDDING_BINDING=openai                  # Provider type (see supported list below)
EMBEDDING_MODEL=text-embedding-3-large    # e.g., text-embedding-3-large, nomic-embed-text
EMBEDDING_DIMENSION=3072                  # Important! Must match model dimensions
EMBEDDING_HOST=https://api.openai.com/v1
EMBEDDING_API_KEY=your_api_key

# ============================================================================
# Web Search Configuration - Optional
# ============================================================================
SEARCH_PROVIDER=perplexity                # Options: perplexity, tavily, serper, jina, exa, baidu
SEARCH_API_KEY=your_search_api_key        # Unified API key for all search providers

# ============================================================================
# TTS (Text-to-Speech) Configuration - Optional
# ============================================================================
TTS_MODEL=
TTS_URL=
TTS_API_KEY=
```

## 🔌 Supported Providers

### LLM Providers

| Provider | `LLM_BINDING` Value | Notes |
|:---------|:--------------------|:------|
| OpenAI | `openai` | GPT-4o, GPT-4, GPT-3.5, etc. |
| Anthropic | `anthropic` | Claude 3.5, Claude 3, etc. |
| Azure OpenAI | `azure_openai` | Enterprise deployments |
| Ollama | `ollama` | Local models (auto adds `/v1` suffix) |
| Groq | `groq` | Fast inference |
| OpenRouter | `openrouter` | Multi-model gateway |
| DeepSeek | `deepseek` | DeepSeek-V3, DeepSeek-R1 |
| Google Gemini | `gemini` | OpenAI-compatible mode |

### Embedding Providers

| Provider | `EMBEDDING_BINDING` Value | Notes |
|:---------|:--------------------------|:------|
| OpenAI | `openai` | text-embedding-3-large/small |
| Azure OpenAI | `azure_openai` | Enterprise deployments |
| Jina AI | `jina` | jina-embeddings-v3 |
| Cohere | `cohere` | embed-v3 series |
| Ollama | `ollama` | Local embedding models |
| LM Studio | `lm_studio` | Local inference server |
| HuggingFace | `huggingface` | OpenAI-compatible endpoints |

> **Note**: Ensure that `EMBEDDING_DIMENSION` matches your embedding model's output dimensions. The RAG module uses RAG-Anything—see [the repository](https://github.com/HKUDS/RAG-Anything) for details.

## 🛠️ Tool Configuration

Configure tool availability in `config/main.yaml`:

```yaml
tools:
  rag_tool:
    kb_base_dir: ./data/knowledge_bases
    default_kb: ai_textbook
  run_code:
    workspace: ./data/user/run_code_workspace
  web_search:
    enabled: true  # Global switch for web search
  query_item:
    enabled: true
    max_results: 5
```

## 📂 Data Storage

All user content and system data are stored in the `data/` directory:

```
data/
├── knowledge_bases/              # Knowledge base storage
└── user/                         # User activity data
    ├── solve/                    # Problem solving results
    ├── question/                 # Generated questions
    ├── research/                 # Research reports and cache
    ├── co_writer/                # Interactive IdeaGen documents
    ├── notebook/                 # Notebook records
    ├── guide/                    # Guided learning sessions
    ├── logs/                     # System logs
    └── run_code_workspace/       # Code execution workspace
```

## 🔗 Advanced Configuration

For the full configuration reference, see [config/README.md](https://github.com/HKUDS/DeepTutor/tree/main/config).
