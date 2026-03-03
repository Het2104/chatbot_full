"""
Query Embedder Module

Converts user queries into embedding vectors for similarity search.
This is Step 9 of the RAG pipeline: Query Embedding.

Reuses the same Embedder from offline processing to ensure vector space compatibility.
"""

import numpy as np
from typing import Optional
from app.rag.offline.embedder import Embedder
from app.logging_config import get_logger

logger = get_logger(__name__)

class QueryEmbedder:
    """
    Converts user queries into embedding vectors.
    
    Uses the same model as offline processing (BAAI/bge-large-en-v1.5)
    to ensure query and document embeddings are in the same vector space.
    """
    
    def __init__(self, model_name: str = 'BAAI/bge-large-en-v1.5'):
        """
        Initialize query embedder with the same model used for documents.
        
        Args:
            model_name: Must match the model used in offline processing
        """
        logger.debug(f"Initializing query embedder with model: {model_name}")
        self.embedder = Embedder(model_name=model_name)
        self.embedding_dim = self.embedder.get_embedding_dimension()
        logger.info(f"Query embedder initialized: {self.embedding_dim}D embeddings")
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Convert a user query into an embedding vector.
        
        Args:
            query: User's question/message as a string
            
        Returns:
            NumPy array of shape (384,) - normalized embedding vector
            
        Example:
            >>> embedder = QueryEmbedder()
            >>> query = "What is Theory X?"
            >>> embedding = embedder.embed_query(query)
            >>> embedding.shape
            (1024,)
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to query embedder")
            raise ValueError("Query cannot be empty")
        
        # Clean the query
        query = query.strip()
        logger.debug(f"Embedding query: '{query[:100]}...'")
        
        # bge models require this instruction prefix for query embeddings
        query = f"Represent this sentence for searching relevant passages: {query}"
        
        # Generate embedding using the same model as offline processing
        embedding = self.embedder.embed_single(query)
        
        logger.debug(f"Query embedded: shape={embedding.shape}")
        return embedding
    
    def embed_queries(self, queries: list[str]) -> np.ndarray:
        """
        Convert multiple queries into embeddings (batch processing).
        
        Args:
            queries: List of query strings
            
        Returns:
            NumPy array of shape (len(queries), 384)
        """
        if not queries:
            raise ValueError("Queries list cannot be empty")
        
        # Clean queries
        queries = [q.strip() for q in queries if q and q.strip()]
        
        if not queries:
            raise ValueError("No valid queries after cleaning")
        
        # Generate embeddings
        embeddings = self.embedder.embed_texts(queries, show_progress=False)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings (should be 384)"""
        return self.embedding_dim


# Singleton instance for reuse across requests
_query_embedder_instance: Optional[QueryEmbedder] = None


def get_query_embedder() -> QueryEmbedder:
    """
    Get or create a singleton QueryEmbedder instance.
    
    This avoids reloading the model on every request.
    The model is loaded once and reused.
    
    Returns:
        QueryEmbedder instance
    """
    global _query_embedder_instance
    
    if _query_embedder_instance is None:
        _query_embedder_instance = QueryEmbedder()
    
    return _query_embedder_instance


if __name__ == "__main__":
    """Quick test of query embedding"""
    print("\n" + "="*60)
    print("STEP 9: Query Embedder Test")
    print("="*60 + "\n")
    
    # Initialize embedder using singleton
    print("1. Initializing query embedder (singleton)...")
    embedder = get_query_embedder()
    print(f"   ✅ Embedding dimension: {embedder.get_embedding_dimension()}")
    
    # Test query embedding
    print("\n2. Testing query embedding...")
    test_queries = [
        "What is Theory X?",
        "How do managers motivate employees?",
        "What is quantum physics?"
    ]
    
    for query in test_queries:
        embedding = embedder.embed_query(query)
        print(f"   Query: '{query}'")
        print(f"   ✅ Embedding shape: {embedding.shape}")
        print(f"   ✅ Embedding preview: [{embedding[0]:.4f}, {embedding[1]:.4f}, ..., {embedding[-1]:.4f}]")
        print()
    
    # Test batch embedding
    print("3. Testing batch embedding...")
    embeddings = embedder.embed_queries(test_queries)
    print(f"   ✅ Batch shape: {embeddings.shape}")
    print(f"   ✅ All queries embedded successfully!")
    
    # Test singleton
    print("\n4. Testing singleton pattern...")
    embedder2 = get_query_embedder()
    print(f"   ✅ Same instance: {embedder is embedder2}")
    
    print("\n" + "="*60)
    print("✅ Step 9 Complete: Query Embedder Working!")
    print("="*60 + "\n")
