# Question Generation System

Intelligent question generation system with **dual-mode architecture** supporting both knowledge base-driven custom generation and reference exam paper mimicking.

## 📁 Directory Structure

```
question/
├── __init__.py                    # Module exports
├── agents/                        # Agent classes
│   ├── __init__.py
│   ├── base_agent.py             # Base agent class (ReAct paradigm)
│   ├── generation_agent.py       # Question generation agent
│   └── validation_agent.py       # Question validation agent (deprecated)
├── tools/                         # Tools and utilities
│   ├── __init__.py
│   ├── pdf_parser.py             # PDF parsing with MinerU
│   ├── question_extractor.py     # Extract questions from exams
│   └── exam_mimic.py             # Reference-based question generation
├── prompts/                       # Bilingual prompts (YAML)
│   ├── zh/                       # Chinese prompts
│   │   ├── generation_agent.yaml
│   │   ├── validation_workflow.yaml
│   │   └── coordinator.yaml
│   └── en/                       # English prompts
│       └── (same structure)
├── coordinator.py                # Agent coordinator
├── validation_workflow.py        # Validation workflow
├── example.py                    # Usage examples
└── README.md
```

## 🚀 Core Features

### Custom Mode (Knowledge Base-Driven)
- ✅ **Intelligent Search Query Generation** - Generates configurable number of RAG queries (from `config/main.yaml`)
- ✅ **Background Knowledge Acquisition** - Retrieves relevant knowledge using naive mode RAG
- ✅ **Question Planning** - Creates comprehensive plan with question IDs, focuses, and types
- ✅ **Single-Pass Validation** - Analyzes question relevance without iterative refinement
- ✅ **Complete File Persistence** - Saves background knowledge, plan, and individual results

### Mimic Mode (Reference Exam-Based)
- ✅ **PDF Parsing** - Automatic PDF extraction using MinerU
- ✅ **Question Extraction** - Identifies and extracts reference questions from exams
- ✅ **Style Mimicking** - Generates similar questions based on reference structure
- ✅ **Batch Organization** - All outputs saved to timestamped folders
- ✅ **Progress Tracking** - Real-time updates for parsing, extracting, and generating stages

### Common Features
- ✅ **Multimodal Content Support** - Correctly parses text, equations, images, and tables
- ✅ **Batch Question Generation** - Handles multiple questions in parallel
- ✅ **Bilingual Prompts** - Supports both Chinese and English prompts via YAML configuration
- ✅ **Real-time WebSocket Streaming** - Live progress updates to frontend

## System Architecture

### Custom Mode Architecture
```
User Requirement
    ↓
Generate RAG Queries (configurable count)
    ↓
Retrieve Background Knowledge (naive mode)
    ↓
Create Question Plan (IDs, focuses, types)
    ↓
For each question:
    GenerationAgent → ValidationWorkflow
    ↓                     ↓
  [retrieve]         [analyze_relevance]
  [generate]         (single-pass, no rejection)
    ↓
Save: background_knowledge.json
      question_plan.json
      question_X_result.json
```

### Mimic Mode Architecture
```
PDF Upload / Parsed Directory
    ↓
Parse PDF with MinerU
    ↓
Extract Reference Questions
    ↓
For each reference question (parallel):
    GenerationAgent → ValidationWorkflow
    ↓
Save to: mimic_YYYYMMDD_HHMMSS_{pdf_name}/
    ├── {pdf_name}.pdf
    ├── auto/{pdf_name}.md
    ├── {pdf_name}_questions.json
    └── {pdf_name}_generated_questions.json
```

## Core Components

### 1. BaseAgent (Base Agent Class)

Located in `agents/base_agent.py`. Implements ReAct loop: **Think → Act → Observe**

### 2. QuestionGenerationAgent

Located in `agents/generation_agent.py`. Generates questions based on knowledge base content or reference questions.

**Available Actions** (Custom Mode):
- `retrieve`: Retrieve relevant knowledge from knowledge base
- `generate_question`: Generate questions based on retrieved knowledge
- `refine_question`: Modify questions based on validation feedback
- `submit_question`: Submit question to validation workflow

**Key Changes**:
- ❌ Removed `reject_task` action - no longer rejects tasks
- ✅ Focuses on generation and refinement only

### 3. QuestionValidationWorkflow

Located in `validation_workflow.py`. Validates question quality using single-pass analysis.

**Custom Mode Workflow**:
- `retrieve` → `validate` → `analyze_relevance` → `return`

**Validation Output**:
- `decision`: "approve" (always, no rejection)
- `relevance`: "highly_relevant" | "partially_relevant"
- `kb_coverage`: Detailed analysis of knowledge base content tested
- `extension_points`: Explanation of extensions beyond KB (if applicable)
- `issues`: List of quality issues (if any)
- `suggestions`: Improvement suggestions (for refinement)

**Mimic Mode Workflow**:
- Similar structure, but validates against reference question style and knowledge base sufficiency

