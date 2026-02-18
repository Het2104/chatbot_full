"""
Text Extractor Module with OCR Support

Extracts text from PDFs using standard extraction (pdfplumber) first,
then applies OCR (pytesseract) for image-based or scanned PDFs.
This is Step 3 of the RAG pipeline: OCR for Scanned Content.
"""

import os
from typing import Dict, Tuple, Optional
import pdfplumber
from pathlib import Path

from app.logging_config import get_logger
from app.config import (
    OCR_DEFAULT_DPI,
    TEXT_SPARSE_MIN_CHARS,
    TEXT_SPARSE_MIN_READABLE_WORDS,
    TEXT_SPARSE_MIN_WORD_LENGTH,
    TEXT_SPARSE_MIN_CHARS_PER_LINE,
    TESSERACT_PATHS,
    POPPLER_PATHS,
)
from app.utils import (
    count_readable_words,
    poppler_not_found_error,
    tesseract_not_found_error,
    OCR_NOT_INSTALLED_ERROR,
)

logger = get_logger(__name__)

# OCR imports (will check availability at runtime)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
    logger.info("OCR libraries imported successfully")
    
    # Set Tesseract path for Windows at module load time
    for path in TESSERACT_PATHS:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract executable found at: {path}")
            break
    else:
        logger.warning("Tesseract executable not found in standard paths, will try system PATH")
    
    # Set Poppler path for Windows (needed by pdf2image)
    POPPLER_PATH = None
    for path in POPPLER_PATHS:
        if os.path.exists(path):
            POPPLER_PATH = path
            logger.info(f"Poppler found at: {path}")
            break
    
    if not POPPLER_PATH:
        logger.warning("Poppler not found in standard paths - PDF to image conversion may fail")
        logger.warning("Download from: https://github.com/oschwartz10612/poppler-windows/releases/")
        
except ImportError as e:
    OCR_AVAILABLE = False
    logger.warning(f"OCR libraries not available: {e}")
    logger.warning("Install with: pip install pytesseract pdf2image Pillow")
    POPPLER_PATH = None


def is_text_sparse(text: str, min_chars: int = TEXT_SPARSE_MIN_CHARS) -> bool:
    """
    Check if extracted text is too sparse (likely a scanned page).
    
    Args:
        text: Extracted text to check
        min_chars: Minimum character threshold
        
    Returns:
        True if text is sparse/empty, False if sufficient text
    """
    if not text:
        return True
    
    # Remove whitespace and count
    clean_text = text.strip().replace(" ", "").replace("\n", "").replace("\t", "")
    
    # Check character count
    if len(clean_text) < min_chars:
        return True
    
    # Check for readable words
    readable_words_count = count_readable_words(text, TEXT_SPARSE_MIN_WORD_LENGTH)
    if readable_words_count < TEXT_SPARSE_MIN_READABLE_WORDS:
        logger.debug(f"Text appears sparse: only {readable_words_count} readable words found")
        return True
    
    # Check text density (characters per line)
    lines = [l for l in text.split('\n') if l.strip()]
    if lines:
        avg_chars_per_line = len(clean_text) / len(lines)
        if avg_chars_per_line < TEXT_SPARSE_MIN_CHARS_PER_LINE:
            logger.debug(f"Text appears sparse: avg {avg_chars_per_line:.1f} chars/line")
            return True
    
    return False


def extract_text_with_fallback(pdf_path: str, page_num: int, dpi: int = OCR_DEFAULT_DPI) -> Tuple[str, str]:
    """
    Extract text from a PDF page, using OCR if standard extraction fails.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (1-indexed)
        dpi: DPI for OCR image conversion (higher = better quality, slower)
        
    Returns:
        Tuple of (extracted_text, method_used)
        method_used can be: 'standard', 'ocr', or 'failed'
    """
    logger.debug(f"Extracting page {page_num} from {Path(pdf_path).name}")
    
    # First try standard extraction with pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num > len(pdf.pages):
                logger.warning(f"Page {page_num} exceeds total pages {len(pdf.pages)}")
                return "", "failed"
            
            page = pdf.pages[page_num - 1]  # Convert to 0-indexed
            text = page.extract_text()
            
            logger.debug(f"Page {page_num}: Standard extraction got {len(text) if text else 0} chars")
            
            # Check if we got enough text
            if text and not is_text_sparse(text):
                logger.debug(f"Page {page_num}: Using standard extraction (sufficient text)")
                return text, "standard"
            
            # Text is sparse or empty, try OCR if available
            if not OCR_AVAILABLE:
                logger.warning(f"Page {page_num}: Text is sparse but OCR not available")
                logger.warning("Install OCR: pip install pytesseract pdf2image Pillow")
                return text if text else "", "standard"
            
            logger.info(f"Page {page_num}: Text sparse/empty (got {len(text) if text else 0} chars), applying OCR...")
            ocr_text = extract_with_ocr(pdf_path, page_num, dpi)
            
            if ocr_text and len(ocr_text.strip()) > 0:
                logger.info(f"Page {page_num}: OCR successful, extracted {len(ocr_text)} chars")
                return ocr_text, "ocr"
            else:
                logger.warning(f"Page {page_num}: OCR returned no text, using standard result")
                return text if text else "", "ocr_failed"
                
    except Exception as e:
        logger.error(f"Error extracting page {page_num}: {e}", exc_info=True)
        return "", "failed"


