"""
Utilities Package

Common utility functions and error messages.
"""

from app.utils.common import (
    sanitize_filename,
    add_timestamp_to_filename,
    get_file_size_mb,
    ensure_file_deleted,
    validate_file_extension,
    format_bytes,
    truncate_text,
    count_readable_words,
)

from app.utils.errors import (
    invalid_file_type_error,
    file_too_large_error,
    file_not_found_error,
    ocr_extraction_failed_error,
    poppler_not_found_error,
    tesseract_not_found_error,
    entity_not_found_error,
    no_active_workflow_error,
    pdf_processing_error,
    upload_failed_error,
    OCR_NOT_INSTALLED_ERROR,
    RAG_UNAVAILABLE_ERROR,
    NO_RELEVANT_DOCS_MESSAGE,
)

__all__ = [
    # Common utilities
    'sanitize_filename',
    'add_timestamp_to_filename',
    'get_file_size_mb',
    'ensure_file_deleted',
    'validate_file_extension',
    'format_bytes',
    'truncate_text',
    'count_readable_words',
    # Error messages
    'invalid_file_type_error',
    'file_too_large_error',
    'file_not_found_error',
    'ocr_extraction_failed_error',
    'poppler_not_found_error',
    'tesseract_not_found_error',
    'entity_not_found_error',
    'no_active_workflow_error',
    'pdf_processing_error',
    'upload_failed_error',
    'OCR_NOT_INSTALLED_ERROR',
    'RAG_UNAVAILABLE_ERROR',
    'NO_RELEVANT_DOCS_MESSAGE',
]