### 4. AgentCoordinator

Located in `coordinator.py`. Manages question generation workflows for both custom and mimic modes.

**Custom Mode Methods**:
- `generate_questions_custom()`: Full pipeline from requirement text to final questions
- `_generate_search_queries_from_text()`: Creates RAG queries (count from config)
- `_create_question_plan()`: Generates question plan based on requirements
- `generate_question()`: Single question generation with validation

**Mimic Mode**:
- Handled by `tools/exam_mimic.py` with coordinator for individual question generation

## Usage

### Custom Mode - Full Pipeline

```python
import asyncio
from src.agents.question import AgentCoordinator

async def main():
    # Create coordinator
    coordinator = AgentCoordinator(
        max_rounds=10,
        kb_name="math2211",
        output_dir="data/user/question"
    )

    # Full pipeline from text requirement
    result = await coordinator.generate_questions_custom(
        requirement_text="Generate 3 medium-difficulty questions about multivariable limits",
        difficulty="medium",
        question_type="choice",
        count=3
    )

    print(f"✅ Generated {result['completed']}/{result['requested']} questions")
    for q in result['results']:
        print(f"- {q['question']['question'][:50]}...")

asyncio.run(main())
```

### Custom Mode - Single Question

```python
# Define question requirement
requirement = {
    "knowledge_point": "Limits and continuity of multivariable functions",
    "difficulty": "medium",
    "question_type": "choice",
    "focus": "Test path-dependent limits at (0,0)"
}

# Generate single question
result = await coordinator.generate_question(requirement)

if result["success"]:
    print(f"✅ Generated in {result['rounds']} rounds")
    print(f"Question: {result['question']['question']}")
    print(f"Relevance: {result['validation']['relevance']}")
else:
    print(f"❌ Failed: {result['error']}")
```

### Mimic Mode - PDF Upload

```python
from src.agents.question.tools.exam_mimic import mimic_exam_questions

result = await mimic_exam_questions(
    pdf_path="exams/midterm.pdf",
    kb_name="math2211",
    output_dir="data/user/question/mimic_papers",
    max_questions=5
)

print(f"✅ Generated {result['successful_generations']} questions")
print(f"Output: {result['output_file']}")
```

### Mimic Mode - Parsed Directory

```python
# If you already have MinerU parsed results
result = await mimic_exam_questions(
    paper_dir="data/parsed_exams/exam_20240101",
    kb_name="math2211",
    max_questions=None  # Generate for all reference questions
)
```

## Prompts Configuration

Prompts are stored in YAML files under `prompts/` directory with bilingual support:

- `prompts/en/` - English prompts
- `prompts/zh/` - Chinese prompts

Each agent loads prompts based on the `language` parameter (default: "en").

### YAML Format Example

```yaml
system: |
  You are a professional Question Generation Agent...

generate: |
  Generate a question based on the following information:
  Requirements: {requirements}
  Retrieved knowledge: {knowledge}
  ...

refine: |
  Please modify the question based on validation feedback:
  ...
```

## Configuration

### Environment Variables

```bash
# LLM API Configuration
LLM_API_KEY=your_api_key_here
LLM_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### Configuration Files

**`config/main.yaml`** - RAG query count:
```yaml
question:
  rag_query_count: 3  # Number of RAG queries for background knowledge
```

**`config/agents.yaml`** - Agent parameters:
```yaml
question:
  temperature: 0.7
  max_tokens: 4000
```

## Tools

### PDF Parsing (`tools/pdf_parser.py`)

Uses MinerU for high-quality PDF extraction with formula and table support.

```python
from src.agents.question.tools import parse_pdf_with_mineru

# Parse PDF to markdown
success = await parse_pdf_with_mineru(
    pdf_path="/path/to/exam.pdf",
    output_base_dir="data/user/question/mimic_papers"
)
```

### Question Extraction (`tools/question_extractor.py`)

Extracts structured questions from parsed exam papers.

```python
from src.agents.question.tools import extract_questions_from_paper

questions = await extract_questions_from_paper(
    paper_dir="data/mimic_papers/exam_20241211",
    output_dir="data/mimic_papers"
)
# Returns: [{"question_number": "1", "question_text": "...", "images": []}, ...]
```

### Exam Mimicking (`tools/exam_mimic.py`)

Complete pipeline for reference-based question generation.

```python
from src.agents.question.tools import mimic_exam_questions

result = await mimic_exam_questions(
    pdf_path="exams/midterm.pdf",  # Or use paper_dir for parsed
    kb_name="math2211",
    output_dir="data/user/question/mimic_papers",
    max_questions=5,
    ws_callback=None  # Optional: async callback for progress updates
)
```

## Return Format

### Custom Mode - Single Question

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
        "decision": "approve",  # Always approve, no rejection
        "relevance": "highly_relevant",  # or "partially_relevant"
        "kb_coverage": "This question tests...",  # For highly relevant
        "extension_points": "This question extends...",  # For partially relevant
        "issues": [],  # Quality issues if any
        "suggestions": []  # Improvement suggestions
    },
    "rounds": 1  # Number of generation rounds (typically 1-2)
}
```