def extract_with_ocr(pdf_path: str, page_num: int, dpi: int = OCR_DEFAULT_DPI) -> str:
    """
    Extract text using OCR (for scanned/image-based PDFs).
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (1-indexed)
        dpi: DPI for image conversion
        
    Returns:
        Extracted text from OCR
    """
    if not OCR_AVAILABLE:
        logger.error("OCR libraries not installed - cannot perform OCR")
        raise RuntimeError(OCR_NOT_INSTALLED_ERROR)
    
    logger.info(f"🔍 Converting PDF page {page_num} to image at {dpi} DPI...")
    
    try:
        # Convert PDF page to image
        # Use poppler_path if we found it
        convert_kwargs = {
            'pdf_path': pdf_path,
            'dpi': dpi,
            'first_page': page_num,
            'last_page': page_num
        }
        
        if POPPLER_PATH:
            convert_kwargs['poppler_path'] = POPPLER_PATH
            logger.debug(f"Using Poppler from: {POPPLER_PATH}")
        
        images = convert_from_path(**convert_kwargs)
        
        if not images:
            logger.error(f"PDF to image conversion returned no images for page {page_num}")
            return ""
        
        logger.info(f"✅ PDF converted to image, now applying Tesseract OCR...")
        
        # Apply OCR to the image
        text = pytesseract.image_to_string(images[0], lang='eng')
        
        logger.info(f"✅ OCR complete: extracted {len(text)} characters from page {page_num}")
        logger.debug(f"OCR preview: {text[:100]}..." if len(text) > 100 else f"OCR result: {text}")
        
        return text
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ OCR failed for page {page_num}: {error_msg}", exc_info=True)
        
        # Provide helpful error messages
        if "poppler" in error_msg.lower() or "pdfinfo" in error_msg.lower():
            logger.error(poppler_not_found_error())
        elif "tesseract" in error_msg.lower():
            logger.error(tesseract_not_found_error())
        
        return ""


def extract_text_from_pdf_smart(pdf_path: str, use_ocr: bool = True, dpi: int = 300) -> Dict[int, Dict[str, str]]:
    """
    Extract text from all pages of a PDF, automatically using OCR when needed.
    
    Args:
        pdf_path: Path to the PDF file
        use_ocr: Whether to use OCR for sparse pages (if libraries available)
        dpi: DPI for OCR image conversion
        
    Returns:
        Dictionary mapping page number to dict with keys:
        - 'text': extracted text
        - 'method': extraction method used ('standard', 'ocr', 'ocr_failed', 'failed')
    """
    if not os.path.exists(pdf_path):
        raise ValueError(f"PDF file does not exist: {pdf_path}")
    
    logger.info(f"📄 Starting text extraction: {Path(pdf_path).name}")
    logger.info(f"OCR mode: {'enabled' if use_ocr else 'disabled'}, OCR available: {OCR_AVAILABLE}")
    
    pages_data = {}
    ocr_count = 0
    standard_count = 0
    failed_count = 0
    ocr_failed_count = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"📖 Processing {total_pages} page(s)...")
            
            for page_num in range(1, total_pages + 1):
                text, method = extract_text_with_fallback(pdf_path, page_num, dpi)
                
                pages_data[page_num] = {
                    'text': text,
                    'method': method
                }
                
                if method == 'ocr':
                    ocr_count += 1
                elif method == 'standard':
                    standard_count += 1
                elif method == 'ocr_failed':
                    ocr_failed_count += 1
                else:
                    failed_count += 1
        
        # Summary
        total_chars = sum(len(data['text']) for data in pages_data.values())
        logger.info(f"✅ Extraction complete: {total_chars} total characters")
        logger.info(f"   📊 Methods: {standard_count} standard, {ocr_count} OCR, {ocr_failed_count} OCR-failed, {failed_count} failed")
        
        if ocr_count > 0:
            logger.info(f"   🔍 Used OCR on {ocr_count}/{total_pages} page(s)")
        
        if total_chars == 0:
            logger.error("⚠️  No text extracted from any page!")
            if not OCR_AVAILABLE:
                logger.error("   OCR is not available - install: pip install pytesseract pdf2image Pillow")
            elif ocr_failed_count > 0:
                logger.error("   OCR attempted but failed - check Tesseract and Poppler installation")
        
    except Exception as e:
        logger.error(f"❌ Failed to extract text from {pdf_path}: {e}", exc_info=True)
        raise ValueError(f"Failed to extract text from {pdf_path}: {e}")
    
    return pages_data


