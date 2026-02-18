"""
Response Formatter Module

Formats LLM answers with optional metadata for user-friendly responses.
This is Step 14 of the RAG pipeline: Response Formatting.

Takes raw LLM output and formats it with sources, confidence, etc.
"""

from typing import List, Dict, Optional
from app.logging_config import get_logger

logger = get_logger(__name__)

def format_response(
    llm_answer: str,
    retrieved_chunks: Optional[List[Dict]] = None,
    include_sources: bool = False,
    include_confidence: bool = False
) -> Dict:
    """
    Format RAG response with optional metadata.
    
    Args:
        llm_answer: Raw answer from LLM generator (Step 13)
        retrieved_chunks: Chunks from retriever (Step 10) with metadata
        include_sources: Whether to include source document references
        include_confidence: Whether to include confidence score
        
    Returns:
        Formatted response dictionary:
        {
            "answer": str,              # Main answer text
            "sources": List[str],       # Optional: source files
            "confidence": float,        # Optional: avg similarity score
            "chunk_count": int          # Optional: number of chunks used
        }
        
    Example:
        >>> chunks = [{"text": "...", "score": 0.46, "source_file": "doc.pdf"}]
        >>> response = format_response("Theory X assumes...", chunks, include_sources=True)
        >>> print(response["answer"])
        Theory X assumes...
        >>> print(response["sources"])
        ['doc.pdf']
    """
    logger.debug(f"Formatting response: answer_len={len(llm_answer)}, chunks={len(retrieved_chunks) if retrieved_chunks else 0}")
    
    # Base response
    response = {
        "answer": llm_answer.strip()
    }
    
    # Add optional metadata if chunks provided
    if retrieved_chunks and len(retrieved_chunks) > 0:
        
        # Extract unique source files
        if include_sources:
            sources = list(set(
                chunk.get("source_file", "unknown") 
                for chunk in retrieved_chunks
            ))
            response["sources"] = sources
        
        # Calculate average confidence score
        if include_confidence:
            scores = [chunk.get("score", 0.0) for chunk in retrieved_chunks]
            avg_confidence = sum(scores) / len(scores) if scores else 0.0
            response["confidence"] = round(avg_confidence, 4)
        
        # Add chunk count
        response["chunk_count"] = len(retrieved_chunks)
    
    logger.info(f"Response formatted successfully with {len(response)} fields")
    return response


def format_response_with_sources_inline(
    llm_answer: str,
    retrieved_chunks: Optional[List[Dict]] = None
) -> str:
    """
    Format response with source references inline (e.g., [1], [2]).
    
    Args:
        llm_answer: Raw answer from LLM
        retrieved_chunks: Chunks with metadata
        
    Returns:
        Answer with inline citations
        
    Example:
        >>> answer = "Theory X assumes employees dislike work."
        >>> chunks = [{"source_file": "McGregor.pdf"}]
        >>> formatted = format_response_with_sources_inline(answer, chunks)
        >>> print(formatted)
        Theory X assumes employees dislike work.
        
        Sources:
        [1] McGregor.pdf
    """
    
    if not retrieved_chunks or len(retrieved_chunks) == 0:
        return llm_answer
    
    # Get unique sources
    sources = []
    seen = set()
    for chunk in retrieved_chunks:
        source = chunk.get("source_file", "unknown")
        if source not in seen:
            sources.append(source)
            seen.add(source)
    
    # Build source list
    if sources:
        source_text = "\n\nSources:\n"
        for i, source in enumerate(sources, 1):
            source_text += f"[{i}] {source}\n"
        
        return llm_answer.strip() + source_text
    
    return llm_answer


def format_response_simple(llm_answer: str) -> str:
    """
    Simple formatting - just clean up the answer.
    
    Args:
        llm_answer: Raw answer from LLM
        
    Returns:
        Cleaned answer text
    """
    # Remove extra whitespace
    answer = " ".join(llm_answer.split())
    return answer.strip()


def check_if_no_answer(llm_answer: str) -> bool:
    """
    Check if LLM responded with "I don't know" variant.
    
    Args:
        llm_answer: Answer from LLM
        
    Returns:
        True if answer indicates "don't know", False otherwise
    """
    
    no_answer_phrases = [
        "i don't know",
        "i do not know",
        "don't know based on",
        "do not know based on",
        "not found in the context",
        "no information",
        "cannot answer"
    ]
    
    answer_lower = llm_answer.lower().strip()
    
    return any(phrase in answer_lower for phrase in no_answer_phrases)


