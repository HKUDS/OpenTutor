# Quick Start

Get DeepTutor running in under 5 minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- An LLM API key (OpenAI, Anthropic, DeepSeek, etc.)

## Installation

::: code-group

```bash [Quick Install]
# Clone and setup
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Install and launch
bash scripts/install_all.sh
python scripts/start_web.py
```

```bash [Docker]
docker run -d --name deeptutor \
  -p 8001:8001 -p 3782:3782 \
  -e LLM_MODEL=gpt-4o \
  -e LLM_API_KEY=your-key \
  -e LLM_HOST=https://api.openai.com/v1 \
  -e EMBEDDING_MODEL=text-embedding-3-large \
  -e EMBEDDING_API_KEY=your-key \
  -e EMBEDDING_HOST=https://api.openai.com/v1 \
  ghcr.io/hkuds/deeptutor:latest
```

:::

## Essential `.env` Variables

```bash
# Required
LLM_MODEL=gpt-4o
LLM_API_KEY=your_api_key
LLM_HOST=https://api.openai.com/v1

EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_API_KEY=your_api_key
EMBEDDING_HOST=https://api.openai.com/v1
```

> 📖 **Full configuration options**: See [Configuration](/guide/configuration) or [README](https://github.com/HKUDS/DeepTutor#step-1-pre-configuration)

## Access Points

| Service | URL |
|:--------|:----|
| **Web App** | http://localhost:3782 |
| **API Docs** | http://localhost:8001/docs |

## Your First Knowledge Base

1. Navigate to http://localhost:3782/knowledge
2. Click **"New Knowledge Base"**
3. Upload PDF, TXT, or Markdown files
4. Wait for processing to complete

That's it! Start exploring with the **Solver**, **Question Generator**, or **Deep Research** modules.

## Next Steps

- [Configuration →](/guide/configuration)
- [Troubleshooting →](/guide/troubleshooting)
- [Full Installation Guide →](https://github.com/HKUDS/DeepTutor#-getting-started)