def get_full_text_smart(pdf_path: str, use_ocr: bool = True) -> str:
    """
    Extract all text from a PDF as a single string, using OCR when needed.
    
    Args:
        pdf_path: Path to the PDF file
        use_ocr: Whether to use OCR for sparse pages
        
    Returns:
        Combined text from all pages
    """
    pages_data = extract_text_from_pdf_smart(pdf_path, use_ocr)
    
    # Combine all page texts
    all_text = []
    for page_num in sorted(pages_data.keys()):
        page_text = pages_data[page_num]['text']
        if page_text.strip():
            all_text.append(page_text)
    
    return "\n\n".join(all_text)


def check_ocr_setup() -> Dict[str, bool]:
    """
    Check if OCR dependencies are properly installed.
    
    Returns:
        Dictionary with setup status for each component
    """
    status = {
        'pytesseract_installed': False,
        'pdf2image_installed': False,
        'tesseract_executable': False,
        'poppler_available': False
    }
    
    # Check Python packages
    try:
        import pytesseract
        import os
        status['pytesseract_installed'] = True
        
        # Try to set Tesseract path before checking
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        
        # Check if Tesseract executable is found
        try:
            pytesseract.get_tesseract_version()
            status['tesseract_executable'] = True
        except Exception as e:
            # Try without explicit path (might be in system PATH)
            pass
    except ImportError:
        pass
    
    try:
        import pdf2image
        status['pdf2image_installed'] = True
        
        # Try to check poppler (will fail if not installed)
        try:
            from pdf2image.exceptions import PDFInfoNotInstalledError
            # This is a basic check - actual usage will reveal if poppler works
            status['poppler_available'] = True  # Assume available if package imported
        except:
            pass
    except ImportError:
        pass
    
    return status


if __name__ == "__main__":
    # Test the text extractor with OCR support
    import sys
    
    print("\n🔍 Testing Text Extractor with OCR Support")
    print("=" * 60)
    
    # Check OCR setup
    print("\n📋 Checking OCR Setup:")
    setup_status = check_ocr_setup()
    for component, installed in setup_status.items():
        icon = "✅" if installed else "❌"
        print(f"  {icon} {component.replace('_', ' ').title()}: {installed}")
    
    if not all(setup_status.values()):
        print("\n⚠️  OCR is not fully set up. See installation guide.")
        print("  Standard text extraction will still work for regular PDFs.")
    
    # Test with PDFs if available
    data_folder = r"c:\chatbot\backend\data\raw_pdfs"
    
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
    
    print(f"\n📂 Folder: {data_folder}")
    
    from app.rag.offline.document_loader import load_pdfs_from_folder
    
    try:
        documents = load_pdfs_from_folder(data_folder)
        
        if documents:
            print(f"\n✅ Found {len(documents)} document(s)\n")
            
            # Test extraction on first document
            if len(documents) > 0:
                first_doc = documents[0]
                print(f"📖 Extracting from: {first_doc.filename}")
                
                # Use smart extraction (with OCR fallback if available)
                text = get_full_text_smart(first_doc.file_path)
                
                print(f"\n  ✅ Total extracted: {len(text)} characters")
                if text:
                    print(f"  Preview (first 300 chars):")
                    print(f"  {'-' * 50}")
                    print(f"  {text[:300]}...")
                    print(f"  {'-' * 50}")
        else:
            print("\n⚠️  No PDF files found. Add PDFs to test extraction.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
