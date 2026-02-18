"""
Text Chunker Module

Splits cleaned text into overlapping chunks using sentence-based strategy.
This is Step 5 of the RAG pipeline: Text Chunking.

Uses pure Python (no tiktoken) with sentence boundaries and character limits.
"""

import re
from typing import List, Dict

from app.logging_config import get_logger

logger = get_logger(__name__)

class TextChunk:
    """Represents a single text chunk with metadata"""
    
    def __init__(self, text: str, chunk_id: int, source_file: str = "", 
                 start_char: int = 0, end_char: int = 0):
        self.text = text
        self.chunk_id = chunk_id
        self.source_file = source_file
        self.start_char = start_char
        self.end_char = end_char
        self.char_count = len(text)
        self.word_count = len(text.split())
    
    def __repr__(self):
        return f"TextChunk(id={self.chunk_id}, chars={self.char_count}, words={self.word_count})"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'source_file': self.source_file,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'char_count': self.char_count,
            'word_count': self.word_count
        }


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences
    """
    # Split on sentence endings (. ! ?) followed by whitespace
    # This regex handles common cases like "Dr." and "Mr."
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    # Filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def chunk_text(text: str, 
               max_chars: int = 2000, 
               overlap_sentences: int = 3,
               min_chunk_chars: int = 100) -> List[TextChunk]:
    """
    Split text into overlapping chunks using SENTENCE-BASED strategy.
    
    Strategy:
    - Split by sentences first
    - Group sentences until max_chars (CHARACTER limit) is reached
    - Keep overlap_sentences (SENTENCE count) from previous chunk for context
    
    Args:
        text: Cleaned text to chunk
        max_chars: Maximum CHARACTERS per chunk (2000 = ~300 words)
        overlap_sentences: Number of SENTENCES to overlap (3 = good balance)
        min_chunk_chars: Minimum CHARACTERS for a valid chunk
        
    Returns:
        List of TextChunk objects
    """
    logger.debug(f"Chunking text: {len(text)} chars, max_chars={max_chars}, overlap={overlap_sentences}")
    if not text or len(text) < min_chunk_chars:
        logger.warning(f"Text too short for chunking: {len(text)} chars < {min_chunk_chars} min")
        return []
    
    sentences = split_into_sentences(text)
    logger.debug(f"Split into {len(sentences)} sentences")
    
    if not sentences:
        logger.warning("No sentences found after splitting")
        return []
    
    chunks = []
    current_chunk = []
    current_length = 0
    chunk_id = 0
    start_char = 0
    
    for sentence in sentences:
        sentence_length = len(sentence) + 1  # +1 for space
        
        # If adding this sentence exceeds limit and we have content, save chunk
        if current_length + sentence_length > max_chars and current_chunk:
            # Save current chunk
            chunk_text = ' '.join(current_chunk)
            end_char = start_char + len(chunk_text)
            
            chunk = TextChunk(
                text=chunk_text,
                chunk_id=chunk_id,
                start_char=start_char,
                end_char=end_char
            )
            chunks.append(chunk)
            chunk_id += 1
            
            # Keep last N sentences for overlap
            if len(current_chunk) > overlap_sentences:
                overlap_text = ' '.join(current_chunk[-overlap_sentences:])
                start_char = end_char - len(overlap_text)
                current_chunk = current_chunk[-overlap_sentences:]
                current_length = sum(len(s) + 1 for s in current_chunk)
            else:
                start_char = end_char
                current_chunk = []
                current_length = 0
        
        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_length += sentence_length
    
    # Add final chunk if it meets minimum size
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        if len(chunk_text) >= min_chunk_chars:
            end_char = start_char + len(chunk_text)
            chunk = TextChunk(
                text=chunk_text,
                chunk_id=chunk_id,
                start_char=start_char,
                end_char=end_char
            )
            chunks.append(chunk)
    
    logger.info(f"Created {len(chunks)} chunks from {len(sentences)} sentences")
    return chunks


def chunk_document(text: str, 
                   source_file: str = "",
                   max_chars: int = 2000,
                   overlap_sentences: int = 3) -> List[TextChunk]:
    """
    Chunk a complete document using SENTENCE-BASED strategy.
    
    Args:
        text: Full document text
        source_file: Name of source file
        max_chars: Maximum CHARACTERS per chunk (2000 chars)
        overlap_sentences: Number of SENTENCES to overlap (3 sentences)
        
    Returns:
        List of TextChunk objects with metadata
    """
    logger.debug(f"Chunking document: {source_file}, {len(text)} chars")
    chunks = chunk_text(text, max_chars, overlap_sentences)
    
    # Add source file to each chunk
    for chunk in chunks:
        chunk.source_file = source_file
    
    logger.info(f"Document chunked: {source_file} -> {len(chunks)} chunks")
    return chunks


def get_chunking_stats(chunks: List[TextChunk]) -> Dict:
    """
    Get statistics about chunking results.
    
    Args:
        chunks: List of chunks
        
    Returns:
        Dictionary with statistics
    """
    if not chunks:
        return {
            'total_chunks': 0,
            'total_chars': 0,
            'total_words': 0,
            'avg_chunk_chars': 0,
            'avg_chunk_words': 0,
            'min_chunk_chars': 0,
            'max_chunk_chars': 0
        }
    
    char_counts = [c.char_count for c in chunks]
    word_counts = [c.word_count for c in chunks]
    
    return {
        'total_chunks': len(chunks),
        'total_chars': sum(char_counts),
        'total_words': sum(word_counts),
        'avg_chunk_chars': sum(char_counts) / len(chunks),
        'avg_chunk_words': sum(word_counts) / len(chunks),
        'min_chunk_chars': min(char_counts),
        'max_chunk_chars': max(char_counts)
    }


if __name__ == "__main__":
    # Test the chunker
    import sys
    from pathlib import Path
    
    print("\n✂️  Testing Text Chunker (Sentence-Based)")
    print("=" * 60)
    
    # Test 1: Simple example
    print("\n📝 Test 1: Simple Example")
    print("-" * 60)
    
    sample_text = """
    This is the first sentence. This is the second sentence. This is the third sentence.
    Here comes the fourth sentence. And the fifth one too. The sixth sentence is here.
    Seventh sentence for testing. Eighth sentence follows. Ninth sentence appears.
    And finally, the tenth sentence. Eleventh sentence is here. Twelfth sentence concludes.
    """
    
    sample_text = sample_text.strip()
    print(f"Input: {len(sample_text)} chars, {len(sample_text.split())} words")
    
    # Chunk with small max_chars to force multiple chunks
    test_chunks = chunk_text(sample_text, max_chars=200, overlap_sentences=2)
    
    print(f"Result: {len(test_chunks)} chunks created")
    for i, chunk in enumerate(test_chunks, 1):
        print(f"\n  Chunk {i}: {chunk.char_count} chars, {chunk.word_count} words")
        print(f"  Text: {chunk.text[:100]}...")
    
    # Test 2: Real PDF
    data_folder = r"c:\chatbot\backend\data\raw_pdfs"
    
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
    
    print(f"\n\n📂 Test 2: Real PDF Chunking")
    print("-" * 60)
    print(f"Folder: {data_folder}")
    
    try:
        from app.rag.offline.document_loader import load_pdfs_from_folder
        from app.rag.offline.text_extractor import get_full_text_smart
        from app.rag.offline.text_cleaner import clean_text
        
        documents = load_pdfs_from_folder(data_folder)
        
        if documents:
            first_doc = documents[0]
            print(f"\n📖 Processing: {first_doc.filename}")
            
            # Full pipeline: Extract → Clean → Chunk
            print("\n  Step 1: Extracting text...")
            raw_text = get_full_text_smart(first_doc.file_path)
            
            print(f"  Step 2: Cleaning text...")
            cleaned_text = clean_text(raw_text)
            
            print(f"  Step 3: Chunking text (Sentence-Based Strategy)...")
            print(f"    Settings: max_chars=2000 (characters), overlap=3 (sentences)")
            
            chunks = chunk_document(
                text=cleaned_text,
                source_file=first_doc.filename,
                max_chars=2000,
                overlap_sentences=3
            )
            
            # Show statistics
            stats = get_chunking_stats(chunks)
            print(f"\n  ✅ Chunking Complete!")
            print(f"    - Total chunks: {stats['total_chunks']}")
            print(f"    - Avg chunk size: {stats['avg_chunk_chars']:.0f} chars, {stats['avg_chunk_words']:.0f} words")
            print(f"    - Min chunk size: {stats['min_chunk_chars']} chars")
            print(f"    - Max chunk size: {stats['max_chunk_chars']} chars")
            print(f"    - Total content: {stats['total_chars']} chars, {stats['total_words']} words")
            
            # Show preview of each chunk
            print(f"\n  📋 Chunk Previews:")
            for chunk in chunks[:3]:  # Show first 3 chunks
                print(f"\n    Chunk #{chunk.chunk_id} ({chunk.char_count} chars):")
                print(f"    {'-' * 55}")
                preview = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
                print(f"    {preview}")
            
            if len(chunks) > 3:
                print(f"\n    ... and {len(chunks) - 3} more chunks")
            
            # Check overlap
            if len(chunks) > 1:
                print(f"\n  🔗 Checking Overlap Between Chunks:")
                for i in range(min(2, len(chunks) - 1)):
                    chunk1_end = chunks[i].text[-100:]
                    chunk2_start = chunks[i+1].text[:100]
                    
                    # Find common words
                    words1 = set(chunk1_end.split())
                    words2 = set(chunk2_start.split())
                    overlap = words1.intersection(words2)
                    
                    print(f"    Chunk {i} → Chunk {i+1}: {len(overlap)} overlapping words")
            
        else:
            print("\n⚠️  No PDF files found. Add PDFs to test chunking.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
