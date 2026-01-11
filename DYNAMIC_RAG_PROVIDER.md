# Dynamic RAG Provider Selection

## Overview

The knowledge base initialization has been refactored to support dynamic RAG provider selection based on the `RAG_PROVIDER` environment variable.

## Changes Made

### 1. Updated `src/knowledge/initializer.py`

**Previous Behavior:**
- Hardcoded to use `RAGAnything` directly
- Imported `raganything`, `RAGAnythingConfig`, `LightRAGLogContext`, `EmbeddingFunc`
- Manually configured LLM, vision, and embedding functions
- Directly instantiated `RAGAnything` class

**New Behavior:**
- Uses `RAGService` which respects `RAG_PROVIDER` environment variable
- Simplified imports - only imports `RAGService`
- Provider selection is automatic based on environment configuration
- Supports all registered RAG pipelines: `raganything`, `lightrag`, `llamaindex`, `academic`

### 2. Key Code Changes

#### Imports (Lines 26-33)
```python
# Before: Direct RAGAnything imports
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.utils import EmbeddingFunc

# After: RAGService import
from src.services.rag.service import RAGService
```

#### Process Documents Method (Lines 151-235)
```python
# Before: 200+ lines of RAGAnything configuration
config = RAGAnythingConfig(...)
rag = RAGAnything(config=config, llm_model_func=..., ...)
for doc in docs:
    await rag.process_document_complete(...)

# After: Simple RAGService usage
provider = os.getenv("RAG_PROVIDER", "raganything")
rag_service = RAGService(kb_base_dir=str(self.base_dir), provider=provider)
success = await rag_service.initialize(
    kb_name=self.kb_name,
    file_paths=file_paths,
    extract_numbered_items=True
)
```

#### Statistics Display (Lines 405-465)
```python
# Added generic statistics method that works with all providers
async def display_statistics_generic(self):
    # Shows stats for RAGAnything/LightRAG (entities, relations, chunks)
    # Shows stats for LlamaIndex (vector embeddings, dimensions)
    # Displays which provider was used
```

## How It Works

1. **Environment Variable**: Set `RAG_PROVIDER` in `.env` file:
   ```bash
   RAG_PROVIDER=llamaindex  # or raganything, lightrag, academic
   ```

2. **Automatic Provider Selection**: `RAGService` reads the environment variable and selects the appropriate pipeline from the factory

3. **Pipeline Execution**: The selected pipeline processes documents according to its implementation:
   - **raganything**: Uses RAG-Anything with MinerU parser, creates graph storage
   - **lightrag**: Uses LightRAG, creates graph-based knowledge base
   - **llamaindex**: Uses LlamaIndex with VectorIndexer and DenseRetriever, creates vector store
   - **academic**: Stub implementation (needs implementation)

4. **Storage Format**: Each provider creates its own storage format:
   - **raganything/lightrag**: `rag_storage/` with JSON files (entities, relations, chunks)
   - **llamaindex**: `vector_store/` with FAISS index and embeddings
   - **Note**: Storage formats are incompatible between providers

## Testing

To test different providers:

1. Set environment variable:
   ```bash
   # In .env file
   RAG_PROVIDER=llamaindex
   ```

2. Create a new knowledge base:
   ```bash
   # Via API or web interface
   # Upload documents to create new KB
   ```

3. Check logs to verify correct provider:
   ```
   [KnowledgeInit] Processing documents with RAG provider: llamaindex
   [RAGService] Initializing KB 'test_kb' with provider 'llamaindex'
   ```

4. Verify storage structure:
   ```bash
   # For LlamaIndex
   ls data/knowledge_bases/test_kb/vector_store/
   # Should see: index.faiss, embeddings.pkl, metadata.json, info.json
   
   # For RAGAnything/LightRAG
   ls data/knowledge_bases/test_kb/rag_storage/
   # Should see: kv_store_*.json files
   ```

## Benefits

1. **Flexibility**: Switch RAG providers without code changes
2. **Maintainability**: Single point of configuration in environment variables
3. **Extensibility**: Easy to add new RAG providers via factory pattern
4. **Consistency**: All pipelines use the same interface
5. **Testing**: Easy to test different providers for comparison

## Migration Notes

- **Existing KBs**: Continue to work with their original provider
- **New KBs**: Use provider specified in `RAG_PROVIDER` at creation time
- **Provider Changes**: Cannot change provider for existing KB without rebuilding
- **Storage Incompatibility**: Different providers cannot share the same KB storage

## Future Improvements

1. Store provider information in KB metadata to track which provider was used
2. Implement provider migration tool to convert between storage formats
3. Add DocumentAdder support for dynamic provider selection
4. Create unified storage format that all providers can use
