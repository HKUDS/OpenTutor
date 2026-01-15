#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Knowledge Base Initialization Script

This script initializes a new knowledge base from given documents:
1. Creates directory structure
2. Processes documents using RAG-Anything
3. Builds knowledge graph database
4. Extracts images and content lists
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import shutil

from src.logging import get_logger
from src.services.embedding import get_embedding_config
from src.services.llm import get_llm_config
from src.services.rag.service import RAGService

logger = get_logger("KnowledgeInit")

# Import numbered items extraction functionality
from src.knowledge.extract_numbered_items import process_content_list
from src.knowledge.progress_tracker import ProgressStage, ProgressTracker


class KnowledgeBaseInitializer:
    """Knowledge base initializer"""

    def __init__(
        self,
        kb_name: str,
        base_dir="./data/knowledge_bases",
        api_key: str | None = None,
        base_url: str | None = None,
        progress_tracker: ProgressTracker | None = None,
        rag_provider: str | None = None,
    ):
        self.kb_name = kb_name
        self.base_dir = Path(base_dir)
        self.kb_dir = self.base_dir / kb_name

        # Directory structure
        self.raw_dir = self.kb_dir / "raw"
        self.images_dir = self.kb_dir / "images"
        self.rag_storage_dir = self.kb_dir / "rag_storage"
        self.content_list_dir = self.kb_dir / "content_list"

        self.api_key = api_key
        self.base_url = base_url
        self.embedding_cfg = get_embedding_config()
        self.progress_tracker = progress_tracker or ProgressTracker(kb_name, self.base_dir)
        self.rag_provider = rag_provider

    def _register_to_config(self):
        """Register KB to kb_config.json (only knowledge_bases list, no default)."""
        config_file = self.base_dir / "kb_config.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read config: {e}, creating new")
                config = {"knowledge_bases": {}}
        else:
            config = {"knowledge_bases": {}}

        if "knowledge_bases" not in config:
            config["knowledge_bases"] = {}

        # Remove old "default" field if exists (migration)
        if "default" in config:
            del config["default"]

        if self.kb_name not in config.get("knowledge_bases", {}):
            config["knowledge_bases"][self.kb_name] = {
                "path": self.kb_name,
                "description": f"Knowledge base: {self.kb_name}",
            }

            try:
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config, indent=2, ensure_ascii=False, fp=f)
                logger.info("  ✓ Registered to kb_config.json")
            except Exception as e:
                logger.warning(f"Failed to update config: {e}")
        else:
            logger.info("  ✓ Already registered in kb_config.json")

    def _update_metadata_with_provider(self, provider: str):
        """Update metadata.json and centralized config with the RAG provider used."""
        metadata_file = self.kb_dir / "metadata.json"
        try:
            if metadata_file.exists():
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            metadata["rag_provider"] = provider
            metadata["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, indent=2, ensure_ascii=False, fp=f)

            logger.info(f"  ✓ Updated metadata with RAG provider: {provider}")

            # Also save to centralized config file
            try:
                from src.services.config import get_kb_config_service

                kb_config_service = get_kb_config_service()
                kb_config_service.set_rag_provider(self.kb_name, provider)
                logger.info("  ✓ Saved RAG provider to centralized config")
            except Exception as config_err:
                logger.warning(f"Failed to save to centralized config: {config_err}")

        except Exception as e:
            logger.warning(f"Failed to update metadata with provider: {e}")

    def create_directory_structure(self):
        """Create knowledge base directory structure"""
        logger.info(f"Creating directory structure for knowledge base: {self.kb_name}")

        for dir_path in [
            self.raw_dir,
            self.images_dir,
            self.rag_storage_dir,
            self.content_list_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"  ✓ Created: {dir_path}")

        # Create metadata file
        metadata = {
            "name": self.kb_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Knowledge base: {self.kb_name}",
            "version": "1.0",
            "rag_provider": None,  # Will be set during document processing
        }

        metadata_file = self.kb_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, indent=2, ensure_ascii=False, fp=f)

        logger.info(f"  ✓ Created metadata file: {metadata_file}")

        # Automatically register to kb_config.json
        self._register_to_config()

    def copy_documents(self, source_files: list[str]):
        """Copy documents to raw directory"""
        logger.info(f"Copying {len(source_files)} documents to {self.raw_dir}")

        copied_files = []
        for source in source_files:
            source_path = Path(source)
            if not source_path.exists():
                logger.warning(f"  ⚠ Source file not found: {source}")
                continue

            dest_path = self.raw_dir / source_path.name
            shutil.copy2(source_path, dest_path)
            copied_files.append(str(dest_path))
            logger.info(f"  ✓ Copied: {source_path.name}")

        return copied_files

    async def process_documents(self):
        """Process documents using RAGService with dynamic provider selection"""
        # Use the provider passed during initialization, or fallback to env var
        provider = self.rag_provider or os.getenv("RAG_PROVIDER", "raganything")
        logger.info(f"Processing documents with RAG provider: {provider}")

        self.progress_tracker.update(
            ProgressStage.PROCESSING_DOCUMENTS,
            f"Starting to process documents with {provider} provider...",
            current=0,
            total=0,
        )

        # Get all documents in raw directory
        doc_files = []
        for ext in ["*.pdf", "*.docx", "*.doc", "*.txt", "*.md"]:
            doc_files.extend(list(self.raw_dir.glob(ext)))

        if not doc_files:
            logger.warning("No documents found to process")
            self.progress_tracker.update(
                ProgressStage.ERROR, "No documents found to process", error="No documents found"
            )
            return

        logger.info(f"Found {len(doc_files)} document(s) to process")
        self.progress_tracker.update(
            ProgressStage.PROCESSING_DOCUMENTS,
            f"Found {len(doc_files)} documents, starting to process...",
            current=0,
            total=len(doc_files),
        )

        # Initialize RAGService with the selected provider
        rag_service = RAGService(
            kb_base_dir=str(
                self.base_dir
            ),  # Base directory for all KBs (e.g., data/knowledge_bases)
            provider=provider,
        )

        # Convert Path objects to strings for file paths
        file_paths = [str(doc_file) for doc_file in doc_files]

        try:
            # Process all documents using the RAGService
            success = await rag_service.initialize(
                kb_name=self.kb_name,
                file_paths=file_paths,
                extract_numbered_items=True,  # Enable numbered items extraction
            )

            if success:
                logger.info("✓ Document processing completed!")

                # Update metadata with the RAG provider used
                self._update_metadata_with_provider(provider)

                self.progress_tracker.update(
                    ProgressStage.PROCESSING_DOCUMENTS,
                    "Documents processed successfully",
                    current=len(doc_files),
                    total=len(doc_files),
                )
            else:
                logger.error("Document processing failed")
                self.progress_tracker.update(
                    ProgressStage.ERROR,
                    "Document processing failed",
                    error="RAG pipeline returned failure",
                )

        except asyncio.TimeoutError:
            error_msg = "Processing timeout (>10 minutes)"
            logger.error("✗ Timeout processing documents")
            logger.error("Possible causes: Large files, slow embedding API, network issues")
            self.progress_tracker.update(
                ProgressStage.ERROR,
                "Timeout processing documents",
                error=error_msg,
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"✗ Error processing documents: {error_msg}")
            import traceback

            logger.error(traceback.format_exc())
            self.progress_tracker.update(
                ProgressStage.ERROR,
                "Failed to process documents",
                error=error_msg,
            )

        # Fix structure: flatten nested content_list directories (for RAGAnything compatibility)
        await self.fix_structure()

        # Display statistics
        await self.display_statistics_generic()

    async def fix_structure(self):
        """
        Fix the nested structure created by process_document_complete.
        Flattens content_list directories and moves images to the correct location.
        """
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
                logger.error(f"  ✗ Error moving {source.name}: {e!s}")

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
                                    logger.warning(f"  ⚠ Source image not found: {img_file}")
                                    continue
                                shutil.copy2(img_file, target_img)
                                image_count += 1
                            except FileNotFoundError:
                                logger.error(
                                    f"  ✗ Error moving image {img_file.name}: Source file not found: {img_file}"
                                )
                            except Exception as e:
                                logger.error(f"  ✗ Error moving image {img_file.name}: {e!s}")

                if image_count > 0:
                    logger.info(f"  ✓ Moved {image_count} images from {doc_dir.name}/auto/images/")

        # Clean up nested directories
        for doc_dir in self.content_list_dir.glob("*"):
            if doc_dir.is_dir():
                try:
                    shutil.rmtree(doc_dir)
                    logger.info(f"  ✓ Cleaned up: {doc_dir.name}/")
                except Exception as e:
                    logger.error(f"  ✗ Error removing {doc_dir.name}: {e!s}")

        logger.info("✓ Structure fixed!")

    def extract_numbered_items(self, batch_size: int = 20):
        """
        Extract numbered items from knowledge base (Definition, Proposition, Equation, Figure, etc.)

        Args:
            batch_size: Number of items to process per batch
        """
        logger.info("\n" + "=" * 60)
        logger.info("🔍 Starting to extract numbered items...")
        logger.info("=" * 60 + "\n")

        self.progress_tracker.update(
            ProgressStage.EXTRACTING_ITEMS,
            "Starting to extract numbered items...",
            current=0,
            total=0,
        )

        # Get LLM config for credentials
        llm_cfg = get_llm_config()
        api_key = self.api_key or llm_cfg.api_key
        base_url = self.base_url or llm_cfg.base_url

        output_file = self.kb_dir / "numbered_items.json"
        content_list_files = sorted(self.content_list_dir.glob("*.json"))

        if not content_list_files:
            logger.warning("No content_list files found, skipping numbered items extraction")
            return

        logger.info(f"Found {len(content_list_files)} content_list files")
        self.progress_tracker.update(
            ProgressStage.EXTRACTING_ITEMS,
            f"Found {len(content_list_files)} files, starting extraction...",
            current=0,
            total=len(content_list_files),
        )

        try:
            # Process all content_list files
            for idx, content_list_file in enumerate(content_list_files, 1):
                logger.info(
                    f"\nProcessing file [{idx}/{len(content_list_files)}]: {content_list_file.name}"
                )
                self.progress_tracker.update(
                    ProgressStage.EXTRACTING_ITEMS,
                    f"Extracting: {content_list_file.name}",
                    current=idx,
                    total=len(content_list_files),
                    file_name=content_list_file.name,
                )

                # First file doesn't merge (creates new file), subsequent files merge into existing results
                merge = idx > 1

                process_content_list(
                    content_list_file=content_list_file,
                    output_file=output_file,
                    api_key=api_key,
                    base_url=base_url,
                    batch_size=batch_size,
                    merge=merge,
                )

            logger.info(f"\n{'=' * 60}")
            logger.info("✓ Numbered items extraction completed!")
            logger.info(f"Output file: {output_file}")
            logger.info(f"{'=' * 60}\n")

            self.progress_tracker.update(
                ProgressStage.COMPLETED,
                "Knowledge base initialization completed!",
                current=len(content_list_files),
                total=len(content_list_files),
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"\n✗ Numbered items extraction failed: {error_msg}")
            import traceback

            traceback.print_exc()
            self.progress_tracker.update(
                ProgressStage.ERROR, "Numbered items extraction failed", error=error_msg
            )

    async def display_statistics(self, rag):
        """Display knowledge base statistics (legacy - for RAGAnything)"""
        await self.display_statistics_generic()

    async def display_statistics_generic(self):
        """Display knowledge base statistics (provider-agnostic)"""
        logger.info("\n" + "=" * 50)
        logger.info("Knowledge Base Statistics")
        logger.info("=" * 50)

        # Count files
        raw_files = list(self.raw_dir.glob("*"))
        image_files = list(self.images_dir.glob("*"))
        content_files = list(self.content_list_dir.glob("*.json"))

        logger.info(f"Raw documents: {len(raw_files)}")
        logger.info(f"Extracted images: {len(image_files)}")
        logger.info(f"Content lists: {len(content_files)}")

        # Read provider from metadata instead of env var
        provider = self.rag_provider or os.getenv("RAG_PROVIDER", "raganything")

        # Try to read from metadata.json if available
        metadata_file = self.kb_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)
                    if "rag_provider" in metadata and metadata["rag_provider"]:
                        provider = metadata["rag_provider"]
            except Exception:
                pass

        # RAGAnything/LightRAG format
        entities_file = self.rag_storage_dir / "kv_store_full_entities.json"
        relations_file = self.rag_storage_dir / "kv_store_full_relations.json"
        chunks_file = self.rag_storage_dir / "kv_store_text_chunks.json"

        # LlamaIndex format
        vector_store_dir = self.base_dir / self.kb_name / "vector_store"

        try:
            if entities_file.exists():
                with open(entities_file, encoding="utf-8") as f:
                    entities = json.load(f)
                    logger.info(f"Knowledge entities: {len(entities)}")

            if relations_file.exists():
                with open(relations_file, encoding="utf-8") as f:
                    relations = json.load(f)
                    logger.info(f"Knowledge relations: {len(relations)}")

            if chunks_file.exists():
                with open(chunks_file, encoding="utf-8") as f:
                    chunks = json.load(f)
                    logger.info(f"Text chunks: {len(chunks)}")

            if vector_store_dir.exists():
                metadata_file = vector_store_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, encoding="utf-8") as f:
                        metadata = json.load(f)
                        logger.info(f"Vector embeddings: {metadata.get('num_embeddings', 0)}")
                        logger.info(f"Embedding dimension: {metadata.get('dimension', 0)}")
        except Exception as e:
            logger.warning(f"Could not retrieve statistics: {e!s}")

        logger.info(f"Provider used: {provider}")
        logger.info("=" * 50)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Initialize a new knowledge base from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Initialize new knowledge base from documents (with auto extraction)
  python init_knowledge_base.py my_kb --docs document1.pdf document2.pdf

  # Initialize from a directory
  python init_knowledge_base.py my_kb --docs-dir ./my_documents/

  # Initialize without numbered items extraction
  python init_knowledge_base.py my_kb --docs document.pdf --skip-extract

  # Adjust batch size for extraction (for large knowledge bases)
  python init_knowledge_base.py my_kb --docs document.pdf --batch-size 30
        """,
    )

    parser.add_argument("name", help="Knowledge base name")
    parser.add_argument("--docs", nargs="+", help="Document files to process")
    parser.add_argument("--docs-dir", help="Directory containing documents to process")
    parser.add_argument(
        "--base-dir",
        default="./knowledge_bases",
        help="Base directory for knowledge bases (default: ./knowledge_bases)",
    )
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY"), help="OpenAI API key")
    parser.add_argument("--base-url", default=os.getenv("LLM_HOST"), help="API base URL")
    parser.add_argument(
        "--skip-processing",
        action="store_true",
        help="Skip document processing (only create structure)",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip numbered items extraction after initialization",
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
        logger.error("Set LLM_API_KEY environment variable or use --api-key option")
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
            logger.error(f"Error: Documents directory not found: {args.docs_dir}")
            return

    if not args.skip_processing and not doc_files:
        logger.error("Error: No documents specified")
        logger.error("Use --docs or --docs-dir to specify documents")
        return

    # Initialize knowledge base
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Initializing Knowledge Base: {args.name}")
    logger.info(f"{'=' * 60}\n")

    initializer = KnowledgeBaseInitializer(
        kb_name=args.name, base_dir=args.base_dir, api_key=args.api_key, base_url=args.base_url
    )

    # Create directory structure
    initializer.create_directory_structure()

    # Copy documents
    if doc_files:
        copied_files = initializer.copy_documents(doc_files)
        logger.info(f"\nCopied {len(copied_files)} file(s) to raw directory")

    # Process documents
    if not args.skip_processing:
        await initializer.process_documents()
    else:
        logger.info("\nSkipping document processing (--skip-processing specified)")

    # Extract numbered items (automatically after processing)
    if not args.skip_processing and not args.skip_extract:
        initializer.extract_numbered_items(batch_size=args.batch_size)
    elif args.skip_extract:
        logger.info("\nSkipping numbered items extraction (--skip-extract specified)")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"✓ Knowledge base '{args.name}' initialized successfully!")
    logger.info(f"Location: {initializer.kb_dir}")
    logger.info(f"{'=' * 60}\n")


if __name__ == "__main__":
    # Logging configuration already completed during module import, no need to configure again here
    asyncio.run(main())
