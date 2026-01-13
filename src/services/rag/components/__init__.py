"""
RAG Components
==============

Modular components for building RAG pipelines.

Components follow a simple protocol:
- Each component has a `name` attribute
- Each component has an async `process()` method
"""

# Import component modules for convenience
from . import chunkers, embedders, indexers, parsers, retrievers
from .base import BaseComponent, Component

__all__ = [
    "Component",
    "BaseComponent",
    "parsers",
    "chunkers",
    "embedders",
    "indexers",
    "retrievers",
]
