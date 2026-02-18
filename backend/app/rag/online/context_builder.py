"""
Context Builder Module

Assembles retrieved document chunks into formatted context for LLM prompts.
This is Step 11 of the RAG pipeline: Context Assembly.

Takes retrieved chunks and combines them into a single context string.
"""

from typing import List, Dict, Optional
from app.logging_config import get_logger

logger = get_logger(__name__)

def assemble_context(
    retrieved_chunks: List[Dict],
    include_scores: bool = False,
    include_sources: bool = True,
    max_chunks: Optional[int] = None
) -> str:
    """
    Combine retrieved chunks into formatted context for LLM.
    
    Args:
        retrieved_chunks: List of chunks from retriever, each containing:
            - text: Chunk text content
            - score: Similarity score (0.0 to 1.0)
            - source_file: Source document filename
            - chunk_index: Position in document
        include_scores: Whether to show relevance scores
        include_sources: Whether to show source filenames
        max_chunks: Maximum number of chunks to include (None = all)
        
    Returns:
        Formatted context string ready for LLM prompt
        
    Example:
        >>> chunks = [
        ...     {"text": "Theory X assumes...", "score": 0.46, "source_file": "doc.pdf"},
        ...     {"text": "Theory Y believes...", "score": 0.42, "source_file": "doc.pdf"}
        ... ]
        >>> context = assemble_context(chunks)
        >>> print(context)
        Context 1 (from doc.pdf):
        Theory X assumes...
        
        Context 2 (from doc.pdf):
        Theory Y believes...
    """
    logger.debug(f"Assembling context from {len(retrieved_chunks)} chunks")
    
    if not retrieved_chunks:
        logger.warning("No chunks to assemble into context")
        return ""
    
    # Limit number of chunks if specified
    chunks_to_use = retrieved_chunks[:max_chunks] if max_chunks else retrieved_chunks
    logger.debug(f"Using {len(chunks_to_use)} chunks for context")
    
    # Build context sections
    context_parts = []
    
    for i, chunk in enumerate(chunks_to_use, 1):
        # Build header
        header_parts = [f"Context {i}"]
        
        if include_scores:
            score = chunk.get('score', 0.0)
            header_parts.append(f"relevance: {score:.2f}")
        
        if include_sources:
            source = chunk.get('source_file', 'unknown')
            header_parts.append(f"from {source}")
        
        # Format section
        header = " (".join(header_parts)
        if len(header_parts) > 1:
            header += ")"
        header += ":"
        
        text = chunk.get('text', '').strip()
        
        section = f"{header}\n{text}"
        context_parts.append(section)
    
    context_result = "\n\n".join(context_parts)
    logger.info(f"Context assembled: {len(chunks_to_use)} chunks, {len(context_result)} chars")
    return context_result


def assemble_context_simple(retrieved_chunks: List[Dict]) -> str:
    """
    Combine chunks into simple context without headers.
    
    Args:
        retrieved_chunks: List of chunks from retriever
        
    Returns:
        Plain context string (just the text, no formatting)
        
    Example:
        >>> chunks = [{"text": "Theory X..."}, {"text": "Theory Y..."}]
        >>> context = assemble_context_simple(chunks)
        >>> print(context)
        Theory X...
        
        Theory Y...
    """
    
    if not retrieved_chunks:
        return ""
    
    texts = [chunk.get('text', '').strip() for chunk in retrieved_chunks]
    return "\n\n".join(texts)


def get_context_stats(retrieved_chunks: List[Dict]) -> Dict:
    """
    Get statistics about the assembled context.
    
    Args:
        retrieved_chunks: List of chunks from retriever
        
    Returns:
        Dictionary with stats:
        - num_chunks: Number of chunks
        - total_chars: Total character count
        - total_words: Estimated word count
        - avg_score: Average similarity score
        - sources: List of unique source files
    """
    
    if not retrieved_chunks:
        return {
            "num_chunks": 0,
            "total_chars": 0,
            "total_words": 0,
            "avg_score": 0.0,
            "sources": []
        }
    
    total_chars = sum(len(chunk.get('text', '')) for chunk in retrieved_chunks)
    total_words = sum(len(chunk.get('text', '').split()) for chunk in retrieved_chunks)
    avg_score = sum(chunk.get('score', 0.0) for chunk in retrieved_chunks) / len(retrieved_chunks)
    sources = list(set(chunk.get('source_file', 'unknown') for chunk in retrieved_chunks))
    
    return {
        "num_chunks": len(retrieved_chunks),
        "total_chars": total_chars,
        "total_words": total_words,
        "avg_score": avg_score,
        "sources": sources
    }


