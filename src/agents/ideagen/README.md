# Idea Generation Module

The Idea Generation module extracts knowledge points from notebook records and generates research ideas through a multi-stage filtering and exploration workflow.

## 📋 Overview

The Idea Generation module helps users discover research opportunities by:
1. Extracting knowledge points from notebook records
2. Filtering and exploring knowledge points
3. Generating research ideas for each knowledge point
4. Strictly filtering ideas to identify the most valuable ones
5. Organizing final ideas into structured markdown output

## 🏗️ Architecture

```
ideagen/
├── __init__.py
├── base_idea_agent.py              # Base agent class with unified LLM interface
├── material_organizer_agent.py      # Extracts knowledge points from notebook records
├── idea_generation_workflow.py     # Main workflow orchestrator
├── prompts/                        # Bilingual prompts (YAML)
│   ├── zh/                         # Chinese prompts
│   │   ├── material_organizer.yaml
│   │   └── idea_generation.yaml
│   └── en/                         # English prompts
│       ├── material_organizer.yaml
│       └── idea_generation.yaml
└── README.md
```

## 🔧 Components

### BaseIdeaAgent

**Purpose**: Base class providing unified LLM call interface and base functionality

**Features**:
- Unified LLM configuration loading
- Shared statistics tracking
- Common logging setup

**Methods**:
```python
async def call_llm(
    user_prompt: str,
    system_prompt: str,
    response_format: Optional[Dict[str, str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str
```

### MaterialOrganizerAgent

**Purpose**: Extracts knowledge points from notebook records

**Features**:
- Analyzes notebook records (solve, question, research, co-writer)
- Extracts core knowledge points
- Provides descriptions for each knowledge point

**Methods**:
```python
async def process(
    records: List[Dict[str, Any]],
    user_thoughts: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Returns**:
```python
[
    {
        "knowledge_point": str,      # Knowledge point name
        "description": str            # Description from system response
    },
    ...
]
```

### IdeaGenerationWorkflow

**Purpose**: Main workflow orchestrator for idea generation

**Workflow Stages**:

1. **Loose Filter** (`loose_filter`)
   - Filters knowledge points with loose criteria
   - Removes obviously unsuitable points
   - Returns filtered knowledge point list

2. **Explore Ideas** (`explore_ideas`)
   - Generates at least 5 research ideas for each knowledge point
   - Encourages innovative thinking from multiple dimensions
   - Returns list of research ideas

3. **Strict Filter** (`strict_filter`)
   - Strictly evaluates research ideas
   - Must keep at least 1, must eliminate at least 2
   - Returns filtered research ideas

4. **Generate Markdown** (`generate_markdown`)
   - Organizes final ideas into structured markdown
   - Includes knowledge points, ideas, and descriptions

**Methods**:
```python
async def loose_filter(
    knowledge_points: List[Dict[str, Any]]
) -> List[Dict[str, Any]]

async def explore_ideas(
    knowledge_point: Dict[str, Any]
) -> List[str]

async def strict_filter(
    knowledge_point: Dict[str, Any],
    research_ideas: List[str]
) -> List[str]

async def generate_markdown(
    knowledge_points: List[Dict[str, Any]],
    ideas_map: Dict[str, List[str]]
) -> str
```

## 📊 Workflow

```
Notebook Records
    ↓
MaterialOrganizerAgent → Extract Knowledge Points
    ↓
IdeaGenerationWorkflow.loose_filter → Filter Knowledge Points
    ↓
IdeaGenerationWorkflow.explore_ideas → Generate Research Ideas (≥5 per point)
    ↓
IdeaGenerationWorkflow.strict_filter → Strictly Filter Ideas (keep ≥1, eliminate ≥2)
    ↓
IdeaGenerationWorkflow.generate_markdown → Generate Final Markdown
```

## 🔌 API Integration

The Idea Generation module is exposed via FastAPI routes in `src/api/routers/ideagen.py`:

### Endpoints

- `POST /api/v1/ideagen/generate` - Generate research ideas from notebook records

### Request Format

```json
{
  "notebook_id": "notebook_123",
  "user_thoughts": "Optional user thoughts and preferences"
}
```

### Response Format

```json
{
  "success": true,
  "markdown": "# Generated markdown content...",
  "knowledge_points": [...],
  "ideas_map": {...}
}
```

## 📝 Usage Example

```python
from src.agents.ideagen.material_organizer_agent import MaterialOrganizerAgent
from src.agents.ideagen.idea_generation_workflow import IdeaGenerationWorkflow

# 1. Extract knowledge points
organizer = MaterialOrganizerAgent()
records = [...]  # Notebook records
knowledge_points = await organizer.process(records, user_thoughts="Focus on ML")

# 2. Generate ideas
workflow = IdeaGenerationWorkflow(
    progress_callback=print  # Optional progress callback
)

# Loose filter
filtered_points = await workflow.loose_filter(knowledge_points)

# Explore ideas for each point
ideas_map = {}
for point in filtered_points:
    ideas = await workflow.explore_ideas(point)
    filtered_ideas = await workflow.strict_filter(point, ideas)
    ideas_map[point["knowledge_point"]] = filtered_ideas

# Generate markdown
markdown = await workflow.generate_markdown(filtered_points, ideas_map)
```

## ⚙️ Configuration

### LLM Configuration

Required environment variables (same as other modules):

```bash
LLM_API_KEY=your_api_key
LLM_HOST=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

### Progress Callback

The workflow supports progress callbacks for streaming output:

```python
async def progress_callback(stage: str, data: Any):
    print(f"Stage: {stage}, Data: {data}")

workflow = IdeaGenerationWorkflow(progress_callback=progress_callback)
```

## 📊 Statistics Tracking

The module tracks LLM usage statistics:

```python
from src.agents.ideagen.base_idea_agent import BaseIdeaAgent

# Print statistics
BaseIdeaAgent.print_stats()
```

## 🔗 Related Modules

- **API Routes**: `src/api/routers/ideagen.py` - REST API endpoints
- **Notebook**: `src/api/utils/notebook_manager.py` - Notebook record management
- **Core Config**: `src/core/core.py` - Configuration management

## 🛠️ Development

### Adding New Filtering Stages

To add a new filtering stage:

1. Add a new method to `IdeaGenerationWorkflow`
2. Update the workflow sequence
3. Add progress callback support

### Customizing Idea Generation

Prompts are now stored in YAML files under `prompts/` directory:

```yaml
# prompts/en/idea_generation.yaml
explore_ideas_system: |
  You are a research idea generation expert...

explore_ideas_user_template: |
  Based on the following knowledge point, generate at least 5 feasible research ideas:
  Knowledge Point: {knowledge_point}
  ...
```

To customize:
- Edit YAML files in `prompts/en/` or `prompts/zh/`
- Modify number of ideas, generation criteria, innovation dimensions
- Add new prompts for custom stages

## ⚠️ Notes

1. **Minimum Ideas**: Each knowledge point must generate at least 5 ideas
2. **Strict Filtering**: Must keep at least 1 idea, eliminate at least 2
3. **Progress Tracking**: Use progress callbacks for real-time updates
4. **Output Directory**: Intermediate results can be saved if `output_dir` is provided

## 📈 Output Format

The final markdown output includes:

```markdown
# Research Ideas

## Knowledge Point 1
Description: ...

### Research Ideas
1. Idea 1...
2. Idea 2...

## Knowledge Point 2
...
```
