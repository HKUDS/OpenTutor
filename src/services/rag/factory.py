"""
Pipeline Factory
================

Factory for creating and managing RAG pipelines.
"""

from typing import Callable, Dict, List, Optional

from .pipelines import lightrag, llamaindex
from .pipelines.raganything import RAGAnythingPipeline

# Pipeline registry
_PIPELINES: Dict[str, Callable] = {
    "raganything": RAGAnythingPipeline,  # Full multimodal: MinerU parser, deep analysis (slow, thorough)
    "lightrag": lightrag.LightRAGPipeline,  # Knowledge graph: PDFParser, fast text-only (medium speed)
    "llamaindex": llamaindex.LlamaIndexPipeline,  # Vector-only: Simple chunking, fast (fastest)
}


def get_pipeline(name: str = "raganything", kb_base_dir: Optional[str] = None, **kwargs):
    """
    Get a pre-configured pipeline by name.

    Args:
        name: Pipeline name (raganything, lightrag, llamaindex, academic)
        kb_base_dir: Base directory for knowledge bases (passed to all pipelines)
        **kwargs: Additional arguments passed to pipeline constructor

    Returns:
        Pipeline instance

    Raises:
        ValueError: If pipeline name is not found
    """
    if name not in _PIPELINES:
        available = list(_PIPELINES.keys())
        raise ValueError(f"Unknown pipeline: {name}. Available: {available}")

    factory = _PIPELINES[name]

    # Handle different pipeline types:
    # - lightrag, academic: functions that return RAGPipeline
    # - llamaindex, raganything: classes that need instantiation
    if name in ("lightrag", "academic"):
        # LightRAGPipeline and AcademicPipeline are factory functions
        return factory(kb_base_dir=kb_base_dir)
    elif name in ("llamaindex", "raganything"):
        # LlamaIndexPipeline and RAGAnythingPipeline are classes
        if kb_base_dir:
            kwargs["kb_base_dir"] = kb_base_dir
        return factory(**kwargs)
    else:
        # Default: try calling with kb_base_dir
        return factory(kb_base_dir=kb_base_dir)


def list_pipelines() -> List[Dict[str, str]]:
    """
    List available pipelines.

    Returns:
        List of pipeline info dictionaries
    """
    return [
        {
            "id": "llamaindex",
            "name": "LlamaIndex",
            "description": "Pure vector retrieval, fastest processing speed.",
        },
        {
            "id": "lightrag",
            "name": "LightRAG",
            "description": "Lightweight knowledge graph retrieval, fast processing of text documents.",
        },
        {
            "id": "raganything",
            "name": "RAG-Anything",
            "description": "Multimodal document processing with chart and formula extraction, builds knowledge graphs.",
        },
    ]


def register_pipeline(name: str, factory: Callable):
    """
    Register a custom pipeline.

    Args:
        name: Pipeline name
        factory: Factory function or class that creates the pipeline
    """
    _PIPELINES[name] = factory


def has_pipeline(name: str) -> bool:
    """
    Check if a pipeline exists.

    Args:
        name: Pipeline name

    Returns:
        True if pipeline exists
    """
    return name in _PIPELINES


# Backward compatibility with old plugin API
def get_plugin(name: str) -> Dict[str, Callable]:
    """
    DEPRECATED: Use get_pipeline() instead.

    Get a plugin by name (maps to pipeline API).
    """
    import warnings

    warnings.warn(
        "get_plugin() is deprecated, use get_pipeline() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    pipeline = get_pipeline(name)
    return {
        "initialize": pipeline.initialize,
        "search": pipeline.search,
        "delete": getattr(pipeline, "delete", lambda kb: True),
    }


def list_plugins() -> List[Dict[str, str]]:
    """
    DEPRECATED: Use list_pipelines() instead.
    """
    import warnings

    warnings.warn(
        "list_plugins() is deprecated, use list_pipelines() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return list_pipelines()


def has_plugin(name: str) -> bool:
    """
    DEPRECATED: Use has_pipeline() instead.
    """
    import warnings

    warnings.warn(
        "has_plugin() is deprecated, use has_pipeline() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return has_pipeline(name)
