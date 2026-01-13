"""
LlamaIndex Pipeline
===================

Component-based pipeline using vector indexing for fast retrieval.
"""

from typing import Optional

from ..components.chunkers import SemanticChunker
from ..components.embedders import OpenAIEmbedder
from ..components.indexers import VectorIndexer
from ..components.parsers import TextParser
from ..components.retrievers import DenseRetriever
from ..pipeline import RAGPipeline


def LlamaIndexPipeline(kb_base_dir: Optional[str] = None) -> RAGPipeline:
    """
    Create a LlamaIndex-style pipeline.

    This pipeline uses:
    - TextParser for document parsing (supports txt, md files)
    - SemanticChunker for text chunking
    - OpenAIEmbedder for embedding generation
    - VectorIndexer for vector indexing
    - DenseRetriever for dense retrieval

    Args:
        kb_base_dir: Base directory for knowledge bases

    Returns:
        Configured RAGPipeline
    """
    return (
        RAGPipeline("llamaindex", kb_base_dir=kb_base_dir)
        .parser(TextParser())
        .chunker(SemanticChunker())
        .embedder(OpenAIEmbedder())
        .indexer(VectorIndexer(kb_base_dir=kb_base_dir))
        .retriever(DenseRetriever(kb_base_dir=kb_base_dir))
    )
