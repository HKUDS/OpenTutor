"""
Pre-configured Pipelines
========================

Ready-to-use RAG pipelines for common use cases.
"""

from .academic import AcademicPipeline
from .lightrag import LightRAGPipeline
from .llamaindex import LlamaIndexPipeline
from .raganything import RAGAnythingPipeline

__all__ = [
    "RAGAnythingPipeline",
    "LightRAGPipeline",
    "LlamaIndexPipeline",
    "AcademicPipeline",
]
