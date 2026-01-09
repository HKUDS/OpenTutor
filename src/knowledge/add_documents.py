#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Incrementally add documents to existing knowledge base

This script allows adding new documents to an existing knowledge base,
rather than recreating the entire knowledge base.
Only newly added documents will be processed, without affecting the existing knowledge graph.
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# Add raganything module path
raganything_path = project_root.parent / "raganything" / "RAG-Anything"
if raganything_path.exists():
    sys.path.insert(0, str(raganything_path))

from dotenv import load_dotenv
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from raganything import RAGAnything, RAGAnythingConfig

try:
    from openai import APIError, APIStatusError, RateLimitError
except ImportError:  # pragma: no cover - openai is an optional dependency at runtime
    APIError = APIStatusError = RateLimitError = None

from src.services.embedding import get_embedding_client, get_embedding_config
from src.services.llm import get_llm_config

load_dotenv(dotenv_path=".env", override=False)

from src.logging import LightRAGLogContext, get_logger

logger = get_logger("KnowledgeInit")

# Import numbered items extraction functionality
from src.knowledge.extract_numbered_items import process_content_list


class DocumentAdder:
    """Add documents to existing knowledge base"""

    def __init__(
        self,
        kb_name: str,
        base_dir="./data/knowledge_bases",
        api_key: str = None,
        base_url: str = None,
        progress_tracker=None,
    ):
        self.kb_name = kb_name
        self.base_dir = Path(base_dir)
        self.kb_dir = self.base_dir / kb_name

        # Check if knowledge base exists
        if not self.kb_dir.exists():
            raise ValueError(f"Knowledge base does not exist: {kb_name}")

        # Directory structure
        self.raw_dir = self.kb_dir / "raw"
        self.images_dir = self.kb_dir / "images"
        self.rag_storage_dir = self.kb_dir / "rag_storage"
        self.content_list_dir = self.kb_dir / "content_list"

        # Check directory structure
        if not self.rag_storage_dir.exists():
            raise ValueError(
                f"Knowledge base not initialized: {kb_name}, please create knowledge base first"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.embedding_cfg = get_embedding_config()
        self.llm_cfg = get_llm_config()
        self.progress_tracker = progress_tracker

    def get_existing_files(self) -> set:
        """Get list of existing documents"""
        existing_files = set()
        if self.raw_dir.exists():
            for file_path in self.raw_dir.glob("*"):
                if file_path.is_file():
                    existing_files.add(file_path.name)
        return existing_files

    def add_documents(self, source_files: list[str], skip_duplicates: bool = True) -> list[Path]:
        """
        Add documents to knowledge base

        Args:
            source_files: List of document files to add
            skip_duplicates: Whether to skip duplicate files (files with same name)

        Returns:
            List of successfully added new file paths
        """
        logger.info(f"Adding documents to knowledge base '{self.kb_name}'...")

        existing_files = self.get_existing_files()
        new_files = []
        skipped_files = []

        for source in source_files:
            source_path = Path(source)
            if not source_path.exists():
                logger.warning(f"  ⚠ Source file does not exist: {source}")
                continue

            # Check if already exists
            if source_path.name in existing_files:
                if skip_duplicates:
                    logger.info(f"  → Skipped (already exists): {source_path.name}")
                    skipped_files.append(source_path.name)
                    continue
                logger.warning(f"  ⚠ Overwriting existing file: {source_path.name}")

            # Copy to raw directory
            dest_path = self.raw_dir / source_path.name
            shutil.copy2(source_path, dest_path)
            new_files.append(dest_path)
            logger.info(f"  ✓ Added: {source_path.name}")

        if skipped_files:
            logger.info(f"\nSkipped {len(skipped_files)} existing files")

        logger.info(f"Successfully added {len(new_files)} new files")
        return new_files

    async def process_new_documents(self, new_files: list[Path]):
        """Process newly added documents. Re-reads config to catch .env changes."""
        if not new_files:
            logger.warning("No new files to process")
            return None

        logger.info(f"\nProcessing {len(new_files)} new documents...")

        self.embedding_cfg = get_embedding_config()
        self.llm_cfg = get_llm_config()

        logger.info(
            f"Using: {self.embedding_cfg.model} "
            f"({self.embedding_cfg.dim}D, {self.embedding_cfg.binding})"
        )

        config = RAGAnythingConfig(
            working_dir=str(self.rag_storage_dir),
            parser="mineru",
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        )

        model = self.llm_cfg.model
        api_key = self.api_key or self.llm_cfg.api_key
        base_url = self.base_url or self.llm_cfg.base_url

        def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return openai_complete_if_cache(
                model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )

        def vision_model_func(
            prompt,
            system_prompt=None,
            history_messages=[],
            image_data=None,
            messages=None,
            **kwargs,
        ):
            if messages:
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["messages", "prompt", "system_prompt", "history_messages"]
                }
                return openai_complete_if_cache(
                    model,
                    prompt="",
                    system_prompt=None,
                    history_messages=[],
                    messages=messages,
                    api_key=api_key,
                    base_url=base_url,
                    **clean_kwargs,
                )
            # Traditional single image format
            if image_data:
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["messages", "prompt", "system_prompt", "history_messages"]
                }
                messages = [
                    msg
                    for msg in [
                        {"role": "system", "content": system_prompt} if system_prompt else None,
                        (
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_data}"
                                        },
                                    },
                                ],
                            }
                            if image_data
                            else {"role": "user", "content": prompt}
                        ),
                    ]
                    if msg is not None
                ]
                return openai_complete_if_cache(
                    model,
                    prompt="",
                    system_prompt=None,
                    history_messages=[],
                    messages=messages,
                    api_key=api_key,
                    base_url=base_url,
                    **clean_kwargs,
                )
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

        # Define embedding function using unified EmbeddingClient
        # Reset client to pick up latest config (including active provider from UI)
        from src.services.embedding import reset_embedding_client

        reset_embedding_client()

        embedding_cfg = get_embedding_config()  # Reload config
        embedding_client = get_embedding_client()  # Get fresh client with new config

        logger.info(
            f"Using embedding: {embedding_cfg.model} "
            f"({embedding_cfg.dim}D, {embedding_cfg.binding})"
        )

        # Create async wrapper compatible with LightRAG's expected signature
        async def unified_embed_func(texts):
            """
            Unified embedding function using EmbeddingClient.
            Supports multiple providers: OpenAI, Cohere, Jina, Ollama, etc.
            """
            try:
                embeddings = await embedding_client.embed(texts)
                return embeddings
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                raise

        embedding_func = EmbeddingFunc(
            embedding_dim=embedding_cfg.dim,
            max_token_size=embedding_cfg.max_tokens,
            func=unified_embed_func,
        )

        # Initialize RAGAnything with existing storage and log forwarding
        with LightRAGLogContext(scene="knowledge_init"):
            rag = RAGAnything(
                config=config,
                llm_model_func=llm_model_func,
                vision_model_func=vision_model_func,
                embedding_func=embedding_func,
            )

            # Ensure LightRAG is initialized (will load existing knowledge base)
            await rag._ensure_lightrag_initialized()
            logger.info("✓ Loaded existing knowledge base")

        # Process each new document
        processed_files = []
        total_files = len(new_files)
        for idx, doc_file in enumerate(new_files, 1):
            logger.info(f"\nProcessing: {doc_file.name}")

            # Update progress
            if self.progress_tracker:
                from src.knowledge.progress_tracker import ProgressStage

                self.progress_tracker.update(
                    ProgressStage.PROCESSING_FILE,
                    f"Processing: {doc_file.name}",
                    current=idx,
                    total=total_files,
                    file_name=doc_file.name,
                )

            try:
                # Use RAGAnything's process_document_complete method with timeout
                logger.info("  → Starting document processing...")
                await asyncio.wait_for(
                    rag.process_document_complete(
                        file_path=str(doc_file),
                        output_dir=str(self.content_list_dir),
                        parse_method="auto",
                    ),
                    timeout=600.0,  # 10 minute timeout
                )
                logger.info(f"  ✓ Successfully processed: {doc_file.name}")
                processed_files.append(doc_file)

                # Content list should be automatically saved
                doc_name = doc_file.stem
                content_list_file = self.content_list_dir / f"{doc_name}.json"
                if content_list_file.exists():
                    logger.info(f"  ✓ Content list saved: {content_list_file.name}")

            except asyncio.TimeoutError:
                logger.error(f"  ✗ Processing timeout for {doc_file.name} (>10 minutes)")
                logger.error("  Possible causes: Large PDF, slow embedding API, network issues")
                if self.progress_tracker:
                    from src.knowledge.progress_tracker import ProgressStage

                    self.progress_tracker.update(
                        ProgressStage.ERROR,
                        f"Timeout processing: {doc_file.name}",
                        current=idx,
                        total=total_files,
                        error="Processing timeout (>10 minutes)",
                    )
            except Exception as e:
                error_message = self._format_exception_message(e)
                logger.error(f"  ✗ Processing failed {doc_file.name}: {error_message}")
                if self.progress_tracker:
                    from src.knowledge.progress_tracker import ProgressStage

                    self.progress_tracker.update(
                        ProgressStage.ERROR,
                        f"Processing failed: {doc_file.name}",
                        current=idx,
                        total=total_files,
                        file_name=doc_file.name,
                        error=error_message,
                    )
                import traceback

                logger.error(traceback.format_exc())

        # Copy extracted images
        rag_images_dir = self.rag_storage_dir / "images"
        if rag_images_dir.exists():
            logger.info("\nCopying extracted images...")
            image_count = 0
            for img_file in rag_images_dir.glob("*"):
                if img_file.is_file():
                    dest = self.images_dir / img_file.name
                    if not dest.exists():
                        shutil.copy2(img_file, dest)
                        image_count += 1
            if image_count > 0:
                logger.info(f"  ✓ Copied {image_count} images")

        # Fix structure
        await self.fix_structure()

        logger.info("\n✓ Document processing completed!")

        return processed_files

    async def fix_structure(self):
        """Fix nested directory structure"""
        logger.info("\nFixing directory structure...")

        # Find nested content lists
        content_list_moves = []
        for doc_dir in self.content_list_dir.glob("*"):
            if not doc_dir.is_dir():
                continue

            auto_dir = doc_dir / "auto"
            if not auto_dir.exists():
                continue

            # Find the _content_list.json file
            for json_file in auto_dir.glob("*_content_list.json"):
                target_file = self.content_list_dir / f"{doc_dir.name}.json"
                content_list_moves.append((json_file, target_file))

        # Move content list files
        for source, target in content_list_moves:
            try:
                shutil.copy2(source, target)
                logger.info(f"  ✓ Moved: {source.name} -> {target.name}")
            except Exception as e:
                logger.error(f"  ✗ Move failed {source.name}: {e!s}")

        # Find and move nested images
        for doc_dir in self.content_list_dir.glob("*"):
            if not doc_dir.is_dir():
                continue

            auto_dir = doc_dir / "auto"
            if not auto_dir.exists():
                continue

            images_dir = auto_dir / "images"
            if images_dir.exists() and images_dir.is_dir():
                image_count = 0
                # Ensure target directory exists
                self.images_dir.mkdir(parents=True, exist_ok=True)

                for img_file in images_dir.glob("*"):
                    if img_file.is_file() and img_file.exists():
                        target_img = self.images_dir / img_file.name
                        if not target_img.exists():
                            try:
                                # Ensure source file exists
                                if not img_file.exists():
                                    logger.warning(f"  ⚠ Source image does not exist: {img_file}")
                                    continue
                                shutil.copy2(img_file, target_img)
                                image_count += 1
                            except FileNotFoundError:
                                logger.error(
                                    f"  ✗ Failed to move image {img_file.name}: Source file does not exist: {img_file}"
                                )
                            except Exception as e:
                                logger.error(f"  ✗ Failed to move image {img_file.name}: {e!s}")

                if image_count > 0:
                    logger.info(f"  ✓ Moved {image_count} images from {doc_dir.name}/auto/images/")

        # Clean up nested directories
        def cleanup_onerror(func, path, excinfo):
            logger.warning(f"Failed to remove {path} during cleanup: {excinfo[1]}")

        for doc_dir in self.content_list_dir.glob("*"):
            if doc_dir.is_dir():
                shutil.rmtree(doc_dir, onerror=cleanup_onerror)
                logger.info(f"  ✓ Cleaned: {doc_dir.name}/")

        logger.info("✓ Directory structure fixed!")

    def extract_numbered_items_for_new_docs(
        self, processed_files: list[Path], batch_size: int = 20
    ):
        """
        Extract numbered items for newly added documents

        Args:
            processed_files: List of newly processed files
            batch_size: Number of items to process per batch
        """
        if not processed_files:
            logger.info("No new files need numbered items extraction")
            return

        logger.info("\n" + "=" * 60)
        logger.info("🔍 Extracting numbered items for new documents...")
        logger.info("=" * 60 + "\n")

        # Use credentials from config as fallback
        api_key = self.api_key or self.llm_cfg.api_key
        base_url = self.base_url or self.llm_cfg.base_url

        output_file = self.kb_dir / "numbered_items.json"

        try:
            for idx, doc_file in enumerate(processed_files, 1):
                doc_name = doc_file.stem
                content_list_file = self.content_list_dir / f"{doc_name}.json"

                if not content_list_file.exists():
                    logger.warning(f"Content list file not found: {content_list_file.name}")
                    continue

                logger.info(
                    f"\nProcessing file [{idx}/{len(processed_files)}]: {content_list_file.name}"
                )

                # Always merge to existing file (if exists)
                merge = output_file.exists()

                process_content_list(
                    content_list_file=content_list_file,
                    output_file=output_file,
                    api_key=api_key,
                    base_url=base_url,
                    batch_size=batch_size,
                    merge=merge,
                )

            logger.info(f"\n{'=' * 60}")
            logger.info("✓ Numbered items extraction complete!")
            logger.info(f"Output file: {output_file}")
            logger.info(f"{'=' * 60}\n")

        except Exception as e:
            error_message = self._format_exception_message(e)
            logger.error(f"\n✗ Numbered items extraction failed: {error_message}")
            if self.progress_tracker:
                from src.knowledge.progress_tracker import ProgressStage

                self.progress_tracker.update(
                    ProgressStage.ERROR,
                    "Numbered items extraction failed",
                    current=len(processed_files),
                    total=len(processed_files),
                    error=error_message,
                )
            import traceback

            logger.error(traceback.format_exc())

    def update_metadata(self, added_count: int):
        """Update knowledge base metadata"""
        metadata_file = self.kb_dir / "metadata.json"

        try:
            if metadata_file.exists():
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            # Update modification time
            metadata["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Record add operation
            if "update_history" not in metadata:
                metadata["update_history"] = []

            metadata["update_history"].append(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "add_documents",
                    "files_added": added_count,
                }
            )

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info("✓ Metadata updated")

        except Exception as e:
            logger.warning(f"Failed to update metadata: {e!s}")

    def _format_exception_message(self, exc: Exception) -> str:
        """Build a human friendly error message, preserving API details when available."""

        def append_unique_message(target: list[str], value: object):
            if not value:
                return
            text = str(value).strip()
            if not text:
                return
            if text not in target:
                target.append(text)

        messages: list[str] = []

        append_unique_message(messages, str(exc))
        # Some exceptions keep a separate message attribute
        message_attr = getattr(exc, "message", None)
        if message_attr is not None:
            append_unique_message(messages, message_attr)

        # OpenAI errors expose structured bodies with detailed messages
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_payload = body.get("error") or body
            if isinstance(error_payload, dict):
                for key in ("message", "detail", "error", "description"):
                    if key in error_payload:
                        append_unique_message(messages, error_payload[key])

        if RateLimitError is not None and isinstance(exc, RateLimitError):
            # Provide a consistent hint for rate limit scenarios
            append_unique_message(messages, "OpenAI API rate limit reached")

        # APIStatusError / APIError may provide response payloads
        if APIStatusError is not None and isinstance(exc, APIStatusError):
            response = getattr(exc, "response", None)
            if response is not None:
                json_loader = getattr(response, "json", None)
                if callable(json_loader):
                    try:
                        data = json_loader()
                    except (json.JSONDecodeError, ValueError) as e:  # best effort only: ignore JSON decoding issues
                        logger.debug(f"Failed to parse JSON from response: {e}")
                        data = None
                else:
                    data = None

                if isinstance(data, dict):
                    error_payload = data.get("error") or data
                    if isinstance(error_payload, dict):
                        for key in ("message", "detail", "error", "description"):
                            if key in error_payload:
                                append_unique_message(messages, error_payload[key])
                else:
                    text = getattr(response, "text", None)
                    if text:
                        append_unique_message(messages, text)

        if APIError is not None and isinstance(exc, APIError):
            append_unique_message(messages, f"OpenAI API error ({exc.__class__.__name__})")

        if not messages:
            append_unique_message(messages, exc.__class__.__name__)

        return " | ".join(messages)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Incrementally add documents to existing knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Add a single document to knowledge base
  python add_documents.py ai_textbook --docs new_chapter.pdf

  # Add multiple documents to knowledge base
  python add_documents.py math2211 --docs chapter1.pdf chapter2.pdf

  # Add documents from directory
  python add_documents.py ai_textbook --docs-dir ./new_materials/

  # Allow overwriting files with same name
  python add_documents.py ai_textbook --docs document.pdf --allow-duplicates

  # Only add files, skip processing (process manually later)
  python add_documents.py ai_textbook --docs file.pdf --skip-processing

  # Skip numbered items extraction
  python add_documents.py ai_textbook --docs file.pdf --skip-extract
        """,
    )

    parser.add_argument("kb_name", help="Knowledge base name")
    parser.add_argument("--docs", nargs="+", help="Document files to add")
    parser.add_argument("--docs-dir", help="Directory containing documents to add")
    parser.add_argument(
        "--base-dir",
        default="./knowledge_bases",
        help="Knowledge base base directory (default: ./knowledge_bases)",
    )
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY"), help="OpenAI API key")
    parser.add_argument("--base-url", default=os.getenv("LLM_HOST"), help="API base URL")
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow overwriting files with same name (default: skip)",
    )
    parser.add_argument(
        "--skip-processing", action="store_true", help="Only add files, skip document processing"
    )
    parser.add_argument(
        "--skip-extract", action="store_true", help="Skip numbered items extraction"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Batch size for numbered items extraction (default: 20)",
    )

    args = parser.parse_args()

    # Check API key
    if not args.skip_processing and not args.api_key:
        logger.error("Error: OpenAI API key required")
        logger.error("Please set LLM_API_KEY environment variable or use --api-key option")
        return

    # Collect document files
    doc_files = []
    if args.docs:
        doc_files.extend(args.docs)

    if args.docs_dir:
        docs_dir = Path(args.docs_dir)
        if docs_dir.exists() and docs_dir.is_dir():
            for ext in ["*.pdf", "*.docx", "*.doc", "*.txt", "*.md"]:
                doc_files.extend([str(f) for f in docs_dir.glob(ext)])
        else:
            logger.error(f"Error: Document directory does not exist: {args.docs_dir}")
            return

    if not doc_files:
        logger.error("Error: No documents specified")
        logger.error("Use --docs or --docs-dir to specify documents to add")
        return

    # Initialize document adder
    try:
        adder = DocumentAdder(
            kb_name=args.kb_name,
            base_dir=args.base_dir,
            api_key=args.api_key,
            base_url=args.base_url,
        )
    except ValueError as e:
        logger.error(f"Error: {e!s}")
        return

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Adding documents to knowledge base: {args.kb_name}")
    logger.info(f"{'=' * 60}\n")

    # Add documents to raw directory
    new_files = adder.add_documents(doc_files, skip_duplicates=not args.allow_duplicates)

    if not new_files:
        logger.info("\nNo new files need processing")
        return

    # Process new documents
    processed_files = []
    if not args.skip_processing:
        processed_files = await adder.process_new_documents(new_files)
    else:
        logger.info("\nSkipping document processing (--skip-processing specified)")
        processed_files = new_files

    # Extract numbered items for new documents
    if not args.skip_processing and not args.skip_extract and processed_files:
        adder.extract_numbered_items_for_new_docs(processed_files, batch_size=args.batch_size)
    elif args.skip_extract:
        logger.info("\nSkipping numbered items extraction (--skip-extract specified)")

    # Update metadata
    adder.update_metadata(len(new_files))

    logger.info(f"\n{'=' * 60}")
    logger.info(
        f"✓ Successfully added {len(new_files)} documents to knowledge base '{args.kb_name}'!"
    )
    logger.info(f"{'=' * 60}\n")


if __name__ == "__main__":
    # Logging configuration is done during module import, no need to configure again here
    asyncio.run(main())
