"""
Vector Indexer
==============

Vector-based indexer using dense embeddings.
"""

from pathlib import Path
from typing import List, Optional

from ...types import Document
from ..base import BaseComponent


class VectorIndexer(BaseComponent):
    """
    Vector indexer using dense embeddings.

    Can use LlamaIndex or other vector stores for indexing.
    """

    name = "vector_indexer"

    def __init__(self, kb_base_dir: Optional[str] = None):
        """
        Initialize vector indexer.

        Args:
            kb_base_dir: Base directory for knowledge bases
        """
        super().__init__()
        self.kb_base_dir = kb_base_dir or str(
            Path(__file__).resolve().parent.parent.parent.parent.parent.parent
            / "data"
            / "knowledge_bases"
        )

    async def process(self, kb_name: str, documents: List[Document], **kwargs) -> bool:
        """
        Index documents using vector embeddings.

        Args:
            kb_name: Knowledge base name
            documents: List of documents to index
            **kwargs: Additional arguments

        Returns:
            True if successful
        """
        self.logger.info(f"Indexing {len(documents)} documents into vector store for {kb_name}")

        # Collect all chunks with embeddings
        all_chunks = []
        for doc in documents:
            for chunk in doc.chunks:
                # Check if embedding exists (handles numpy arrays and lists)
                if chunk.embedding is not None and len(chunk.embedding) > 0:
                    all_chunks.append(chunk)

        if not all_chunks:
            self.logger.warning("No chunks with embeddings to index")
            return False

        self.logger.info(f"Indexing {len(all_chunks)} chunks")

        # Create vector store directory
        kb_dir = Path(self.kb_base_dir) / kb_name / "vector_store"
        kb_dir.mkdir(parents=True, exist_ok=True)

        # Simple JSON-based storage (placeholder for actual vector store)
        import json

        index_data = []
        for i, chunk in enumerate(all_chunks):
            index_data.append(
                {
                    "id": i,
                    "content": chunk.content,
                    "type": chunk.chunk_type,
                    "metadata": chunk.metadata,
                    "embedding": chunk.embedding,
                }
            )

        with open(kb_dir / "index.json", "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Vector index saved to {kb_dir}")
        return True