### Custom Mode - Batch Generation

```python
{
    "completed": 3,
    "requested": 3,
    "failed": 0,
    "results": [
        {
            "question": {...},
            "validation": {...},
            "rounds": 1
        },
        ...
    ]
}
```

### Mimic Mode - Output

```python
{
    "reference_paper": "exam_name",
    "kb_name": "math2211",
    "total_reference_questions": 5,
    "successful_generations": 5,
    "failed_generations": 0,
    "generated_questions": [
        {
            "success": True,
            "reference_question_number": "1",
            "reference_question_text": "Original question...",
            "generated_question": {...},
            "validation": {...},
            "rounds": 2
        },
        ...
    ],
    "output_file": "data/user/question/mimic_papers/mimic_20241211_120000_exam/..."
}
```

## Output Files

### Custom Mode Directory Structure

```
data/user/question/custom_YYYYMMDD_HHMMSS/
├── background_knowledge.json       # RAG retrieval results
│   {
│     "queries": ["query1", "query2", "query3"],
│     "knowledge": {
│       "query1": {"chunks": [...], "entities": [...], "relations": [...]},
│       ...
│     }
│   }
│
├── question_plan.json              # Question planning
│   {
│     "focuses": [
│       {"id": "q_1", "focus": "...", "type": "choice"},
│       {"id": "q_2", "focus": "...", "type": "written"},
│       ...
│     ]
│   }
│
├── question_1_result.json          # Individual question + validation
├── question_2_result.json
└── ...
```

### Mimic Mode Directory Structure

```
data/user/question/mimic_papers/
└── mimic_YYYYMMDD_HHMMSS_{pdf_name}/
    ├── {pdf_name}.pdf                                      # Original PDF
    ├── auto/{pdf_name}.md                                  # MinerU parsed markdown
    ├── {pdf_name}_YYYYMMDD_HHMMSS_questions.json          # Extracted reference questions
    │   {
    │     "total_questions": 4,
    │     "questions": [
    │       {"question_number": "1", "question_text": "...", "images": []},
    │       ...
    │     ]
    │   }
    │
    └── {pdf_name}_YYYYMMDD_HHMMSS_generated_questions.json # Generated questions
        {
          "reference_paper": "...",
          "kb_name": "...",
          "total_reference_questions": 4,
          "successful_generations": 4,
          "generated_questions": [
            {
              "reference_question_text": "...",
              "generated_question": {...},
              "validation": {...}
            },
            ...
          ]
        }
```

## Key Changes from Previous Version

### ✅ What's New

1. **Dual-Mode Architecture**
   - Custom mode: Knowledge base-driven generation
   - Mimic mode: Reference exam paper mimicking

2. **Simplified Validation**
   - Single-pass validation (no iterative refinement)
   - Always approves questions (no rejection)
   - Analyzes relevance: `highly_relevant` vs `partially_relevant`

3. **Enhanced File Persistence**
   - All intermediate files saved (background knowledge, plan)
   - Mimic mode: Timestamped batch folders
   - Complete traceability for debugging

4. **Configurable RAG Queries**
   - `rag_query_count` in `config/main.yaml`
   - Previously hardcoded to 3

5. **Real-time Progress Tracking**
   - WebSocket streaming for live updates
   - Mimic mode stages: uploading → parsing → extracting → generating

### ❌ What's Removed

1. **Task Rejection Logic**
   - Removed `reject_task` action from generation agent
   - Questions always proceed to validation
   - Validation analyzes relevance instead of rejecting

2. **Iterative Refinement**
   - No multi-round validation loop
   - Single-pass generation + validation
   - Reduces LLM calls and cost

3. **Standalone Validation Agent**
   - Merged into `ValidationWorkflow`
   - Simplified architecture

## Migration Notes

If upgrading from the old structure:

**File Structure Changes:**
- `base_agent.py` → `agents/base_agent.py`
- `question_generation_agent.py` → `agents/generation_agent.py`
- `question_validation_agent.py` → `agents/validation_agent.py` (deprecated)
- `question_tools/retrieve.py` → Removed (use RAG tool directly)
- `parse_pdf_with_mineru.py` → `tools/pdf_parser.py`
- `extract_questions_from_paper.py` → `tools/question_extractor.py`
- `mimic_exam_paper.py` → `tools/exam_mimic.py`
- `question_validation_workflow.py` → `validation_workflow.py`

**Import Path Updates:**
```python
# Old
from .base_agent import BaseAgent
from .question_tools import retrieve

# New
from .agents import BaseAgent
from src.tools import rag_search  # Use RAG tool directly
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
    relevance = result["validation"]["relevance"]
    if relevance == "highly_relevant":
        print(result["validation"]["kb_coverage"])
    else:
        print(result["validation"]["extension_points"])
```
