"""
Text Cleaner Module

Cleans and normalizes extracted text from PDFs while preserving meaning.
This is Step 4 of the RAG pipeline: Text Cleaning & Normalization.
"""

import re
from typing import Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


def clean_text(raw_text: str, preserve_structure: bool = True) -> str:
    """
    Clean and normalize extracted text while preserving meaning.
    
    Args:
        raw_text: Raw extracted text from PDF
        preserve_structure: If True, keep paragraph breaks; if False, more aggressive cleaning
        
    Returns:
        Cleaned and normalized text
    """
    logger.debug(f"Cleaning text: {len(raw_text)} chars, preserve_structure={preserve_structure}")
    if not raw_text:
        logger.warning("Empty text provided for cleaning")
        return ""
    
    text = raw_text
    
    # Step 1: Normalize line breaks and spacing
    text = normalize_whitespace(text, preserve_structure)
    
    # Step 2: Fix common PDF extraction issues
    text = fix_pdf_artifacts(text)
    
    # Step 3: Remove excessive punctuation
    text = clean_punctuation(text)
    
    # Step 4: Final cleanup
    text = text.strip()
    
    logger.info(f"Text cleaned: {len(raw_text)} → {len(text)} chars")
    return text


def normalize_whitespace(text: str, preserve_structure: bool = True) -> str:
    """
    Normalize whitespace while optionally preserving paragraph structure.
    
    Args:
        text: Text to normalize
        preserve_structure: Keep paragraph breaks (double newlines)
        
    Returns:
        Text with normalized whitespace
    """
    if preserve_structure:
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace single newlines with space (join broken lines)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    else:
        # Replace all newlines with space
        text = re.sub(r'\n+', ' ', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Replace tabs with space
    text = text.replace('\t', ' ')
    
    return text


def fix_pdf_artifacts(text: str) -> str:
    """
    Fix common PDF extraction artifacts.
    
    Args:
        text: Text with potential PDF artifacts
        
    Returns:
        Text with artifacts removed/fixed
    """
    # Remove soft hyphens (often appear in PDF extractions)
    text = text.replace('\u00ad', '')
    
    # Fix hyphenated words split across lines (e.g., "manage-\nment" → "management")
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Remove zero-width spaces and other invisible characters
    text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
    
    # Fix common ligatures (æ, œ, etc.) if needed
    # text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    
    return text


def clean_punctuation(text: str) -> str:
    """
    Clean excessive or malformed punctuation.
    
    Args:
        text: Text with potential punctuation issues
        
    Returns:
        Text with cleaned punctuation
    """
    # Replace multiple periods (except ellipsis)
    text = re.sub(r'\.{4,}', '...', text)
    
    # Replace multiple question marks
    text = re.sub(r'\?{2,}', '?', text)
    
    # Replace multiple exclamation marks
    text = re.sub(r'!{2,}', '!', text)
    
    # Fix space before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Fix missing space after punctuation (e.g., "word.Next" → "word. Next")
    text = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', text)
    
    return text


def remove_headers_footers(text: str, header_pattern: Optional[str] = None, 
                           footer_pattern: Optional[str] = None) -> str:
    """
    Remove common headers/footers from text (optional advanced cleaning).
    
    Args:
        text: Text to clean
        header_pattern: Regex pattern for header text
        footer_pattern: Regex pattern for footer text
        
    Returns:
        Text with headers/footers removed
    """
    if header_pattern:
        text = re.sub(header_pattern, '', text, flags=re.IGNORECASE)
    
    if footer_pattern:
        text = re.sub(footer_pattern, '', text, flags=re.IGNORECASE)
    
    return text


def get_text_stats(text: str) -> dict:
    """
    Get statistics about the text for quality checking.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with text statistics
    """
    if not text:
        return {
            'char_count': 0,
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'avg_word_length': 0
        }
    
    words = text.split()
    lines = text.split('\n')
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    
    return {
        'char_count': len(text),
        'word_count': len(words),
        'line_count': len(lines),
        'paragraph_count': len(paragraphs),
        'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0
    }


if __name__ == "__main__":
    # Test the text cleaner
    import sys
    from pathlib import Path
    
    print("\n🧹 Testing Text Cleaner")
    print("=" * 60)
    
    # Test with sample text
    print("\n📝 Test 1: Sample Text with Issues")
    print("-" * 60)
    
    sample_text = """This is a   test    with   multiple    spaces.
And some
broken
lines that   should be  fixed.


Too many

newlines


here.

Word-
break fix test.

missing.Space.here.And.here."""
    
    print("Before cleaning:")
    print(f"  Chars: {len(sample_text)}, Words: {len(sample_text.split())}")
    print(f"  Preview: {sample_text[:100]}...")
    
    cleaned = clean_text(sample_text)
    
    print("\nAfter cleaning:")
    print(f"  Chars: {len(cleaned)}, Words: {len(cleaned.split())}")
    print(f"  Result:\n{cleaned}")
    
    # Test with actual PDF if available
    data_folder = r"c:\chatbot\backend\data\raw_pdfs"
    
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
    
    print(f"\n\n📂 Test 2: Real PDF Cleaning")
    print("-" * 60)
    print(f"Folder: {data_folder}")
    
    try:
        from app.rag.offline.document_loader import load_pdfs_from_folder
        from app.rag.offline.text_extractor import get_full_text_smart
        
        documents = load_pdfs_from_folder(data_folder)
        
        if documents:
            first_doc = documents[0]
            print(f"\n📖 Processing: {first_doc.filename}")
            
            # Extract text
            print("\n  Step 1: Extracting text...")
            raw_text = get_full_text_smart(first_doc.file_path)
            
            # Get stats before cleaning
            before_stats = get_text_stats(raw_text)
            print(f"\n  Before cleaning:")
            print(f"    - Characters: {before_stats['char_count']}")
            print(f"    - Words: {before_stats['word_count']}")
            print(f"    - Paragraphs: {before_stats['paragraph_count']}")
            print(f"    - Avg word length: {before_stats['avg_word_length']:.1f}")
            
            # Clean text
            print(f"\n  Step 2: Cleaning text...")
            cleaned_text = clean_text(raw_text)
            
            # Get stats after cleaning
            after_stats = get_text_stats(cleaned_text)
            print(f"\n  After cleaning:")
            print(f"    - Characters: {after_stats['char_count']}")
            print(f"    - Words: {after_stats['word_count']}")
            print(f"    - Paragraphs: {after_stats['paragraph_count']}")
            print(f"    - Avg word length: {after_stats['avg_word_length']:.1f}")
            
            # Show improvement
            char_reduction = before_stats['char_count'] - after_stats['char_count']
            print(f"\n  ✅ Cleaned: removed {char_reduction} excess characters")
            
            # Preview
            print(f"\n  Preview (first 400 chars):")
            print(f"  {'-' * 55}")
            print(f"  {cleaned_text[:400]}...")
            print(f"  {'-' * 55}")
            
        else:
            print("\n⚠️  No PDF files found. Add PDFs to test cleaning.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
