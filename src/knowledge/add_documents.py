#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Incrementally add documents to existing knowledge base.
Improved version with Hash-based duplicate checking, robust error handling,
and architectural improvements for data integrity and vision support.
"""

import argparse
import asyncio
from datetime import datetime
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING, Any, Dict, List

from dotenv import load_dotenv

# Attempt imports for dynamic dependencies
try:
    from lightrag.llm.openai import openai_complete_if_cache
    from lightrag.utils import EmbeddingFunc
except ImportError:
    # These will be caught during runtime if needed
    openai_complete_if_cache = None
    EmbeddingFunc = None

# Type hinting support for dynamic imports
if TYPE_CHECKING:
    try:
        from raganything import RAGAnything
        from raganything import RAGAnythingConfig as RAGAnythingConfigType
    except ImportError:
        RAGAnything = Any
        RAGAnythingConfigType = Any
else:
    RAGAnything = None
    RAGAnythingConfigType = None

# Placeholder for runtime classes
raganything_cls = None
RAGAnythingConfig = None


def load_dynamic_imports(project_root: Path):
    """Handle the path injections and dynamic imports safely."""
    global raganything_cls, RAGAnythingConfig

    sys.path.insert(0, str(project_root))
    raganything_path = project_root.parent / "raganything" / "RAG-Anything"
    if raganything_path.exists():
        sys.path.insert(0, str(raganything_path))

    try:
        from raganything import RAGAnything as RA
        from raganything import RAGAnythingConfig as RAC

        raganything_cls = RA
        RAGAnythingConfig = RAC
    except ImportError:
        pass


from src.knowledge.extract_numbered_items import process_content_list
from src.logging import LightRAGLogContext, get_logger
from src.services.embedding import (
    get_embedding_client,
    get_embedding_config,
    reset_embedding_client,
)
from src.services.llm import get_llm_config

logger = get_logger("KnowledgeInit")

# Default base directory for knowledge bases
DEFAULT_BASE_DIR = "./data/knowledge_bases"


class DocumentAdder:
    """Add documents to existing knowledge base with Hash-validation"""

    def __init__(
        self,
        kb_name: str,
        base_dir=DEFAULT_BASE_DIR,
        api_key: str | None = None,
        base_url: str | None = None,
        progress_tracker=None,
        rag_provider: str | None = None,
    ):
        self.kb_name = kb_name
        self.base_dir = Path(base_dir)
        self.kb_dir = self.base_dir / kb_name

        if not self.kb_dir.exists():
            raise ValueError(f"Knowledge base does not exist: {kb_name}")

        self.raw_dir = self.kb_dir / "raw"
        self.images_dir = self.kb_dir / "images"
        self.rag_storage_dir = self.kb_dir / "rag_storage"
        self.content_list_dir = self.kb_dir / "content_list"
        self.metadata_file = self.kb_dir / "metadata.json"

        if not self.rag_storage_dir.exists():
            raise ValueError(f"Knowledge base not initialized: {kb_name}")

        self.api_key = api_key
        self.base_url = base_url
        self.progress_tracker = progress_tracker
        self.rag_provider = rag_provider
        self._ensure_working_directories()

    def _ensure_working_directories(self):
        for directory in [self.raw_dir, self.images_dir, self.content_list_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        Uses 64KB chunks for better throughput on SSDs.
        """
        sha256_hash = hashlib.sha256()
        chunk_size = 65536  # 64KB
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_ingested_hashes(self) -> Dict[str, str]:
        """Get map of filename -> hash from metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("file_hashes", {})
            except Exception:
                return {}
        return {}

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    def add_documents(self, source_files: List[str], allow_duplicates: bool = False) -> List[Path]:
        """
        Synchronous phase: Validates hashes and prepares files.
        Treats 'raw/' as a Write-Ahead Log: files exist there before being canonized in metadata.
        """
        logger.info(f"Validating documents for '{self.kb_name}'...")

        ingested_hashes = self.get_ingested_hashes()

        files_to_process = []
        for source in source_files:
            source_path = Path(source)
            if not source_path.exists():
                logger.warning(f"  ⚠ Missing: {source}")
                continue

            current_hash = self._get_file_hash(source_path)

            # 1. Check if content is already fully ingested (Canon Check)
            # We look for value matches in the metadata hash map
            if current_hash in ingested_hashes.values() and not allow_duplicates:
                logger.info(f"  → Skipped (content already indexed): {source_path.name}")
                continue

            # 2. Prepare file in raw/ (Write-Ahead Log)
            dest_path = self.raw_dir / source_path.name

            should_copy = True
            if dest_path.exists():
                # If file exists in raw, check if it's the same content
                dest_hash = self._get_file_hash(dest_path)
                if dest_hash == current_hash:
                    should_copy = False
                    logger.info(f"  ⚠ Recovering staged file (interrupted run): {source_path.name}")
                else:
                    if not allow_duplicates:
                        # Name collision with different content
                        logger.info(
                            f"  → Skipped (filename collision with different content): {source_path.name}"
                        )
                        continue
                    else:
                        logger.info(f"  → Overwriting existing raw file: {source_path.name}")

            if should_copy:
                shutil.copy2(source_path, dest_path)
                logger.info(f"  ✓ Staged to raw: {source_path.name}")

            files_to_process.append(dest_path)

        return files_to_process

    async def process_new_documents(self, new_files: List[Path]):
        """
        Async phase: Ingests files into the RAG system.

        Uses FileTypeRouter to classify files and route them appropriately:
        - PDF/DOCX/images -> MinerU parser (full document analysis)
        - Text/Markdown -> Direct read + LightRAG insert (fast)
        """
        if not new_files:
            return None

        if raganything_cls is None:
            raise ImportError("RAGAnything module not found.")

        from src.services.rag.components.routing import FileTypeRouter

        # Pre-import progress stage if needed to avoid overhead in loop
        ProgressStage: Any = None
        if self.progress_tracker:
            from src.knowledge.progress_tracker import ProgressStage

        self.llm_cfg = get_llm_config()
        model = self.llm_cfg.model
        api_key = self.api_key or self.llm_cfg.api_key
        base_url = self.base_url or self.llm_cfg.base_url

        # LLM Function Wrapper
        def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
            if history_messages is None:
                history_messages = []
            return openai_complete_if_cache(
                model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )

        # Vision Function Wrapper - Robust history handling
        def vision_model_func(
            prompt,
            system_prompt=None,
            history_messages=None,
            image_data=None,
            messages=None,
            **kwargs,
        ):
            if history_messages is None:
                history_messages = []
            # If pre-formatted messages are provided, sanitize them
            if messages:
                safe_messages = self._filter_valid_messages(messages)
                return openai_complete_if_cache(
                    model,
                    prompt="",
                    messages=safe_messages,
                    api_key=api_key,
                    base_url=base_url,
                    **kwargs,
                )

            # --- Construct Message History ---
            current_messages = []

            # 1. Add System Prompt (if provided)
            if system_prompt:
                current_messages.append({"role": "system", "content": system_prompt})

            # 2. Add History (Filtering out conflicting system prompts)
            if history_messages:
                # Filter out system messages from history to avoid duplicates/conflicts with the new system_prompt
                filtered_history = [
                    msg
                    for msg in history_messages
                    if isinstance(msg, dict) and msg.get("role") != "system"
                ]
                current_messages.extend(filtered_history)

            # 3. Construct New User Message
            user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            if image_data:
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    }
                )

            # 4. Merge Logic: Avoid back-to-back user messages
            if current_messages and current_messages[-1].get("role") == "user":
                last_msg = current_messages[-1]
                # If last content is string, convert to list format first
                if isinstance(last_msg["content"], str):
                    last_msg["content"] = [{"type": "text", "text": last_msg["content"]}]

                # Append new content blocks
                if isinstance(last_msg["content"], list):
                    last_msg["content"].extend(user_content)
                else:
                    # Fallback if structure is unexpected, just append new message
                    current_messages.append({"role": "user", "content": user_content})
            else:
                current_messages.append({"role": "user", "content": user_content})

            return openai_complete_if_cache(
                model,
                prompt="",
                messages=current_messages,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )

        # Embedding Setup
        reset_embedding_client()
        embedding_cfg = get_embedding_config()
        embedding_client = get_embedding_client()

        async def unified_embed_func(texts):
            return await embedding_client.embed(texts)

        embedding_func = EmbeddingFunc(
            embedding_dim=embedding_cfg.dim,
            max_token_size=embedding_cfg.max_tokens,
            func=unified_embed_func,
        )

        config = RAGAnythingConfig(
            working_dir=str(self.rag_storage_dir),
            parser="mineru",
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        )

        with LightRAGLogContext(scene="knowledge_init"):
            rag = raganything_cls(
                config=config,
                llm_model_func=llm_model_func,
                vision_model_func=vision_model_func,
                embedding_func=embedding_func,
            )
            if hasattr(rag, "_ensure_lightrag_initialized"):
                await rag._ensure_lightrag_initialized()

        # Classify files by type
        file_paths_str = [str(f) for f in new_files]
        classification = FileTypeRouter.classify_files(file_paths_str)

        logger.info(
            f"File classification: {len(classification.needs_mineru)} need MinerU, "
            f"{len(classification.text_files)} text files, "
            f"{len(classification.unsupported)} unsupported"
        )

        processed_files = []
        total_files = len(classification.needs_mineru) + len(classification.text_files)
        idx = 0

        # Process files requiring MinerU (PDF, DOCX, images)
        for doc_file_str in classification.needs_mineru:
            doc_file = Path(doc_file_str)
            idx += 1
            try:
                if self.progress_tracker and ProgressStage:
                    self.progress_tracker.update(
                        ProgressStage.PROCESSING_FILE,
                        f"Ingesting (MinerU) {doc_file.name}",
                        current=idx,
                        total=total_files,
                    )

                # Verify file still exists in raw/ (it should, as we staged it)
                if not doc_file.exists():
                    logger.error(f"  ✗ Failed: Staged file missing {doc_file.name}")
                    continue

                await asyncio.wait_for(
                    rag.process_document_complete(
                        file_path=str(doc_file),
                        output_dir=str(self.content_list_dir),
                        parse_method="auto",
                    ),
                    timeout=600.0,
                )
                processed_files.append(doc_file)
                # Store hash on success - "Canonizing" the file
                self._record_successful_hash(doc_file)
                logger.info(f"  ✓ Processed (MinerU): {doc_file.name}")
            except Exception as e:
                logger.exception(f"  ✗ Failed {doc_file.name}: {e}")

        # Process text files directly (fast path - no MinerU)
        for doc_file_str in classification.text_files:
            doc_file = Path(doc_file_str)
            idx += 1
            try:
                if self.progress_tracker and ProgressStage:
                    self.progress_tracker.update(
                        ProgressStage.PROCESSING_FILE,
                        f"Ingesting (text) {doc_file.name}",
                        current=idx,
                        total=total_files,
                    )

                # Verify file still exists
                if not doc_file.exists():
                    logger.error(f"  ✗ Failed: Staged file missing {doc_file.name}")
                    continue

                # Read text file directly
                content = await FileTypeRouter.read_text_file(str(doc_file))
                if content.strip():
                    # Insert directly into LightRAG, bypassing MinerU
                    await rag.lightrag.ainsert(content)
                    processed_files.append(doc_file)
                    self._record_successful_hash(doc_file)
                    logger.info(f"  ✓ Processed (text): {doc_file.name}")
                else:
                    logger.warning(f"  ⚠ Skipped empty file: {doc_file.name}")
            except Exception as e:
                logger.exception(f"  ✗ Failed {doc_file.name}: {e}")

        # Log unsupported files
        for doc_file_str in classification.unsupported:
            logger.warning(f"  ⚠ Skipped unsupported file: {Path(doc_file_str).name}")

        await self.fix_structure()
        return processed_files

    def _record_successful_hash(self, file_path: Path):
        """Update metadata with the hash of a successfully processed file."""
        file_hash = self._get_file_hash(file_path)
        try:
            metadata = {}
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            if "file_hashes" not in metadata:
                metadata["file_hashes"] = {}

            metadata["file_hashes"][file_path.name] = file_hash
            # Atomic write: write to temp file, then rename
            fd, tmp_path = tempfile.mkstemp(dir=self.kb_dir, suffix=".json")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.metadata_file)
            except Exception:
                os.unlink(tmp_path)
                raise
        except Exception as e:
            logger.warning(f"Could not update hash metadata: {e}")

    @staticmethod
    def _filter_valid_messages(messages):
        return [
            m
            for m in messages
            if isinstance(m, dict) and m.get("role") is not None and m.get("content") is not None
        ]

    async def fix_structure(self):
        """Robustly moves nested outputs and cleans up."""
        logger.info("Organizing storage structure...")

        # 1. Identify moves
        moves = []
        for doc_dir in self.content_list_dir.glob("*"):
            if not doc_dir.is_dir():
                continue

            # Content List
            json_src = next(doc_dir.glob("auto/*_content_list.json"), None)
            if json_src:
                moves.append((json_src, self.content_list_dir / f"{doc_dir.name}.json"))

            # Images
            for img in doc_dir.glob("auto/images/*"):
                moves.append((img, self.images_dir / img.name))

        # 2. Execute moves
        for src, dest in moves:
            if src.exists():
                await self._run_in_executor(shutil.copy2, src, dest)

        # 3. Safe Cleanup: Only delete directories we actually processed
        for doc_dir in self.content_list_dir.glob("*"):
            if doc_dir.is_dir():
                # Safety check: only delete if it looks like a parser output (has 'auto' subdir)
                # This prevents wiping manual user folders in content_list_dir
                if (doc_dir / "auto").exists():
                    await self._run_in_executor(shutil.rmtree, doc_dir, ignore_errors=True)

    def extract_numbered_items_for_new_docs(self, processed_files, batch_size=20):
        if not processed_files:
            return

        llm_cfg = getattr(self, "llm_cfg", None)
        if llm_cfg is None:
            llm_cfg = get_llm_config()
        api_key = self.api_key or llm_cfg.api_key
        base_url = self.base_url or llm_cfg.base_url
        output_file = self.kb_dir / "numbered_items.json"

        for doc_file in processed_files:
            content_list_file = self.content_list_dir / f"{doc_file.stem}.json"
            if content_list_file.exists():
                process_content_list(
                    content_list_file=content_list_file,
                    output_file=output_file,
                    api_key=api_key,
                    base_url=base_url,
                    batch_size=batch_size,
                    merge=output_file.exists(),
                )

    def update_metadata(self, added_count: int):
        if not self.metadata_file.exists():
            return
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            metadata["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Update RAG provider if specified
            if self.rag_provider:
                metadata["rag_provider"] = self.rag_provider

                # Also save to centralized config file
                try:
                    from src.services.config import get_kb_config_service

                    kb_config_service = get_kb_config_service()
                    kb_config_service.set_rag_provider(self.kb_name, self.rag_provider)
                except Exception as config_err:
                    logger.warning(f"Failed to save to centralized config: {config_err}")

            history = metadata.get("update_history", [])
            history.append(
                {
                    "timestamp": metadata["last_updated"],
                    "action": "incremental_add",
                    "count": added_count,
                }
            )
            metadata["update_history"] = history

            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Metadata update failed: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Incrementally add documents to RAG KB")
    parser.add_argument("kb_name", help="KB Name")
    parser.add_argument("--docs", nargs="+", help="Files")
    parser.add_argument("--docs-dir", help="Directory")
    parser.add_argument("--base-dir", default=DEFAULT_BASE_DIR)
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY"))
    parser.add_argument("--base-url", default=os.getenv("LLM_HOST"))
    parser.add_argument("--allow-duplicates", action="store_true")

    args = parser.parse_args()

    # Initialize dynamic paths
    project_root = Path(__file__).parent.parent.parent
    load_dynamic_imports(project_root)

    load_dotenv()

    doc_files = []
    if args.docs:
        doc_files.extend(args.docs)
    if args.docs_dir:
        p = Path(args.docs_dir)
        for ext in ["*.pdf", "*.docx", "*.txt", "*.md"]:
            doc_files.extend([str(f) for f in p.glob(ext)])

    if not doc_files:
        logger.error("No documents provided.")
        return

    adder = DocumentAdder(args.kb_name, args.base_dir, args.api_key, args.base_url)

    # 1. Sync Phase (Validate and Stage)
    new_files = adder.add_documents(doc_files, allow_duplicates=args.allow_duplicates)

    # 2. Async Ingestion (Process and Canonize)
    if new_files:
        processed = await adder.process_new_documents(new_files)
        if processed:
            adder.extract_numbered_items_for_new_docs(processed)
            adder.update_metadata(len(processed))
            logger.info(f"Done! Successfully added {len(processed)} documents.")
    else:
        logger.info("No new unique documents to add.")


if __name__ == "__main__":
    asyncio.run(main())
