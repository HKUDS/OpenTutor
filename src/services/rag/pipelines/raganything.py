"""
RAGAnything Pipeline
====================

End-to-end pipeline wrapping RAG-Anything for academic document processing.
"""

from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from lightrag.llm.openai import openai_complete_if_cache

from src.logging import get_logger
from src.logging.adapters import LightRAGLogContext


class RAGAnythingPipeline:
    """
    RAG-Anything end-to-end Pipeline.

    Uses RAG-Anything's complete processing:
    - MinerU PDF parsing (multimodal: images, tables, equations)
    - LightRAG knowledge graph construction
    - Hybrid retrieval (hybrid/local/global/naive modes)

    This is a "monolithic" pipeline - best for academic documents.
    """

    name = "raganything"

    def __init__(
        self,
        kb_base_dir: Optional[str] = None,
        enable_image_processing: bool = True,
        enable_table_processing: bool = True,
        enable_equation_processing: bool = True,
    ):
        """
        Initialize RAGAnything pipeline.

        Args:
            kb_base_dir: Base directory for knowledge bases
            enable_image_processing: Enable image extraction and processing
            enable_table_processing: Enable table extraction and processing
            enable_equation_processing: Enable equation extraction and processing
        """
        self.logger = get_logger("RAGAnythingPipeline")
        self.kb_base_dir = kb_base_dir or str(
            Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "knowledge_bases"
        )
        self.enable_image = enable_image_processing
        self.enable_table = enable_table_processing
        self.enable_equation = enable_equation_processing
        self._instances: Dict[str, Any] = {}

    def _setup_raganything_path(self):
        """Add RAG-Anything to sys.path if available."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        raganything_path = project_root.parent / "raganything" / "RAG-Anything"
        if raganything_path.exists() and str(raganything_path) not in sys.path:
            sys.path.insert(0, str(raganything_path))

    def _get_rag_instance(self, kb_name: str):
        """Get or create RAGAnything instance."""
        kb_dir = Path(self.kb_base_dir) / kb_name
        working_dir = str(kb_dir / "rag_storage")

        if working_dir in self._instances:
            return self._instances[working_dir]

        self._setup_raganything_path()

        from openai import AsyncOpenAI
        from raganything import RAGAnything, RAGAnythingConfig

        from src.services.embedding import get_embedding_client
        from src.services.llm import get_llm_client

        llm_client = get_llm_client()
        embed_client = get_embedding_client()

        # Create AsyncOpenAI client directly - bypasses LightRAG's response_format handling
        openai_client = AsyncOpenAI(
            api_key=llm_client.config.api_key,
            base_url=llm_client.config.base_url,
        )

        async def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
            """Custom async LLM function that bypasses LightRAG's openai_complete_if_cache."""
            if history_messages is None:
                history_messages = []

            # Build messages array
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add history
            messages.extend(history_messages)

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            # Whitelist only valid OpenAI parameters, filter out LightRAG-specific ones
            valid_params = {
                "temperature",
                "top_p",
                "n",
                "stream",
                "stop",
                "max_tokens",
                "presence_penalty",
                "frequency_penalty",
                "logit_bias",
                "user",
                "seed",
            }
            clean_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}

            # Call OpenAI API directly (async)
            response = await openai_client.chat.completions.create(
                model=llm_client.config.model,
                messages=messages,
                **clean_kwargs,
            )

            return response.choices[0].message.content

        def vision_model_func(
            prompt,
            system_prompt=None,
            history_messages=[],
            image_data=None,
            messages=None,
            **kwargs,
        ):
            # Handle multimodal messages
            if messages:
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["messages", "prompt", "system_prompt", "history_messages"]
                }
                return openai_complete_if_cache(
                    llm_client.config.model,
                    prompt="",
                    messages=messages,
                    api_key=llm_client.config.api_key,
                    base_url=llm_client.config.base_url,
                    **clean_kwargs,
                )
            if image_data:
                # Build image message
                image_message = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                        },
                    ],
                }
                return openai_complete_if_cache(
                    llm_client.config.model,
                    prompt="",
                    messages=[image_message],
                    api_key=llm_client.config.api_key,
                    base_url=llm_client.config.base_url,
                    **kwargs,
                )
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

        config = RAGAnythingConfig(
            working_dir=working_dir,
            enable_image_processing=self.enable_image,
            enable_table_processing=self.enable_table,
            enable_equation_processing=self.enable_equation,
        )

        rag = RAGAnything(
            config=config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embed_client.get_embedding_func(),
        )

        self._instances[working_dir] = rag
        return rag

    async def initialize(
        self,
        kb_name: str,
        file_paths: List[str],
        extract_numbered_items: bool = True,
        **kwargs,
    ) -> bool:
        """
        Initialize KB using RAG-Anything's process_document_complete().

        Uses FileTypeRouter to classify files and route them appropriately:
        - PDF files -> MinerU parser (full document analysis)
        - Text files -> Direct read + LightRAG insert (fast)

        Args:
            kb_name: Knowledge base name
            file_paths: List of file paths to process
            extract_numbered_items: Whether to extract numbered items after processing
            **kwargs: Additional arguments

        Returns:
            True if successful
        """
        from ..components.routing import FileTypeRouter

        self.logger.info(f"Initializing KB '{kb_name}' with {len(file_paths)} files")

        kb_dir = Path(self.kb_base_dir) / kb_name
        content_list_dir = kb_dir / "content_list"
        content_list_dir.mkdir(parents=True, exist_ok=True)

        # Classify files by type
        classification = FileTypeRouter.classify_files(file_paths)

        self.logger.info(
            f"File classification: {len(classification.needs_mineru)} need MinerU, "
            f"{len(classification.text_files)} text files, "
            f"{len(classification.unsupported)} unsupported"
        )

        with LightRAGLogContext(scene="knowledge_init"):
            rag = self._get_rag_instance(kb_name)
            await rag._ensure_lightrag_initialized()

            total_files = len(classification.needs_mineru) + len(classification.text_files)
            idx = 0

            # Process files requiring MinerU (PDF, DOCX, images)
            for file_path in classification.needs_mineru:
                idx += 1
                self.logger.info(
                    f"Processing [{idx}/{total_files}] (MinerU): {Path(file_path).name}"
                )
                await rag.process_document_complete(
                    file_path=file_path,
                    output_dir=str(content_list_dir),
                    parse_method="auto",
                )

            # Process text files directly (fast path)
            for file_path in classification.text_files:
                idx += 1
                self.logger.info(
                    f"Processing [{idx}/{total_files}] (direct text): {Path(file_path).name}"
                )
                content = await FileTypeRouter.read_text_file(file_path)
                if content.strip():
                    # Insert directly into LightRAG, bypassing MinerU
                    await rag.lightrag.ainsert(content)

            # Log unsupported files
            for file_path in classification.unsupported:
                self.logger.warning(f"Skipped unsupported file: {Path(file_path).name}")

        if extract_numbered_items:
            await self._extract_numbered_items(kb_name)

        self.logger.info(f"KB '{kb_name}' initialized successfully")
        return True

    async def _extract_numbered_items(self, kb_name: str):
        """Extract numbered items using existing extraction logic."""
        try:
            import json

            from src.knowledge.extract_numbered_items import (
                extract_numbered_items_with_llm_async,
            )
            from src.services.llm import get_llm_client

            kb_dir = Path(self.kb_base_dir) / kb_name
            content_list_dir = kb_dir / "content_list"

            if not content_list_dir.exists():
                self.logger.warning("No content_list directory found, skipping extraction")
                return

            # Load all content list files
            all_content_items = []
            for json_file in content_list_dir.glob("*.json"):
                with open(json_file, "r", encoding="utf-8") as f:
                    content_items = json.load(f)
                    all_content_items.extend(content_items)

            if not all_content_items:
                self.logger.warning("No content items found for extraction")
                return

            self.logger.info(
                f"Extracting numbered items from {len(all_content_items)} content items"
            )

            llm_client = get_llm_client()
            items = await extract_numbered_items_with_llm_async(
                all_content_items,
                api_key=llm_client.config.api_key,
                base_url=llm_client.config.base_url,
            )

            # Save numbered items
            if items:
                output_file = kb_dir / "numbered_items.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                self.logger.info(f"Extracted {len(items)} numbered items")

        except ImportError as e:
            self.logger.warning(f"Could not import extraction module: {e}")
        except Exception as e:
            self.logger.error(f"Failed to extract numbered items: {e}")

    async def search(
        self,
        query: str,
        kb_name: str,
        mode: str = "hybrid",
        only_need_context: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search using RAG-Anything's aquery().

        Args:
            query: Search query
            kb_name: Knowledge base name
            mode: Search mode (hybrid, local, global, naive)
            only_need_context: Whether to only return context without answer
            **kwargs: Additional arguments

        Returns:
            Search results dictionary
        """
        with LightRAGLogContext(scene="rag_search"):
            rag = self._get_rag_instance(kb_name)
            await rag._ensure_lightrag_initialized()

            answer = await rag.aquery(query, mode=mode, only_need_context=only_need_context)
            answer_str = answer if isinstance(answer, str) else str(answer)

            return {
                "query": query,
                "answer": answer_str,
                "content": answer_str,
                "mode": mode,
                "provider": "raganything",
            }

    async def delete(self, kb_name: str) -> bool:
        """
        Delete knowledge base.

        Args:
            kb_name: Knowledge base name

        Returns:
            True if successful
        """
        import shutil

        kb_dir = Path(self.kb_base_dir) / kb_name
        working_dir = str(kb_dir / "rag_storage")

        # Remove from cache
        if working_dir in self._instances:
            del self._instances[working_dir]

        # Delete directory
        if kb_dir.exists():
            shutil.rmtree(kb_dir)
            self.logger.info(f"Deleted KB '{kb_name}'")
            return True

        return False
