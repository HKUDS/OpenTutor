# Question Generation System

Intelligent question generation system with **modular agent architecture** supporting both knowledge base-driven custom generation and reference exam paper mimicking.

## 📁 Directory Structure

```
question/
├── __init__.py                    # Module exports
├── agents/                        # Specialized agents
│   ├── __init__.py
│   ├── retrieve_agent.py          # Knowledge retrieval from KB
│   ├── generate_agent.py          # Question generation
│   └── relevance_analyzer.py      # Question-KB relevance analysis
├── prompts/                       # Bilingual prompts (YAML)
│   ├── zh/                        # Chinese prompts
│   │   ├── retrieve_agent.yaml
│   │   ├── generate_agent.yaml
│   │   ├── relevance_analyzer.yaml
│   │   └── coordinator.yaml
│   └── en/                        # English prompts
│       └── (same structure)
├── coordinator.py                 # Workflow orchestration
├── example.py                     # Usage examples
└── README.md

# Tools moved to src/tools/question/
src/tools/question/
├── __init__.py
├── pdf_parser.py                  # PDF parsing with MinerU
├── question_extractor.py          # Extract questions from exams
└── exam_mimic.py                  # Reference-based question generation
```

## 🚀 Core Features

### Custom Mode (Knowledge Base-Driven)
- ✅ **Intelligent Search Query Generation** - Generates configurable number of RAG queries
- ✅ **Background Knowledge Acquisition** - Retrieves relevant knowledge using RAG
- ✅ **Question Planning** - Creates comprehensive plan with question IDs and focuses
- ✅ **Single-Pass Relevance Analysis** - Analyzes question relevance (no iteration/rejection)
- ✅ **Complete File Persistence** - Saves knowledge, plan, and individual results

### Mimic Mode (Reference Exam-Based)
- ✅ **PDF Parsing** - Automatic PDF extraction using MinerU
- ✅ **Question Extraction** - Identifies and extracts reference questions from exams
- ✅ **Style Mimicking** - Generates similar questions based on reference structure
- ✅ **Batch Organization** - All outputs saved to timestamped folders

### Common Features
- ✅ **Unified BaseAgent** - All agents inherit from `src/agents/base_agent.py`
- ✅ **No Iteration Loops** - Single-pass generation + analysis
- ✅ **Bilingual Prompts** - Supports both Chinese and English via YAML
- ✅ **Real-time WebSocket Streaming** - Live progress updates to frontend

## System Architecture

### Modular Agent Architecture

```
User Requirement
    ↓
┌─────────────────────────────────────────────────┐
│ AgentCoordinator                                │
│                                                 │
│  1. RetrieveAgent                               │
│     ├── Generate RAG queries (LLM)              │
│     └── Execute RAG searches (parallel)         │
│                                                 │
│  2. Plan Generation (in coordinator)            │
│     └── Create focuses for each question        │
│                                                 │
│  3. GenerateAgent (per question)                │
│     └── Generate question from knowledge+focus  │
│                                                 │
│  4. RelevanceAnalyzer (per question)            │
│     └── Analyze KB relevance (high/partial)     │
│                                                 │
└─────────────────────────────────────────────────┘
    ↓
Save Results:
  - knowledge.json (queries + retrievals)
  - plan.json (focuses)
  - q_1/result.json, q_1/question.md
  - q_2/result.json, q_2/question.md
  - summary.json
```

### Mimic Mode Architecture

```
PDF Upload / Parsed Directory
    ↓
Parse PDF with MinerU (tools/pdf_parser.py)
    ↓
Extract Reference Questions (tools/question_extractor.py)
    ↓
For each reference question (parallel):
    AgentCoordinator.generate_question(with_reference=True)
    ├── RetrieveAgent
    ├── GenerateAgent (with reference)
    └── RelevanceAnalyzer
    ↓
Save to timestamped folder
```

## Core Components

### 1. RetrieveAgent