def format_context_for_display(retrieved_chunks: List[Dict]) -> str:
    """
    Format context for user display (debugging/transparency).
    
    Args:
        retrieved_chunks: List of chunks from retriever
        
    Returns:
        Nicely formatted context with full metadata
    """
    
    if not retrieved_chunks:
        return "No relevant context found."
    
    lines = [f"Found {len(retrieved_chunks)} relevant chunks:\n"]
    
    for i, chunk in enumerate(retrieved_chunks, 1):
        score = chunk.get('score', 0.0)
        source = chunk.get('source_file', 'unknown')
        text = chunk.get('text', '').strip()
        
        lines.append(f"[{i}] Score: {score:.4f} | Source: {source}")
        lines.append(f"    {text[:200]}{'...' if len(text) > 200 else ''}\n")
    
    return "\n".join(lines)


if __name__ == "__main__":
    """Test the context builder"""
    print("\n" + "="*60)
    print("STEP 11: Context Builder Test")
    print("="*60 + "\n")
    
    # Sample chunks (simulating retriever output)
    sample_chunks = [
        {
            "chunk_id": 1,
            "text": "Theory X is a management style that assumes employees inherently dislike work and will avoid it if possible. Managers who subscribe to Theory X believe that workers need to be closely supervised and controlled through rewards and punishments.",
            "score": 0.4645,
            "source_file": "McGregor_Theory_X_and_Y.pdf",
            "chunk_index": 0
        },
        {
            "chunk_id": 2,
            "text": "Theory Y represents a contrasting management philosophy. It assumes that employees are self-motivated, enjoy their work, and seek out responsibility. Theory Y managers believe in empowering employees and giving them autonomy.",
            "score": 0.4120,
            "source_file": "McGregor_Theory_X_and_Y.pdf",
            "chunk_index": 1
        },
        {
            "chunk_id": 3,
            "text": "Douglas McGregor introduced these theories in his 1960 book 'The Human Side of Enterprise'. The theories have had lasting impact on organizational behavior and management practices.",
            "score": 0.3580,
            "source_file": "McGregor_Theory_X_and_Y.pdf",
            "chunk_index": 2
        }
    ]
    
    print("1. Testing standard context assembly...")
    context = assemble_context(sample_chunks, include_scores=True, include_sources=True)
    print(context)
    print()
    
    print("\n" + "-"*60 + "\n")
    print("2. Testing simple context (no headers)...")
    simple = assemble_context_simple(sample_chunks)
    print(simple)
    print()
    
    print("\n" + "-"*60 + "\n")
    print("3. Testing context statistics...")
    stats = get_context_stats(sample_chunks)
    print(f"   Chunks: {stats['num_chunks']}")
    print(f"   Characters: {stats['total_chars']}")
    print(f"   Words: {stats['total_words']}")
    print(f"   Avg Score: {stats['avg_score']:.4f}")
    print(f"   Sources: {', '.join(stats['sources'])}")
    print()
    
    print("\n" + "-"*60 + "\n")
    print("4. Testing display format...")
    display = format_context_for_display(sample_chunks)
    print(display)
    
    print("\n" + "-"*60 + "\n")
    print("5. Testing with max_chunks limit...")
    limited = assemble_context(sample_chunks, max_chunks=2, include_scores=False)
    print(limited)
    print()
    
    print("\n" + "-"*60 + "\n")
    print("6. Testing with empty chunks...")
    empty = assemble_context([])
    print(f"Empty result: '{empty}' (length: {len(empty)})")
    print()
    
    print("\n" + "="*60)
    print("✅ Step 11 Complete: Context Builder Working!")
    print("="*60 + "\n")
