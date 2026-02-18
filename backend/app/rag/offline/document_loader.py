"""
Document Loader Module

Loads PDF documents from a specified directory and extracts basic metadata.
This is Step 2 of the RAG pipeline: Document Ingestion.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import pdfplumber

from app.logging_config import get_logger

logger = get_logger(__name__)

class DocumentInfo:
    """Represents a single document with its metadata"""
    
    def __init__(self, file_path: str, filename: str, page_count: int = 0):
        self.file_path = file_path
        self.filename = filename
        self.page_count = page_count
        self.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    
    def __repr__(self):
        return f"DocumentInfo(filename='{self.filename}', pages={self.page_count}, size={self.file_size} bytes)"


def load_pdfs_from_folder(folder_path: str) -> List[DocumentInfo]:
    """
    Load all PDF files from the specified folder and return document info.
    
    Args:
        folder_path: Path to the folder containing PDF files
        
    Returns:
        List of DocumentInfo objects for each PDF found
        
    Raises:
        ValueError: If folder doesn't exist
    """
    logger.info(f"Loading PDFs from folder: {folder_path}")
    folder = Path(folder_path)
    
    if not folder.exists():
        logger.warning(f"Folder does not exist: {folder_path}")
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    if not folder.is_dir():
        logger.warning(f"Path is not a directory: {folder_path}")
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    documents = []
    
    # Find all PDF files
    pdf_files = list(folder.glob("*.pdf")) + list(folder.glob("*.PDF"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {folder_path}")
        return documents
    
    logger.info(f"Found {len(pdf_files)} PDF file(s)")
    
    for pdf_file in pdf_files:
        try:
            # Get page count using pdfplumber
            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
            
            doc_info = DocumentInfo(
                file_path=str(pdf_file),
                filename=pdf_file.name,
                page_count=page_count
            )
            
            documents.append(doc_info)
            logger.info(f"Loaded: {doc_info.filename} ({doc_info.page_count} pages)")
            
        except Exception as e:
            logger.warning(f"Error loading {pdf_file.name}: {e}")
    
    return documents


def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
    """
    Extract text from a PDF file page by page.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary mapping page number (1-indexed) to extracted text
        
    Raises:
        ValueError: If file doesn't exist or can't be read
    """
    logger.debug(f"Extracting text from: {pdf_path}")
    if not os.path.exists(pdf_path):
        logger.warning(f"PDF file does not exist: {pdf_path}")
        raise ValueError(f"PDF file does not exist: {pdf_path}")
    
    pages_text = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    # Store text even if empty (will be handled by OCR in Step 3)
                    pages_text[page_num] = text if text else ""
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")
                    pages_text[page_num] = ""
        
        total_chars = sum(len(text) for text in pages_text.values())
        logger.info(f"Extracted {len(pages_text)} pages, {total_chars} characters")
        
    except Exception as e:
        logger.error(f"Failed to extract text: {e}", exc_info=True)
        raise ValueError(f"Failed to extract text from {pdf_path}: {e}")
    
    return pages_text


def get_full_text(pdf_path: str) -> str:
    """
    Extract all text from a PDF as a single string.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Combined text from all pages
    """
    pages_text = extract_text_from_pdf(pdf_path)
    return "\n\n".join(pages_text.values())


if __name__ == "__main__":
    # Test the document loader
    import sys
    
    # Default to the raw_pdfs folder
    data_folder = r"c:\chatbot\backend\data\raw_pdfs"
    
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
    
    print(f"\n🔍 Testing Document Loader")
    print(f"📂 Folder: {data_folder}\n")
    
    try:
        # Load all PDFs
        documents = load_pdfs_from_folder(data_folder)
        
        if documents:
            print(f"\n✅ Successfully loaded {len(documents)} document(s)")
            
            # Try extracting text from first document
            if len(documents) > 0:
                first_doc = documents[0]
                print(f"\n📖 Extracting text from: {first_doc.filename}")
                text = get_full_text(first_doc.file_path)
                print(f"  ✅ Extracted {len(text)} characters")
                print(f"  Preview: {text[:200]}...")
        else:
            print("\n⚠️  No documents to process")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
