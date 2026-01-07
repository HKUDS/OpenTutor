# Solve Agents - Dual-Loop Problem Solving System

<div align="center">

**Intelligent Problem Solving System Based on Dual-Loop Architecture**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [Core Modules](#core-modules)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Development Guide](#development-guide)

---

## System Overview

This system is an intelligent problem-solving system based on a **dual-loop architecture**, achieving a complete workflow from problem understanding to answer generation through two collaborative loops.

### Dual-Loop Architecture

| Loop | Function | Key Features |
|------|----------|--------------|
| **Analysis Loop** | Deep understanding of user questions | Dynamic research, iterative knowledge collection, automatic stopping |
| **Solve Loop** | Strict solving and answer generation | Block planning, step-by-step execution, quality checking |

### Core Advantages

✅ **Intelligent Research** - Analysis Loop dynamically determines when to stop research  
✅ **Block-based Solving** - Solve Loop decomposes complex problems into manageable blocks  
✅ **Quality Assurance** - Check Agent automatically checks and corrects errors  
✅ **Persistent Memory** - JSON format storage, supports checkpoint resumption  
✅ **Citation Management** - Automatic citation management and formatting  
✅ **Tool Integration** - RAG, Web Search, Code Execution  

---

## Quick Start

### Install Dependencies & Configure Environment

```bash
pip install -r requirements.txt

# .env file (project root directory)
LLM_BINDING_API_KEY=your_api_key
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4o         # Optional
PERPLEXITY_API_KEY=...   # Optional, enable Web search
```

### Basic Usage (Python API)

```python
import asyncio
import os
from solve_agents import MainSolver

async def main():
    solver = MainSolver(
        kb_name="ai_textbook",
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        base_url=os.getenv("LLM_BINDING_HOST"),
    )

    result = await solver.solve(
        question="What is linear convolution?",
        verbose=True
    )

    print(f"📁 Output directory: {result['metadata']['output_dir']}")
    print(f"📊 Analysis iterations: {result['analysis_iterations']} rounds")
    print(f"📊 Solve steps: {result['solve_steps']} steps")
    print(f"📝 Markdown: {result['output_md']}")

asyncio.run(main())
```

### Using Command Line Tool

```bash
cd DeepTutor/student_TA
python start.py  # CLI currently defaults to dual-loop Solve mode
```

---

## System Architecture

### Overall Flow

```
User Question
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                      MainSolver                              │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Analysis Loop (Analysis Loop)                │  │
│  │                                                         │  │
│  │  ┌──────────┐    ┌──────────┐                           │  │
│  │  │Investigate│ -> │   Note   │                           │  │
│  │  └──────────┘    └──────────┘                           │  │
│  │        ▲             │                                 │  │
│  │        └─────────────┴───────────────┐                 │  │
│  │                                      │                 │  │
│  │                          Stop condition met            │  │
│  │                                      │                 │  │
│  │                            InvestigateMemory           │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            Solve Loop (Solving Loop)                   │  │
│  │                                                         │  │
│  │  ┌──────┐    ┌─────────┐    ┌──────┐    ┌───────┐   │  │
│  │  │ Plan │ -> │ Manager │ -> │Solve │ -> │ Check │   │  │
│  │  └──────┘    └─────────┘    └──────┘    └───────┘   │  │
│  │                                   │           │        │  │
│  │                                   └───────────┘        │  │
│  │                          Loop until completion          │  │
│  │                                       │                │  │
│  │                                       ▼                │  │
│  │                                  ┌────────┐           │  │
│  │                                  │ Format │           │  │
│  │                                  └────────┘           │  │
│  │                                       │                │  │
│  │                                  SolveMemory          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│                          Final Answer                         │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
solve_agents/
├── main_solver.py              # Main controller
├── base_agent.py               # Agent base class
├── config.yaml                 # Configuration file
│
├── analysis_loop/              # Analysis Loop ⭐
│   ├── investigate_agent.py    # Research Agent
│   ├── note_agent.py           # Note Agent
│   └── README.md               # Detailed documentation
│
├── solve_loop/                 # Solve Loop ⭐
│   ├── plan_agent.py           # Planning Agent
│   ├── manager_agent.py        # Manager Agent
│   ├── solve_agent.py          # Solving Agent
│   ├── tool_agent.py           # Tool execution Agent
│   ├── response_agent.py       # Aggregate tool results
│   ├── check_agent.py          # Quality checking
│   ├── precision_answer_agent.py  # Precision answer (optional)
│   ├── citation_manager.py     # Citation manager
│   └── README.md               # Detailed documentation
│
├── memory/                     # Memory system ⭐
│   ├── investigate_memory.py   # Analysis Loop memory
│   └── solve_memory.py         # Solve Loop memory
│
├── utils/                      # Utility modules
│   ├── logger.py               # Logging system
│   ├── performance_monitor.py  # Performance monitoring
│   ├── config_validator.py     # Configuration validation
│   ├── json_utils.py           # JSON utilities
│   ├── tag_parser.py           # Tag parser
│   └── error_handler.py        # Error handling
│
└── prompts/                    # Prompt templates
    ├── analysis_loop/          # Analysis Loop Prompts
    └── solve_loop/             # Solve Loop Prompts
```

---

## Core Modules

### Analysis Loop (Analysis Loop)

**Function**: Deep understanding of user questions

**Agents**:
- **InvestigateAgent**: Based on knowledge chain, outputs multiple queries at once and calls tools, generates `cite_id → raw_result`
- **NoteAgent**: Processes new `cite_id` one by one, generates summary and citations

**Memory**: `InvestigateMemory` (JSON)

**Detailed Documentation**: [analysis_loop/README.md](analysis_loop/README.md)

### Solve Loop (Solving Loop)

**Function**: Strict solving and answer generation

**Agents**:
- **PlanAgent**: Generates problem-solving plan (blocks)
- **ManagerAgent**: Arranges specific steps (steps) for each block
- **SolveAgent**: Calls tools and writes reasoning according to steps
- **ToolAgent**: Unified encapsulation of RAG / Web Search / Code Execution / Query Item tools
- **ResponseAgent**: Organizes outputs from SolveAgent and ToolAgent
- **CheckAgent**: Automatically checks steps and provides correction suggestions
- **PrecisionAnswerAgent**: Generates precision answer summary (optional)

**Memory**: `SolveMemory` (JSON)

**Detailed Documentation**: [solve_loop/README.md](solve_loop/README.md)

### Memory System

**InvestigateMemory**:
```python
{
    "user_question": "...",
    "knowledge_chain": [...],  # Collected knowledge
    "reflections": {...},      # Reserved field, currently only records remaining questions (default empty)
    "metadata": {...}          # Statistics
}
```

**SolveMemory**:
```python
{
    "user_question": "...",
    "plan": {
        "blocks": [...]  # Problem-solving plan
    },
    "progress": {...},   # Execution progress
    "metadata": {...}    # Statistics
}
```

### Tool System

ToolAgent aggregates multiple capabilities and automatically chains them step by step:

- **RAG Search**: Retrieves KBs from `knowledge_bases/`
- **Web Search**: Expands latest materials based on Perplexity API
- **Query Item**: Quickly references formulas / theorems by number
- **Code Execution**: Runs Python in sandbox, results written to `artifacts/`

---

## Configuration

### config.yaml Structure

```yaml
system:
  output_base_dir: "./user/solve"
  save_intermediate_results: true
  output_language: "English"          # or Chinese
  max_analysis_iterations: 5
  max_solve_correction_iterations: 3

logging:
  level: "INFO"
  save_to_file: true
  console_output: true
  log_dir: "./logs"

monitoring:
  enabled: true
  track_token_usage: true
  track_time: true
  save_dir: "./logs/performance"

llm:
  max_retries: 3
  timeout: 120
  max_tokens: 8192

agents:
  investigate_agent:
    temperature: 0.4
    max_iterations: 3
  note_agent:
    max_tokens: 4096

  manager_agent: {}
  solve_agent:
    max_tokens: 8192
  tool_agent: {}
  response_agent:
    max_tokens: 8192
    enabled: false
    max_tokens: 8192
  precision_answer_agent:
    enabled: true
    temperature: 0.2

tools:
  rag_tool:
    kb_base_dir: "./knowledge_bases"
    default_kb: "ai_textbook"
  web_search:
    enabled: true
    max_results: 5
  query_item:
    enabled: true
  run_code:
    enabled: true
    timeout: 10
    workspace: "./student_TA/cache/run_code_workspace"
```

---

## Usage Guide

### Basic Usage

```python
from solve_agents import MainSolver

# Create solver
solver = MainSolver(
    kb_name="ai_textbook",  # Knowledge base name
    config_path=None,       # Use default configuration
    api_key=None,           # Read from environment variables
    base_url=None           # Read from environment variables
)

# Solve problem
result = await solver.solve(
    question="Your question",
    verbose=True  # Print detailed logs
)

# View results
print(result['output_md'])       # final_answer.md
print(result['output_json'])     # solve_chain.json (steps + tool logs)
print(result['final_answer'])    # String, may contain precision answer
print(len(result['citations']))  # Number of citations
```

### Output Files

```
user/solve/solve_20251116_160009/
├── investigate_memory.json    # Analysis Loop memory
├── solve_chain.json           # Solve Loop steps & tool records ⭐
├── citation_memory.json       # Citation management
├── final_answer.md            # Final answer (Markdown)
├── performance_report.json    # Performance monitoring
├── cost_report.json           # Optional: token cost
├── search_*.json              # Search cache (if any)
└── artifacts/                 # Code execution output
```

### View Statistics

```python
result = await solver.solve(question)

# Analysis Loop statistics
print(f"Analysis iterations: {result['analysis_iterations']} rounds")
print(f"Coverage rate: {result['metadata']['coverage_rate']:.2%}")
print(f"Average confidence: {result['metadata']['avg_confidence']:.2%}")

# Solve Loop statistics
print(f"Solve completed steps: {result['solve_steps']} / {result['metadata']['total_steps']}")
print(f"Number of citations: {len(result['citations'])}")
```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# View memory files
import json
output_dir = result['metadata']['output_dir']
with open(f'{output_dir}/investigate_memory.json', encoding='utf-8') as f:
    memory = json.load(f)
print(json.dumps(memory, indent=2, ensure_ascii=False))
```

---

## Development Guide

### Extending New Agent

1. **Inherit BaseAgent**:

```python
from solve_agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, config, api_key, base_url):
        super().__init__(config, api_key, base_url, 'my_agent')

    async def process(self, **kwargs):
        # Implement processing logic
        # Prompts are auto-loaded via unified PromptManager
        system_prompt = self.get_prompt("system")
        response = await self.call_llm(user_prompt, system_prompt)
        return self.parse_response(response)
