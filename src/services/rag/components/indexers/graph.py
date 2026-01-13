"""
Graph Indexer
=============

Knowledge graph indexer using LightRAG.
"""

from pathlib import Path
import sys
from typing import Dict, List, Optional

from ...types import Document
from ..base import BaseComponent


class GraphIndexer(BaseComponent):
    """
    Knowledge graph indexer using LightRAG.

    Builds a knowledge graph from documents for graph-based retrieval.
    """

    name = "graph_indexer"
    _instances: Dict[str, any] = {}  # Cache RAG instances

    def __init__(self, kb_base_dir: Optional[str] = None):
        """
        Initialize graph indexer.

        Args:
            kb_base_dir: Base directory for knowledge bases
        """
        super().__init__()
        self.kb_base_dir = kb_base_dir or str(
            Path(__file__).resolve().parent.parent.parent.parent.parent.parent
            / "data"
            / "knowledge_bases"
        )

    def _get_rag_instance(self, kb_name: str):
        """Get or create a RAGAnything instance."""
        working_dir = str(Path(self.kb_base_dir) / kb_name / "rag_storage")

        if working_dir in self._instances:
            return self._instances[working_dir]

        # Add RAG-Anything path
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        raganything_path = project_root.parent / "raganything" / "RAG-Anything"
        if raganything_path.exists() and str(raganything_path) not in sys.path:
            sys.path.insert(0, str(raganything_path))

        try:
            from lightrag.llm.openai import openai_complete_if_cache
            from raganything import RAGAnything, RAGAnythingConfig

            from src.services.embedding import get_embedding_client
            from src.services.llm import get_llm_client

            llm_client = get_llm_client()
            embed_client = get_embedding_client()

            # LLM function using services
            def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
                return openai_complete_if_cache(
                    llm_client.config.model,
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_key=llm_client.config.api_key,
                    base_url=llm_client.config.base_url,
                    **kwargs,
                )

            config = RAGAnythingConfig(
                working_dir=working_dir,
                enable_image_processing=True,
                enable_table_processing=True,
                enable_equation_processing=True,
            )

            rag = RAGAnything(
                config=config,
                llm_model_func=llm_model_func,
                embedding_func=embed_client.get_embedding_func(),
            )

            self._instances[working_dir] = rag
            return rag

        except ImportError as e:
            self.logger.error(f"Failed to import RAG-Anything: {e}")
            raise

    async def process(self, kb_name: str, documents: List[Document], **kwargs) -> bool:
        """
        Build knowledge graph from documents.

        Args:
            kb_name: Knowledge base name
            documents: List of documents to index
            **kwargs: Additional arguments

        Returns:
            True if successful
        """
        self.logger.info(f"Building knowledge graph for {kb_name}...")

        from src.logging.adapters import LightRAGLogContext

        # Use log forwarding context
        with LightRAGLogContext(scene="indexer"):
            rag = self._get_rag_instance(kb_name)
            await rag._ensure_lightrag_initialized()

            for doc in documents:
                if doc.content:
                    await rag.ainsert(doc.content)

        self.logger.info("Knowledge graph built successfully")
        return True
