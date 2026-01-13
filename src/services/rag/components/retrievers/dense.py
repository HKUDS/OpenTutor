"""
Dense Retriever
===============

Dense vector-based retriever.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseComponent


class DenseRetriever(BaseComponent):
    """
    Dense vector retriever.

    Uses embedding similarity for retrieval.
    """

    name = "dense_retriever"

    def __init__(self, kb_base_dir: Optional[str] = None, top_k: int = 5):
        """
        Initialize dense retriever.

        Args:
            kb_base_dir: Base directory for knowledge bases
            top_k: Number of results to return
        """
        super().__init__()
        self.kb_base_dir = kb_base_dir or str(
            Path(__file__).resolve().parent.parent.parent.parent.parent.parent
            / "data"
            / "knowledge_bases"
        )
        self.top_k = top_k

    async def process(self, query: str, kb_name: str, **kwargs) -> Dict[str, Any]:
        """
        Search using dense embeddings.

        Args:
            query: Search query
            kb_name: Knowledge base name
            **kwargs: Additional arguments

        Returns:
            Search results dictionary
        """
        self.logger.info(f"Dense search in {kb_name}: {query[:50]}...")

        from src.services.embedding import get_embedding_client

        # Get query embedding
        client = get_embedding_client()
        query_embedding = (await client.embed([query]))[0]

        # Load index
        kb_dir = Path(self.kb_base_dir) / kb_name / "vector_store"
        index_file = kb_dir / "index.json"

        if not index_file.exists():
            self.logger.warning(f"No vector index found at {index_file}")
            return {
                "query": query,
                "answer": "No documents indexed.",
                "content": "",
                "mode": "dense",
                "provider": "vector",
            }

        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        # Compute similarities
        results = []
        for item in index_data:
            if item.get("embedding"):
                similarity = self._cosine_similarity(query_embedding, item["embedding"])
                results.append((similarity, item))

        # Sort by similarity
        results.sort(key=lambda x: x[0], reverse=True)
        top_results = results[: self.top_k]

        # Build response
        content_parts = []
        for score, item in top_results:
            content_parts.append(f"[Score: {score:.3f}] {item['content'][:500]}")

        content = "\n\n".join(content_parts)

        return {
            "query": query,
            "answer": content,
            "content": content,
            "mode": "dense",
            "provider": "vector",
            "results": [item for _, item in top_results],
        }

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)
