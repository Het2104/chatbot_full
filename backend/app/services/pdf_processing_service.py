"""
PDF Processing Service
Handles automatic processing of uploaded PDFs into the RAG system
Supports OCR for scanned/image-based PDFs
Reads PDFs from MinIO object storage
"""
import io
import os
import tempfile
import time
from typing import Dict, Any

from app.rag.offline.text_extractor import get_full_text_smart
from app.rag.offline.text_cleaner import clean_text
from app.rag.offline.chunker import chunk_document
from app.services.minio_storage import get_minio_storage
from app.logging_config import get_logger
from app.utils import ocr_extraction_failed_error

logger = get_logger(__name__)
# Lazy imports for heavy dependencies - moved to process_pdf method
# from app.rag.offline.embedder import Embedder
# from app.rag.storage.milvus_store import MilvusVectorStore


class PDFProcessingService:
    """Service for processing PDFs and adding them to the vector store"""
    
    def __init__(self):
        self.embedder = None
        self.vector_store = None
    
    def process_pdf(self, filename: str) -> Dict[str, Any]:
        """
        Process a single PDF file from MinIO and add to vector store
        Uses OCR automatically for scanned/image-based PDFs
        
        Args:
            filename: Name of the PDF file in MinIO
            
        Returns:
            Dictionary with processing statistics
        """
        start_time = time.time()
        logger.info(f"Starting PDF processing: {filename}")
        
        temp_file_path = None
        
        try:
            # Get MinIO storage instance
            minio_storage = get_minio_storage()
            
            # Download PDF from MinIO
            logger.debug(f"Downloading PDF from MinIO: {filename}")
            pdf_data = minio_storage.download_pdf(filename)
            
            if pdf_data is None:
                raise ValueError(f"Failed to download PDF from MinIO: {filename}")
            
            logger.debug(f"Downloaded {len(pdf_data)} bytes from MinIO")
            
            # Create temporary file for processing
            # (text_extractor requires file path for OCR support)
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_data)
                temp_file_path = temp_file.name
            
            logger.debug(f"Saved to temporary file: {temp_file_path}")
        
            # Lazy import heavy dependencies only when actually processing
            if self.embedder is None:
                logger.debug("Initializing embedder...")
                from app.rag.offline.embedder import Embedder
                self.embedder = Embedder()
            if self.vector_store is None:
                logger.debug("Initializing vector store...")
                from app.rag.storage.milvus_store import MilvusVectorStore
                self.vector_store = MilvusVectorStore(collection_name='rag_chunks')
            
            # Step 1: Extract text from PDF (with automatic OCR for scanned PDFs)
            logger.info("Step 1: Extracting text from PDF...")
            
            # Use temporary file for text extraction (supports OCR)
            text = get_full_text_smart(temp_file_path, use_ocr=True)
            text_length = len(text.strip())
            
            # Check if we got any text at all
            if text_length == 0:
                logger.warning("No text extracted from PDF - may be scanned/encrypted")
                # Check if OCR is available
                from app.rag.offline.text_extractor import OCR_AVAILABLE
                raise ValueError(ocr_extraction_failed_error(OCR_AVAILABLE))
            
            # If very little text, might be scanned - but we'll try to work with it
            if text_length < 50:
                logger.warning(f"Very little text extracted ({text_length} chars) - PDF might be scanned/image-based")
            else:
                logger.info(f"Extracted {text_length} characters")
            
            # Warn if very little text (but continue processing)
            if text_length < 100 and text_length > 0:
                logger.warning(f"Very little text extracted ({text_length} chars)")
            
            # Step 2: Clean text
            logger.info("Step 2: Cleaning text...")
            cleaned = clean_text(text)
            cleaned_length = len(cleaned)
            
            logger.info(f"Cleaned to {cleaned_length} characters")
            
            if not cleaned or cleaned_length < 10:
                logger.warning(f"Text too short after cleaning: {text_length} -> {cleaned_length} chars")
                raise ValueError(
                    f"Text became too short after cleaning (from {text_length} to {cleaned_length} chars). "
                    "PDF may contain only special characters, symbols, or formatting."
                )
            
            # Step 3: Chunk document
            logger.info("Step 3: Creating chunks...")
            chunks = chunk_document(cleaned, filename)
            num_chunks = len(chunks)
            
            logger.info(f"Created {num_chunks} chunks")
            
            if num_chunks == 0:
                logger.warning(f"No chunks created - text length: {cleaned_length} chars")
                raise ValueError(
                    f"No chunks created from document. Text length: {cleaned_length} chars. "
                    "Document may be too short or fragmented. Minimum chunk size is 50 characters."
                )
            
            # Step 4: Generate embeddings
            logger.info("Step 4: Generating embeddings...")
            embeddings = self.embedder.embed_chunks(chunks, show_progress=False)
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # Step 5: Store in Milvus
            logger.info("Step 5: Storing in vector database...")
            self.vector_store.add_chunks(chunks, embeddings)
            logger.info("Stored in Milvus successfully")
            
            # Calculate processing time
            processing_time = round(time.time() - start_time, 2)
            
            logger.info(f"Processing complete: {num_chunks} chunks in {processing_time}s")
            
            return {
                "success": True,
                "filename": filename,
                "stats": {
                    "text_length": text_length,
                    "cleaned_length": cleaned_length,
                    "num_chunks": num_chunks,
                    "processing_time_seconds": processing_time
                }
            }
            
        except Exception as e:
            processing_time = round(time.time() - start_time, 2)
            error_msg = str(e)
            logger.error(f"Processing failed: {error_msg}", exc_info=True)
            
            return {
                "success": False,
                "filename": filename,
                "error": error_msg,
                "processing_time_seconds": processing_time
            }
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.debug(f"Deleted temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")