```

2. **Add Prompt**:

Define Prompt in `prompts/analysis_loop/my_agent.yaml` or `prompts/solve_loop/my_agent.yaml`.

3. **Register to MainSolver**:

Initialize in the `_init_agents()` method of `main_solver.py`.

4. **Add Configuration**:

Add Agent configuration in `config.yaml`.

### Extending Memory System

```python
from dataclasses import dataclass, asdict
import json

@dataclass
class MyMemory:
    user_question: str
    data: dict

    def save(self, output_dir: str):
        with open(f"{output_dir}/my_memory.json", 'w') as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_or_create(cls, output_dir: str, user_question: str):
        path = f"{output_dir}/my_memory.json"
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                return cls(**data)
        return cls(user_question=user_question, data={})
```

### Adding New Tool

```python
# Create new tool in tools/ directory
class MyTool:
    def __init__(self, config):
        self.config = config

    async def execute(self, **kwargs):
        # Implement tool logic
        return result

# Register in SolveAgent
self.tools['my_tool'] = MyTool(config)
```

---

## Performance Optimization

### Adjust Iteration Count

```yaml
system:
  max_analysis_iterations: 3  # Reduce Analysis iterations
  max_solve_correction_iterations: 2  # Reduce Solve retries
```

### Use Faster Model

```yaml
agents:
  investigate_agent:
    model: "gpt-3.5-turbo"  # Use faster model
