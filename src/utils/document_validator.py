#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Document Validator - Validation utilities for document uploads
"""

import os


class DocumentValidator:
    """Document validation utilities"""

    # Maximum file size in bytes (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        ".pdf",
        ".txt",
        ".md",
        ".doc",
        ".docx",
        ".rtf",
        ".html",
        ".htm",
        ".xml",
        ".json",
        ".csv",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
    }

    @staticmethod
    def validate_upload_safety(filename: str, file_size: int) -> None:
        """
        Validate file upload safety

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Raises:
            ValueError: If validation fails
        """
        # Check file size
        if file_size > DocumentValidator.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes. Maximum allowed: {DocumentValidator.MAX_FILE_SIZE} bytes"
            )

        # Check file extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in DocumentValidator.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {ext}. Allowed types: {', '.join(DocumentValidator.ALLOWED_EXTENSIONS)}"
            )

    @staticmethod
    def get_file_info(filename: str, file_size: int) -> dict:
        """
        Get file information

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Returns:
            Dictionary with file information
        """
        _, ext = os.path.splitext(filename.lower())
        return {
            "filename": filename,
            "extension": ext,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "is_allowed": ext in DocumentValidator.ALLOWED_EXTENSIONS,
        }
