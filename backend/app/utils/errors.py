"""
Error Messages Module

Centralizes all error messages and provides consistent error formatting.
"""

from typing import Optional


# ============================================================================
# File Upload Errors
# ============================================================================

def invalid_file_type_error(filename: str, allowed_types: list) -> str:
    """Generate error message for invalid file type."""
    types_str = ", ".join(allowed_types)
    return f"Invalid file type '{filename}'. Only {types_str} files are allowed"


def file_too_large_error(size_mb: float, max_size_mb: int) -> str:
    """Generate error message for file too large."""
    return f"File too large ({size_mb:.1f}MB). Maximum size is {max_size_mb}MB"


def file_not_found_error(filename: str) -> str:
    """Generate error message for file not found."""
    return f"File '{filename}' not found"


# ============================================================================
# OCR Errors
# ============================================================================

OCR_NOT_INSTALLED_ERROR = """
OCR libraries are not installed. To enable OCR for scanned PDFs:

1. Install Python packages:
   pip install pytesseract pdf2image Pillow

2. Install Tesseract OCR:
   Download from: https://github.com/UB-Mannheim/tesseract/wiki
   Install to: C:\\Program Files\\Tesseract-OCR

3. Install Poppler:
   Download from: https://github.com/oschwartz10612/poppler-windows/releases/
   Extract to: C:\\poppler
"""


def ocr_extraction_failed_error(has_ocr: bool) -> str:
    """Generate error message for OCR extraction failure."""
    if not has_ocr:
        return (
            "Failed to extract text from PDF. Possible reasons:\n"
            "  - PDF is scanned/image-based (OCR not available)\n"
            "  - PDF is encrypted or password-protected\n"
            "  - PDF is corrupted\n\n"
            + OCR_NOT_INSTALLED_ERROR
        )
    else:
        return (
            "Failed to extract text from PDF even with OCR. Possible reasons:\n"
            "  - PDF is encrypted or password-protected\n"
            "  - PDF is corrupted\n"
            "  - PDF contains no readable content"
        )


def poppler_not_found_error() -> str:
    """Generate error message for missing Poppler."""
    return (
        "Poppler not found! OCR requires Poppler for PDF to image conversion.\n"
        "Download from: https://github.com/oschwartz10612/poppler-windows/releases/\n"
        "Extract and add to PATH or place in C:\\poppler"
    )


def tesseract_not_found_error() -> str:
    """Generate error message for missing Tesseract."""
    return (
        "Tesseract not found! OCR requires Tesseract for text recognition.\n"
        "Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "Install to default location: C:\\Program Files\\Tesseract-OCR"
    )


# ============================================================================
# Database Errors
# ============================================================================

def entity_not_found_error(entity_type: str, entity_id: int) -> str:
    """Generate error message for entity not found."""
    return f"{entity_type} with ID {entity_id} not found"


def no_active_workflow_error(chatbot_id: int) -> str:
    """Generate error message for no active workflow."""
    return f"No active workflow found for chatbot {chatbot_id}"


# ============================================================================
# RAG Errors
# ============================================================================

RAG_UNAVAILABLE_ERROR = "RAG system is currently unavailable. Please check Milvus and Groq configuration."

NO_RELEVANT_DOCS_MESSAGE = "I don't know based on the provided documents."


# ============================================================================
# Processing Errors
# ============================================================================

def pdf_processing_error(error_detail: str) -> str:
    """Generate error message for PDF processing failure."""
    return f"Failed to process PDF: {error_detail}"


def upload_failed_error(error_detail: str) -> str:
    """Generate error message for upload failure."""
    return f"Upload failed: {error_detail}"