Located in `agents/retrieve_agent.py`. Inherits from `src/agents/base_agent.py`.

**Responsibilities:**
- Generate semantic search queries from requirements
- Execute RAG searches in parallel
- Merge and summarize retrieval results

```python
retrieve_agent = RetrieveAgent(kb_name="math2211", language="en")
result = await retrieve_agent.process(requirement, num_queries=3)
# Returns: {"queries": [...], "retrievals": [...], "summary": "...", "has_content": True}
```

### 2. GenerateAgent

Located in `agents/generate_agent.py`. Generates questions based on knowledge context.

**Responsibilities:**
- Generate custom questions from requirements + knowledge
- Generate mimic questions from reference + knowledge
- Output structured question JSON

```python
generate_agent = GenerateAgent(language="en")
result = await generate_agent.process(
    requirement={"knowledge_point": "...", "difficulty": "medium"},
    knowledge_context="...",
    focus={"focus": "...", "type": "written"},
    reference_question=None  # or "reference text" for mimic mode
)
# Returns: {"success": True, "question": {...}}
```

### 3. RelevanceAnalyzer

Located in `agents/relevance_analyzer.py`. Replaces old validation workflow.

**Key difference from old ValidationWorkflow:**
- **NO rejection**: all questions are accepted
- **NO iteration**: single-pass analysis
- Output: relevance level (high/partial) with explanations

```python
analyzer = RelevanceAnalyzer(language="en")
result = await analyzer.process(question={"question": "..."}, knowledge_context="...")
# Returns: {"relevance": "high", "kb_coverage": "...", "extension_points": ""}
```

### 4. AgentCoordinator

Located in `coordinator.py`. Orchestrates the workflow using specialized agents.

**Methods:**
- `generate_question()`: Single question generation (used by Mimic mode)
- `generate_questions_custom()`: Batch generation from requirement

## Usage

### Custom Mode - Batch Generation

```python
import asyncio
from src.agents.question import AgentCoordinator

async def main():
    coordinator = AgentCoordinator(
        kb_name="math2211",
        output_dir="data/user/question",
        language="en"
    )

    result = await coordinator.generate_questions_custom(
        requirement={
            "knowledge_point": "Multivariable limits",
            "difficulty": "medium",
            "question_type": "choice"
        },
        num_questions=3
    )

    print(f"✅ Generated {result['completed']}/{result['requested']} questions")
    for r in result['results']:
        print(f"- [{r['analysis']['relevance']}] {r['question']['question'][:50]}...")

asyncio.run(main())
```

### Custom Mode - Single Question

```python
requirement = {
    "knowledge_point": "Limits and continuity",
    "difficulty": "medium",
    "question_type": "choice"
}

result = await coordinator.generate_question(requirement)

if result["success"]:
    print(f"Question: {result['question']['question']}")
    print(f"Relevance: {result['validation']['relevance']}")
    print(f"KB Coverage: {result['validation']['kb_coverage']}")
```

### Mimic Mode - PDF Upload

```python
from src.tools.question import mimic_exam_questions

result = await mimic_exam_questions(
    pdf_path="exams/midterm.pdf",
    kb_name="math2211",
    output_dir="data/user/question/mimic_papers",
    max_questions=5
)

print(f"✅ Generated {result['successful_generations']} questions")
```

### Mimic Mode - Parsed Directory

```python
result = await mimic_exam_questions(
    paper_dir="data/parsed_exams/exam_20240101",
    kb_name="math2211"
)
```

## Configuration

### `config/main.yaml`

```yaml
question:
  # Refactored: no iteration loops (max_rounds removed)
  rag_query_count: 3
  max_parallel_questions: 1
  rag_mode: naive
  agents:
    retrieve:
      top_k: 30
    generate:
      max_retries: 2
    relevance_analyzer:
      enabled: true
```

### `config/agents.yaml`

