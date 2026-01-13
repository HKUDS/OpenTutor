"""
RAG Service
===========

Unified RAG pipeline service for DeepTutor.

Provides:
- RAGService: Unified entry point for all RAG operations
- Composable RAG pipelines
- Pre-configured pipelines (RAGAnything, LightRAG, LlamaIndex, Academic)
- Modular components (parsers, chunkers, embedders, indexers, retrievers)
- Factory for pipeline creation

Usage:
    # Recommended: Use RAGService for all operations
    from src.services.rag import RAGService

    service = RAGService(provider="llamaindex")
    await service.initialize("kb_name", ["doc1.txt", "doc2.txt"])
    result = await service.search("query", "kb_name")

    # Alternative: Use factory directly
    from src.services.rag import get_pipeline

    pipeline = get_pipeline("raganything")
    await pipeline.initialize("kb_name", ["doc1.pdf"])
    result = await pipeline.search("query", "kb_name")

    # Or build custom pipeline
    from src.services.rag import RAGPipeline
    from src.services.rag.components import TextParser, SemanticChunker

    custom = (
        RAGPipeline("custom")
        .parser(TextParser())
        .chunker(SemanticChunker())
    )
"""

from .factory import get_pipeline, has_pipeline, list_pipelines, register_pipeline
from .pipeline import RAGPipeline

# Import pipeline classes for convenience
from .pipelines.raganything import RAGAnythingPipeline
from .service import RAGService
from .types import Chunk, Document, SearchResult

__all__ = [
    # Service (recommended entry point)
    "RAGService",
    # Types
    "Document",
    "Chunk",
    "SearchResult",
    # Pipeline
    "RAGPipeline",
    # Factory
    "get_pipeline",
    "list_pipelines",
    "register_pipeline",
    "has_pipeline",
    # Pipeline implementations
    "RAGAnythingPipeline",
]
