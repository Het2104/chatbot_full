"""Upload Router

Handles PDF file upload, processing, and management.

Key responsibilities:
1. File upload validation (size, type, security)
2. PDF text extraction (PyPDF2 with OCR fallback)
3. Text processing and chunking
4. Vector embedding generation
5. Storage in Milvus vector database

This powers the RAG (Retrieval Augmented Generation) system.
"""

import os
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.pdf_processing_service import PDFProcessingService
from app.services.minio_storage import get_minio_storage
from app.rag.storage.milvus_store import MilvusVectorStore
from app.logging_config import get_logger
from app.config import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
    ALLOWED_FILE_EXTENSIONS,
    RAW_PDFS_DIR,
)
from app.utils import (
    sanitize_filename,
    add_timestamp_to_filename,
    validate_file_extension,
    ensure_file_deleted,
    invalid_file_type_error,
    file_too_large_error,
    file_not_found_error,
    upload_failed_error,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/upload",
    tags=["upload"]
)


class PDFInfo(BaseModel):
    """Model for PDF file information"""
    filename: str
    size_bytes: int
    size_mb: float
    uploaded_at: float


class PDFListResponse(BaseModel):
    """Response model for listing PDFs"""
    pdfs: List[PDFInfo]
    count: int


class UploadResponse(BaseModel):
    """Response model for PDF upload"""
    success: bool
    message: str
    filename: str
    stats: dict = None
    error: str = None


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file for RAG (Retrieval Augmented Generation).
    
    Processing Pipeline:
    1. Validate file (extension, size)
    2. Save to data/raw_pdfs/
    3. Extract text (PyPDF2 or OCR for scanned PDFs)
    4. Clean and normalize text
    5. Split into overlapping chunks
    6. Generate vector embeddings
    7. Store in Milvus vector database
    
    Request:
        file: PDF file (multipart/form-data)
        
    Returns:
        success: Whether processing succeeded
        message: Human-readable result message
        filename: Sanitized filename that was saved
        stats: Processing statistics (chunks, time, etc.)
        error: Error message if processing failed
        
    Raises:
        400: Invalid file type (not PDF)
        413: File too large (>10MB)
        500: Processing or storage error
        
    Constraints:
    - Maximum file size: 10MB (configurable in config.py)
    - Allowed extensions: .pdf only
    - Duplicate filenames: Old version deleted or timestamp added
    
    Note:
        After successful upload, the PDF content becomes searchable via the
        chat RAG system. Users can ask questions about the document content.
    """
    logger.info(f"Received PDF upload request: {file.filename}")
    
    # ========================================================================
    # STEP 1: Validate File Type
    # ========================================================================
    if not validate_file_extension(file.filename, ALLOWED_FILE_EXTENSIONS):
        logger.warning(f"Invalid file type rejected: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=invalid_file_type_error(file.filename, ALLOWED_FILE_EXTENSIONS)
        )
    
    # ========================================================================
    # STEP 2: Sanitize Filename
    # ========================================================================
    # Sanitize filename (remove special characters for security)
    safe_filename = sanitize_filename(file.filename)
    
    # ========================================================================
    # STEP 3: Handle Duplicate Filenames in MinIO
    # ========================================================================
    # Get MinIO storage instance
    minio_storage = get_minio_storage()
    
    # Check if file already exists in MinIO
    if minio_storage.file_exists(safe_filename):
        logger.info(f"File already exists in MinIO, attempting to delete old version: {safe_filename}")
        
        if not minio_storage.delete_pdf(safe_filename):
            # If deletion fails, add timestamp to avoid overwriting
            logger.warning("Could not delete old file, adding timestamp to new file")
            safe_filename = add_timestamp_to_filename(safe_filename)
            logger.info(f"Using timestamped filename: {safe_filename}")
        else:
            logger.info("Old file deleted successfully from MinIO")
    
    try:
        # ====================================================================
        # STEP 4: Upload File to MinIO
        # ====================================================================
        logger.info(f"Uploading file to MinIO: {safe_filename}")
        
        # Read file contents
        file_contents = await file.read()
        
        # Check file size AFTER reading (actual size, not reported size)
        if len(file_contents) > MAX_FILE_SIZE_BYTES:
            actual_size_mb = len(file_contents) / (1024 * 1024)
            logger.warning(f"File too large: {actual_size_mb:.1f}MB (max: {MAX_FILE_SIZE_MB}MB)")
            raise HTTPException(
                status_code=413,
                detail=file_too_large_error(actual_size_mb, MAX_FILE_SIZE_MB)
            )
        
        # Upload to MinIO
        upload_success = minio_storage.upload_pdf(file_contents, safe_filename)
        
        if not upload_success:
            logger.error(f"Failed to upload file to MinIO: {safe_filename}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )
        
        logger.info(f"File uploaded successfully to MinIO: {len(file_contents)} bytes")
        
        # ====================================================================
        # STEP 5: Process PDF (Extract, Chunk, Embed, Store)
        # ====================================================================
        logger.info(f"Starting PDF processing pipeline for: {safe_filename}")
        pdf_processor = PDFProcessingService()
        processing_result = pdf_processor.process_pdf(safe_filename)
        
        # ====================================================================
        # STEP 6: Handle Success or Failure
        # ====================================================================
        if processing_result["success"]:
            # Processing succeeded
            num_chunks = processing_result['stats']['num_chunks']
            logger.info(f"PDF processing successful: {num_chunks} chunks created")
            
            return UploadResponse(
                success=True,
                message=f"Successfully processed {num_chunks} chunks from {safe_filename}",
                filename=safe_filename,
                stats=processing_result["stats"]
            )
        else:
            # Processing failed - clean up the file from MinIO
            error_message = processing_result['error']
            logger.warning(f"PDF processing failed: {error_message}")
            
            # Delete the file from MinIO to avoid leaving unprocessed PDFs
            minio_storage.delete_pdf(safe_filename)
            logger.info(f"Cleaned up failed upload from MinIO: {safe_filename}")
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF: {error_message}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        # Unexpected error - clean up file from MinIO and return generic error
        logger.error(f"Unexpected upload error: {str(e)}", exc_info=True)
        minio_storage = get_minio_storage()
        minio_storage.delete_pdf(safe_filename)
        
        raise HTTPException(
            status_code=500,
            detail=upload_failed_error(str(e))
        )


@router.get("/pdfs", response_model=PDFListResponse)
async def list_pdfs():
    """
    Get list of all indexed PDF documents from MinIO.
    
    Returns metadata about PDFs that have been uploaded and processed.
    The frontend uses this to display a library of available documents.
    
    Returns:
        pdfs: List of PDF file information:
            - filename: Name of the PDF file
            - size_bytes: File size in bytes
            - size_mb: File size in megabytes (for display)
            - uploaded_at: Unix timestamp of upload time
        count: Total number of indexed PDFs
        
    Raises:
        500: If MinIO access fails
        
    Note:
        This reads from MinIO object storage, not from the vector database.
        It shows what files exist, not what's embedded.
    """
    try:
        minio_storage = get_minio_storage()
        pdf_list = minio_storage.list_pdfs()
        
        pdf_info_list = [
            PDFInfo(
                filename=pdf["filename"],
                size_bytes=pdf["size_bytes"],
                size_mb=pdf["size_mb"],
                uploaded_at=pdf["uploaded_at"] or 0
            )
            for pdf in pdf_list
        ]
        
        return PDFListResponse(
            pdfs=pdf_info_list,
            count=len(pdf_info_list)
        )
    except Exception as e:
        logger.error(f"Failed to list PDFs from MinIO: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list PDFs: {str(e)}"
        )


@router.delete("/pdf/{filename}")
async def delete_pdf(filename: str):
    """
    Delete a PDF file from MinIO and its chunks from Milvus.
    
    This completely removes the document from the system:
    1. Deletes the physical PDF file from MinIO storage
    2. Deletes all associated vector embeddings from Milvus database
    
    Path parameters:
        filename: Name of the PDF file to delete
    
    Returns:
        success: Whether deletion succeeded
        message: Information about what was deleted
        chunks_deleted: Number of chunks removed from Milvus
        
    Raises:
        404: If file doesn't exist
        500: If deletion fails
    """
    minio_storage = get_minio_storage()
    
    # Check if file exists
    if not minio_storage.file_exists(filename):
        logger.warning(f"Attempted to delete non-existent file: {filename}")
        raise HTTPException(
            status_code=404,
            detail=file_not_found_error(filename)
        )
    
    try:
        # Delete chunks from Milvus first
        milvus_store = MilvusVectorStore()
        chunks_deleted = milvus_store.delete_by_source_file(filename)
        logger.info(f"Deleted {chunks_deleted} chunks from Milvus for: {filename}")
        
        # Delete file from MinIO
        delete_success = minio_storage.delete_pdf(filename)
        
        if not delete_success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete file from storage"
            )
        
        logger.info(f"Deleted PDF file from MinIO: {filename}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Deleted {filename} from MinIO and removed {chunks_deleted} chunks from Milvus.",
                "chunks_deleted": chunks_deleted
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete PDF {filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