```yaml
question:
  temperature: 0.7
  max_tokens: 4000
```

## Return Format

### Single Question Result

```python
{
    "success": True,
    "question": {
        "question_type": "choice",
        "question": "Question content",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "correct_answer": "A",
        "explanation": "Detailed explanation",
        "knowledge_point": "Topic name"
    },
    "validation": {
        "decision": "approve",  # Always approve
        "relevance": "high",    # or "partial"
        "kb_coverage": "This question tests...",
        "extension_points": ""  # Only if relevance is "partial"
    },
    "rounds": 1  # Always 1 (no iteration)
}
```

### Batch Generation Result

```python
{
    "success": True,
    "requested": 3,
    "completed": 3,
    "failed": 0,
    "search_queries": ["query1", "query2", "query3"],
    "plan": {"focuses": [...]},
    "results": [
        {
            "question_id": "q_1",
            "focus": {"focus": "...", "type": "written"},
            "question": {...},
            "analysis": {"relevance": "high", "kb_coverage": "..."}
        },
        ...
    ],
    "failures": []
}
```

## Output Files

### Custom Mode Directory Structure

```
data/user/question/batch_YYYYMMDD_HHMMSS/
├── knowledge.json       # RAG queries and retrievals
├── plan.json            # Question focuses
├── q_1/
│   ├── result.json      # Question + analysis
│   └── question.md      # Human-readable format
├── q_2/
│   ├── result.json
│   └── question.md
└── summary.json         # Overall summary
```

### Mimic Mode Directory Structure

```
data/user/question/mimic_papers/{paper_name}/
├── auto/{paper_name}.md                              # MinerU parsed markdown
├── {paper_name}_YYYYMMDD_HHMMSS_questions.json       # Extracted reference questions
└── {paper_name}_YYYYMMDD_HHMMSS_generated.json       # Generated questions
```

## Key Changes from Previous Version

### ✅ Architecture Changes

1. **Unified BaseAgent**
   - All agents now inherit from `src/agents/base_agent.py`
   - Automatic LLM config, prompt loading, token tracking
   - No more separate ReAct base class

2. **Specialized Agents**
   - `RetrieveAgent`: Knowledge retrieval only
   - `GenerateAgent`: Question generation only
   - `RelevanceAnalyzer`: Relevance analysis only (replaces ValidationWorkflow)

3. **No Iteration/Rejection**
   - Removed `max_rounds` from config
   - Single-pass generation + analysis
   - All questions accepted with relevance classification

4. **Tools Moved**
   - `src/agents/question/tools/` → `src/tools/question/`
   - Import via `from src.tools.question import ...`

### ❌ Removed

1. **Old ReAct Architecture**
   - `agents/base_agent.py` (ReAct paradigm)
   - `agents/generation_agent.py` (ReAct-based)
   - `agents/validation_agent.py` (deprecated)
   - `validation_workflow.py` (replaced by RelevanceAnalyzer)

2. **Iteration Logic**
   - No more validation loops
   - No more task rejection
   - No more request_modification/request_regeneration

3. **Message Queue**
   - Agent communication simplified
   - Direct method calls instead of message passing

## Migration Notes

**Import Path Updates:**

```python
# Old
from src.agents.question import BaseAgent, QuestionGenerationAgent
from src.tools.question import mimic_exam_questions

# New
from src.agents.question import RetrieveAgent, GenerateAgent, RelevanceAnalyzer
from src.tools.question import mimic_exam_questions
```

**API Changes:**

```python
# Old - with rejection handling
result = await coordinator.generate_question(requirement)
if result.get("error") == "task_rejected":
    print("Agent rejected task")

# New - always generates, check relevance
result = await coordinator.generate_question(requirement)
if result["success"]:
    if result["validation"]["relevance"] == "high":
        print("Fully covered by KB:", result["validation"]["kb_coverage"])
    else:
        print("Extension question:", result["validation"]["extension_points"])
```
