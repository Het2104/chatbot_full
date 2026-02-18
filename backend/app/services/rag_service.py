"""
RAG Service

Orchestrates the complete RAG pipeline (Steps 9-14).
This is Step 15: Integration into the chatbot.

Provides a single entry point for RAG functionality.
"""

from typing import Optional
from app.logging_config import get_logger
from app.config import (
    RAG_DEFAULT_TOP_K,
    RAG_DEFAULT_MIN_SCORE,
    RAG_DEFAULT_TEMPERATURE,
)
from app.utils import NO_RELEVANT_DOCS_MESSAGE

logger = get_logger(__name__)

from app.rag.online.query_embedder import get_query_embedder
from app.rag.online.retriever import get_retriever
from app.rag.online.context_builder import assemble_context
from app.rag.online.prompt_builder import build_prompt
from app.rag.online.generator import get_generator
from app.rag.online.response_formatter import format_response_simple


class RAGService:
    """
    Complete RAG pipeline orchestrator.
    
    Chains together: Query Embedding → Retrieval → Context Assembly
                     → Prompt Building → LLM Generation → Response Formatting
    """
    
    def __init__(
        self,
        min_score: float = RAG_DEFAULT_MIN_SCORE,
        top_k: int = RAG_DEFAULT_TOP_K,
        temperature: float = RAG_DEFAULT_TEMPERATURE
    ):
        """
        Initialize RAG service with all components.
        
        Args:
            min_score: Minimum similarity score for retrieval (0.3 = balanced)
            top_k: Number of chunks to retrieve
            temperature: LLM temperature (0 = deterministic)
        """
        self.min_score = min_score
        self.top_k = top_k
        self.temperature = temperature
        
        # Initialize components (lazy loading for performance)
        self._embedder = None
        self._retriever = None
        self._generator = None
        self._initialized = False
    
    def _initialize(self):
        """Lazy initialization of RAG components."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing RAG service...")
            
            # Initialize components
            self._embedder = get_query_embedder()
            logger.debug("Query embedder initialized")
            
            self._retriever = get_retriever()
            logger.debug("Retriever initialized")
            
            self._generator = get_generator()
            logger.debug("Generator initialized")
            
            self._initialized = True
            logger.info("RAG service ready")
            
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}", exc_info=True)
            self._initialized = False
    
    def get_rag_response(self, user_question: str) -> Optional[str]:
        """
        Get RAG answer for user question.
        
        Args:
            user_question: User's question text
            
        Returns:
            - Answer string if relevant documents found
            - "I don't know..." if no relevant documents
            - None if RAG system unavailable (triggers fallback)
            
        Example:
            >>> rag = RAGService()
            >>> answer = rag.get_rag_response("What is Theory X?")
            >>> print(answer)
            Theory X assumes employees dislike work...
        """
        
        # Ensure initialized
        self._initialize()
        
        if not self._initialized:
            logger.warning("RAG not initialized, returning None")
            return None
        
        try:
            # Step 9: Embed query
            logger.info(f"RAG Query: '{user_question[:100]}...'")
            query_embedding = self._embedder.embed_query(user_question)
            logger.debug(f"Query embedded: shape={query_embedding.shape}")
            
            # Step 10: Retrieve relevant chunks
            logger.debug(f"Retrieving chunks: top_k={self.top_k}, min_score={self.min_score}")
            chunks = self._retriever.retrieve(
                query_embedding=query_embedding,
                top_k=self.top_k,
                min_score=self.min_score
            )
            
            # Check if any relevant chunks found
            if not chunks or len(chunks) == 0:
                logger.info(f"No relevant documents found (threshold: {self.min_score})")
                return NO_RELEVANT_DOCS_MESSAGE
            
            logger.info(f"Found {len(chunks)} relevant chunks (scores: {[round(c['score'], 3) for c in chunks]})")
            
            # Step 11: Assemble context
            logger.debug("Assembling context from chunks...")
            context = assemble_context(
                chunks,
                include_scores=False,
                include_sources=True
            )
            logger.debug(f"Context assembled: {len(context)} characters")
            
            # Step 12: Build prompt
            logger.debug("Building prompt...")
            prompt = build_prompt(
                question=user_question,
                context=context,
                prompt_type="strict"
            )
            logger.debug(f"Prompt built: {len(prompt)} characters")
            
            # Step 13: Generate answer with LLM
            logger.info("Generating answer with LLM...")
            llm_answer = self._generator.generate(
                prompt=prompt,
                temperature=self.temperature
            )
            logger.debug(f"LLM answer generated: {len(llm_answer)} characters")
            
            # Step 14: Format response
            formatted_answer = format_response_simple(llm_answer)
            
            logger.info(f"RAG answer generated successfully: {formatted_answer[:100]}...")
            
            return formatted_answer
            
        except Exception as e:
            logger.error(f"RAG pipeline error: {e}", exc_info=True)
            # Return None to trigger fallback to default response
            return None
    
    def is_available(self) -> bool:
        """
        Check if RAG system is available and working.
        
        Returns:
            True if RAG can be used, False otherwise
        """
        self._initialize()
        logger.debug(f"RAG availability check: {self._initialized}")
        return self._initialized


# Singleton instance for reuse across requests
_rag_service_instance: Optional[RAGService] = None


def get_rag_service(reinit: bool = False) -> RAGService:
    """
    Get or create singleton RAG service instance.
    
    Args:
        reinit: Force reinitialization
        
    Returns:
        RAGService instance
    """
    global _rag_service_instance
    
    if _rag_service_instance is None or reinit:
        _rag_service_instance = RAGService()
    
    return _rag_service_instance


if __name__ == "__main__":
    """Test RAG service end-to-end"""
    print("\n" + "="*60)
    print("STEP 15: RAG Service Integration Test")
    print("="*60 + "\n")
    
    try:
        # Initialize service
        print("1. Initializing RAG service...")
        rag = get_rag_service()
        
        # Check availability
        print("\n2. Checking availability...")
        available = rag.is_available()
        print(f"   RAG available: {available}\n")
        
        if not available:
            print("⚠️  RAG not available. Check Milvus and Groq configuration.")
        else:
            # Test queries
            test_queries = [
                "What is Theory X?",
                "How do managers motivate employees?",
                "What is quantum physics?"
            ]
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n{i}. Test Query: '{query}'")
                print("-" * 60)
                
                answer = rag.get_rag_response(query)
                
                if answer:
                    print(f"Answer: {answer[:200]}")
                    if len(answer) > 200:
                        print("...")
                else:
                    print("Answer: None (would fallback to default)")
                print()
        
        print("\n" + "="*60)
        print("✅ RAG Service Test Complete!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
