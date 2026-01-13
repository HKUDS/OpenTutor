"""
LightRAG Pipeline
=================

Component-based pipeline using LightRAG for knowledge graph indexing.
"""

from typing import Optional

from ..components.chunkers import SemanticChunker
from ..components.embedders import OpenAIEmbedder
from ..components.indexers import GraphIndexer
from ..components.parsers import TextParser
from ..components.retrievers import HybridRetriever
from ..pipeline import RAGPipeline


def LightRAGPipeline(kb_base_dir: Optional[str] = None) -> RAGPipeline:
    """
    Create a LightRAG-based pipeline.

    This pipeline uses:
    - TextParser for document parsing (supports txt, md files)
    - SemanticChunker for text chunking
    - OpenAIEmbedder for embedding generation
    - GraphIndexer for knowledge graph indexing
    - HybridRetriever for retrieval

    Args:
        kb_base_dir: Base directory for knowledge bases

    Returns:
        Configured RAGPipeline
    """
    return (
        RAGPipeline("lightrag", kb_base_dir=kb_base_dir)
        .parser(TextParser())
        .chunker(SemanticChunker())
        .embedder(OpenAIEmbedder())
        .indexer(GraphIndexer(kb_base_dir=kb_base_dir))
        .retriever(HybridRetriever(kb_base_dir=kb_base_dir))
    )
