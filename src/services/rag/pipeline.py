"""
RAG Pipeline
============

Composable RAG pipeline with fluent API.
"""

import asyncio
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .components.base import Component

# Default knowledge base directory
DEFAULT_KB_BASE_DIR = str(
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "knowledge_bases"
)


class RAGPipeline:
    """
    Composable RAG pipeline.

    Build custom RAG pipelines using a fluent API:

        pipeline = (
            RAGPipeline("custom", kb_base_dir="/path/to/kb")
            .parser(PDFParser())
            .chunker(SemanticChunker())
            .embedder(OpenAIEmbedder())
            .indexer(GraphIndexer())
            .retriever(HybridRetriever())
        )

        await pipeline.initialize("kb_name", ["doc1.pdf"])
        result = await pipeline.search("query", "kb_name")
    """

    def __init__(self, name: str = "default", kb_base_dir: Optional[str] = None):
        """
        Initialize RAG pipeline.

        Args:
            name: Pipeline name for logging
            kb_base_dir: Base directory for knowledge bases
        """
        self.name = name
        self.kb_base_dir = kb_base_dir or DEFAULT_KB_BASE_DIR
        self.logger = get_logger(f"Pipeline:{name}")
        self._parser: Optional[Component] = None
        self._chunkers: List[Component] = []
        self._embedder: Optional[Component] = None
        self._indexers: List[Component] = []
        self._retriever: Optional[Component] = None

    # Fluent API methods
    def parser(self, p: Component) -> "RAGPipeline":
        """Set the document parser."""
        self._parser = p
        return self

    def chunker(self, c: Component) -> "RAGPipeline":
        """Add a chunker to the pipeline."""
        self._chunkers.append(c)
        return self

    def embedder(self, e: Component) -> "RAGPipeline":
        """Set the embedder."""
        self._embedder = e
        return self

    def indexer(self, i: Component) -> "RAGPipeline":
        """Add an indexer to the pipeline."""
        self._indexers.append(i)
        return self

    def retriever(self, r: Component) -> "RAGPipeline":
        """Set the retriever."""
        self._retriever = r
        return self

    async def initialize(self, kb_name: str, file_paths: List[str], **kwargs) -> bool:
        """
        Run full initialization pipeline.

        Args:
            kb_name: Knowledge base name
            file_paths: List of file paths to process
            **kwargs: Additional arguments passed to components

        Returns:
            True if successful
        """
        self.logger.info(f"Initializing KB '{kb_name}' with {len(file_paths)} files")

        if not self._parser:
            raise ValueError("No parser configured. Use .parser() to set one.")

        # Stage 1: Parse documents
        self.logger.info("Stage 1: Parsing documents...")
        documents = []
        for path in file_paths:
            doc = await self._parser.process(path, **kwargs)
            documents.append(doc)

        # Stage 2: Chunk (sequential - later chunkers see earlier results)
        if self._chunkers:
            self.logger.info("Stage 2: Chunking...")
            for chunker in self._chunkers:
                for doc in documents:
                    new_chunks = await chunker.process(doc, **kwargs)
                    doc.chunks.extend(new_chunks)

        # Stage 3: Embed
        if self._embedder:
            self.logger.info("Stage 3: Embedding...")
            for doc in documents:
                await self._embedder.process(doc, **kwargs)

        # Stage 4: Index (can run in parallel)
        if self._indexers:
            self.logger.info("Stage 4: Indexing...")
            await asyncio.gather(
                *[indexer.process(kb_name, documents, **kwargs) for indexer in self._indexers]
            )

        self.logger.info(f"KB '{kb_name}' initialized successfully")
        return True

    async def search(self, query: str, kb_name: str, **kwargs) -> Dict[str, Any]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            kb_name: Knowledge base name
            **kwargs: Additional arguments passed to retriever

        Returns:
            Search results dictionary
        """
        if not self._retriever:
            raise ValueError("No retriever configured. Use .retriever() to set one.")

        return await self._retriever.process(query, kb_name=kb_name, **kwargs)

    async def delete(self, kb_name: str) -> bool:
        """
        Delete a knowledge base.

        Args:
            kb_name: Knowledge base name

        Returns:
            True if successful
        """
        self.logger.info(f"Deleting KB '{kb_name}'")

        kb_dir = Path(self.kb_base_dir) / kb_name
        if kb_dir.exists():
            shutil.rmtree(kb_dir)
            self.logger.info(f"Deleted KB directory: {kb_dir}")
            return True

        self.logger.warning(f"KB directory not found: {kb_dir}")
        return False
