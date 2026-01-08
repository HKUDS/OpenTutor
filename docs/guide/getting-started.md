# 🚀 Quick Start

## Step 1: Clone Repository and Set Up Environment

```bash
# Clone the repository
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Set Up Virtual Environment (Choose One Option)

# Option A: Using conda (Recommended)
conda create -n aitutor python=3.10
conda activate aitutor

# Option B: Using venv
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

## Step 2: Install Dependencies

Run the automated installation script to install all required dependencies:

```bash
# Recommended: Automated Installation
bash scripts/install_all.sh

# Alternative: Manual Installation
python scripts/install_all.py

# Or Install Dependencies Manually
pip install -r requirements.txt
npm install

# Verify Python environment
pip install -e .[dev]
pip check
pytest -q
```

## Step 3: Set Up Environment Variables

Create a `.env` file in the project root directory based on `.env.example`:

```bash
# Copy from .env.example template (if exists)
cp .env.example .env

# Then edit .env file with your API keys
```

## Step 4: Configure Ports and LLM Settings *(Optional)*

By default, the application uses:
- **Backend (FastAPI)**: `8001`
- **Frontend (Next.js)**: `3782`

You can modify these ports in `config/main.yaml` by editing the `server.backend_port` and `server.frontend_port` values.

**LLM Configuration**: Agent settings for `temperature` and `max_tokens` are centralized in `config/agents.yaml`. Each module (guide, solve, research, question, ideagen, co_writer) has customizable parameters. See [Configuration](/guide/configuration) for details.

## Step 5: Try Our Demos *(Optional)*

Experience the system quickly with two pre-built knowledge bases and a collection of challenging questions with usage examples.

<details>
<summary><b>Research Papers Collection</b> — 5 papers (20-50 pages each)</summary>

A curated collection of 5 research papers from our lab covering RAG and Agent fields. This demo showcases broad knowledge coverage for research scenarios.

**Used Papers**: [AI-Researcher](https://github.com/HKUDS/AI-Researcher) | [AutoAgent](https://github.com/HKUDS/AutoAgent) | [RAG-Anything](https://github.com/HKUDS/RAG-Anything) | [LightRAG](https://github.com/HKUDS/LightRAG) | [VideoRAG](https://github.com/HKUDS/VideoRAG)

</details>

<details>
<summary><b>Data Science Textbook</b> — 8 chapters, 296 pages</summary>

A comprehensive data science textbook with challenging content. This demo showcases **deep knowledge depth** for learning scenarios.

**Book Link**: [Deep Representation Learning Book](https://ma-lab-berkeley.github.io/deep-representation-learning-book/)
</details>

**Download and Setup:**

1. Download the demo package: [Google Drive](https://drive.google.com/drive/folders/1iWwfZXiTuQKQqUYb5fGDZjLCeTUP6DA6?usp=sharing)
2. Extract the compressed files directly into the `data/` directory
3. Knowledge bases will be automatically available once you start the system

> **Note:** Our **demo knowledge bases** use `text-embedding-3-large` with `dimensions = 3072`. Ensure your embeddings model has matching dimensions (3072) for compatibility.

## Step 6: Launch the Application

```bash
# Activate virtual environment
conda activate aitutor  # or: source venv/bin/activate

# Start web interface (frontend + backend)
python scripts/start_web.py

# Alternative: CLI interface only
python scripts/start.py

# Stop the service: Ctrl+C
```

## Step 7: Create Your Own Knowledge Base

Create custom knowledge bases through the web interface with support for multiple file formats.

1. **Access Knowledge Base**: Navigate to `http://localhost:3782/knowledge`
2. **Create New Base**: Click "New Knowledge Base"
3. **Configure Settings**: Enter a unique name for your knowledge base
4. **Upload Content**: Add single or multiple files for batch processing
5. **Monitor Progress**: Track processing status in the terminal running `start_web.py`
   - Large files may take several minutes to complete
   - Knowledge base becomes available once processing finishes

> **Tips:** Large files may require several minutes to process. Multiple files can be uploaded simultaneously for efficient batch processing.

## Access URLs

| Service | URL | Description |
|:---:|:---|:---|
| **Frontend** | `http://localhost:3782` | Main web interface |
| **API Docs** | `http://localhost:8001/docs` | Interactive API documentation |
| **Health** | `http://localhost:8001/api/v1/knowledge/health` | System health check |

## Next Steps

- [Configuration](/guide/configuration) — Customize your setup
- [Features Overview](/features/overview) — Explore all features
- [Troubleshooting](/guide/troubleshooting) — Common issues and solutions