def format_for_chat_ui(
    llm_answer: str,
    retrieved_chunks: Optional[List[Dict]] = None,
    include_sources: bool = True
) -> Dict:
    """
    Format response specifically for chat UI integration.
    
    Args:
        llm_answer: Raw answer from LLM
        retrieved_chunks: Chunks with metadata
        include_sources: Whether to show sources
        
    Returns:
        Chat-friendly response:
        {
            "bot_response": str,      # Main text to display
            "metadata": dict,         # Optional metadata for UI
            "has_answer": bool        # False if "don't know"
        }
    """
    
    has_answer = not check_if_no_answer(llm_answer)
    
    # Build main response
    if include_sources and retrieved_chunks and has_answer:
        bot_response = format_response_with_sources_inline(llm_answer, retrieved_chunks)
    else:
        bot_response = format_response_simple(llm_answer)
    
    # Build metadata
    metadata = {}
    if retrieved_chunks:
        metadata["chunk_count"] = len(retrieved_chunks)
        if len(retrieved_chunks) > 0:
            metadata["avg_score"] = round(
                sum(c.get("score", 0) for c in retrieved_chunks) / len(retrieved_chunks),
                4
            )
    
    return {
        "bot_response": bot_response,
        "metadata": metadata,
        "has_answer": has_answer
    }


if __name__ == "__main__":
    """Test the response formatter"""
    print("\n" + "="*60)
    print("STEP 14: Response Formatter Test")
    print("="*60 + "\n")
    
    # Sample data
    sample_answer = "Theory X assumes that employees inherently dislike work and will avoid it if possible. Managers who subscribe to Theory X believe that workers need to be closely supervised."
    
    sample_chunks = [
        {
            "chunk_id": 1,
            "text": "Theory X is a management style...",
            "score": 0.4645,
            "source_file": "McGregor_Theory_X_and_Y.pdf",
            "chunk_index": 0
        },
        {
            "chunk_id": 2,
            "text": "Theory Y represents...",
            "score": 0.4120,
            "source_file": "McGregor_Theory_X_and_Y.pdf",
            "chunk_index": 1
        }
    ]
    
    no_answer = "I don't know based on the provided documents."
    
    # Test 1: Basic formatting with sources
    print("1. Test: Basic formatting with sources...")
    print("-" * 60)
    response1 = format_response(
        sample_answer, 
        sample_chunks, 
        include_sources=True, 
        include_confidence=True
    )
    print(f"Answer: {response1['answer'][:100]}...")
    print(f"Sources: {response1.get('sources', [])}")
    print(f"Confidence: {response1.get('confidence', 0)}")
    print(f"Chunks: {response1.get('chunk_count', 0)}\n")
    
    # Test 2: Simple formatting
    print("\n2. Test: Simple formatting (no metadata)...")
    print("-" * 60)
    response2 = format_response(sample_answer)
    print(f"Keys: {list(response2.keys())}")
    print(f"Answer: {response2['answer'][:100]}...\n")
    
    # Test 3: Inline sources
    print("\n3. Test: Inline source citations...")
    print("-" * 60)
    response3 = format_response_with_sources_inline(sample_answer, sample_chunks)
    print(response3)
    print()
    
    # Test 4: Chat UI format
    print("\n4. Test: Chat UI format...")
    print("-" * 60)
    response4 = format_for_chat_ui(sample_answer, sample_chunks, include_sources=True)
    print(f"Bot response:\n{response4['bot_response'][:150]}...")
    print(f"\nMetadata: {response4['metadata']}")
    print(f"Has answer: {response4['has_answer']}\n")
    
    # Test 5: "Don't know" detection
    print("\n5. Test: 'Don't know' detection...")
    print("-" * 60)
    is_no_answer = check_if_no_answer(no_answer)
    print(f"Answer: '{no_answer}'")
    print(f"Detected as 'no answer': {is_no_answer}")
    
    response5 = format_for_chat_ui(no_answer, sample_chunks)
    print(f"Has answer: {response5['has_answer']}\n")
    
    # Test 6: No chunks provided
    print("\n6. Test: No chunks provided...")
    print("-" * 60)
    response6 = format_response(sample_answer, None, include_sources=True)
    print(f"Keys: {list(response6.keys())}")
    print(f"Has sources: {'sources' in response6}\n")
    
    print("\n" + "="*60)
    print("✅ Step 14 Complete: Response Formatter Working!")
    print("="*60 + "\n")