```

### Disable Optional Features

```yaml
agents:
  precision_answer_agent:
    enabled: false  # Disable precision answer
```

---

## FAQ

**Q: How to adjust the iteration count of Analysis Loop?**

Set `system.max_analysis_iterations` in `config.yaml`.

**Q: How to enable precision answer feature?**

Set `agents.precision_answer_agent.enabled: true` in `config.yaml`.

**Q: How to view detailed execution logs?**

Set `logging.level: "DEBUG"` or enable `verbose=True` in code.

**Q: Where are the memory files?**

In the `{output_base_dir}/solve_{timestamp}/` directory.

**Q: How to reset citation numbers?**

```python
from solve_agents.solve_loop.citation_manager import CitationManager
CitationManager().reset()
```

**Q: What to do if code execution times out?**

Adjust the `agents.code_agent.timeout` configuration.

---

## Version History

- **v3.0** (2025-11-16) - Dual-loop architecture refactoring
  - ✅ Complete refactoring to dual-loop architecture
  - ✅ Remove old Router, Deep Analysis, Deep Solve modules
  - ✅ Introduce dynamic memory system
  - ✅ Optimize tool calling and citation management
  - ✅ Simplify configuration and usage flow
  - ✅ Merge utils and parsers modules

---

## Related Documentation

- [Analysis Loop Detailed Documentation](analysis_loop/README.md)
- [Solve Loop Detailed Documentation](solve_loop/README.md)
- [Configuration File Documentation](config.yaml)
---

## License

MIT License

---

**Made with ❤️ by DeepTutor Team**
