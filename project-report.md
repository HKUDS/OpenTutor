# DeepTutor Fork - Project Report

**Date:** 2026-01-06
**Repository:** Laksh-star/DeepTutor
**Branch:** claude/explore-fork-use-cases-W1Xox

---

## Session Summary

### User Request
User forked the DeepTutor repository and asked to:
1. Understand the project and its capabilities
2. Identify top 3 use cases with minor modifications
3. Set up and run the project in the current environment

---

## What is DeepTutor?

DeepTutor is an **AI-powered multi-agent learning assistant** developed by HKU Data Science Lab. It provides:

- **6 Core Agent Modules:**
  - Smart Solver (dual-loop problem solving)
  - Question Generator (custom + exam mimicking)
  - Deep Research (dynamic topic queue + RAG)
  - Guided Learning (interactive visualizations)
  - Automated IdeaGen (research idea discovery)
  - Interactive IdeaGen/Co-Writer (AI-assisted writing + TTS)

- **Tool Integration:**
  - RAG (LightRAG with knowledge graphs)
  - Web Search (Perplexity API)
  - Academic Paper Search (ArXiv)
  - Code Execution (Python sandbox)
  - Text-to-Speech

- **Technology Stack:**
  - Backend: FastAPI, Python 3.10+
  - Frontend: Next.js 16, React 19, TypeScript
  - LLM: OpenAI-compatible APIs (GPT-4, Claude, DeepSeek, etc.)
  - Embeddings: text-embedding-3-large/small

---

## Top 3 Use Cases Identified

### 1. Corporate Training & Internal Knowledge Assistant
**Current function:** Academic tutoring with Q&A and problem-solving

**Modifications needed:**
- Replace academic documents with company SOPs, policies, technical docs
- Adjust prompts in `src/agents/*/prompts/` for professional tone
- Configure `main.yaml` to point to internal knowledge base

**Use case:** Employee onboarding, policy Q&A, training quiz generation

---

### 2. Research Literature Review & Idea Generation Tool
**Current function:** Deep research on topics with paper search

**Modifications needed:**
- Enable paper search in `main.yaml` (`enable_paper_search: true`)
- Adjust research depth presets for longer papers
- Modify `src/agents/ideagen/` prompts for specific research domains

**Use case:** Graduate students/researchers can get automated literature reviews and generate novel research directions

---

### 3. Customer Support Knowledge Base with Q&A
**Current function:** Interactive guided learning with cited answers

**Modifications needed:**
- Load product documentation, FAQs, support tickets into knowledge base
- Simplify frontend (`web/`) to focus on chat interface
- Adjust `src/agents/solve/` prompts for support-style responses

**Use case:** Internal support tool with citation-backed answers from documentation

---

## Setup Progress

### Environment Configuration

Created `.env` with OpenRouter configuration:
```
LLM_BINDING=openai
LLM_MODEL=anthropic/claude-sonnet-4
LLM_BINDING_HOST=https://openrouter.ai/api/v1
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIM=1536
```

### Installation Status

| Step | Status |
|------|--------|
| Create .env file | Completed |
| Install Python dependencies | In Progress |
| Install frontend dependencies | Pending |
| Start backend + frontend | Pending |

---

## Key Files & Configuration

| File | Purpose |
|------|---------|
| `.env` | API keys and service configuration |
| `config/main.yaml` | Server ports, paths, tool settings |
| `config/agents.yaml` | LLM temperature/tokens per module |
| `src/agents/` | Agent implementations |
| `web/` | Next.js frontend |

---

## Access URLs (after startup)

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3782 |
| API Docs | http://localhost:8001/docs |

---

## Notes

- OpenRouter API provides access to multiple LLMs through unified endpoint
- Embedding model configured as `text-embedding-3-small` (1536 dims) for compatibility
- Demo knowledge bases available from Google Drive (uses 3072-dim embeddings)

---

## Next Steps

1. Complete dependency installation
2. Start backend and frontend services
3. Create a test knowledge base
4. Test the Smart Solver module
5. Explore Question Generator and Deep Research features

---

*Report generated automatically during Claude Code session*
