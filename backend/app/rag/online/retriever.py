"""
Retriever Module

Searches Milvus vector database for relevant document chunks.
This is Step 10 of the RAG pipeline: Similarity Search (Retrieval).

Finds the most similar chunks to a query embedding using cosine similarity.
"""

import numpy as np
from typing import List, Dict, Optional
from app.rag.storage.milvus_store import MilvusVectorStore
from app.logging_config import get_logger
from app.config import (
    MILVUS_COLLECTION_NAME,
    MILVUS_HOST,
    MILVUS_PORT,
)

logger = get_logger(__name__)

class Retriever:
    """
    Retrieves relevant document chunks from Milvus vector database.
    
    Uses cosine similarity (via Inner Product with normalized vectors)
    to find the most relevant chunks for a given query.
    """
    
    def __init__(
        self,
        collection_name: str = MILVUS_COLLECTION_NAME,
        host: str = MILVUS_HOST,
        port: int = MILVUS_PORT
    ):
        """
        Initialize retriever with connection to Milvus.
        
        Args:
            collection_name: Name of Milvus collection
            host: Milvus server host
            port: Milvus server port
        """
        logger.debug(f"Initializing retriever: collection={collection_name}, host={host}, port={port}")
        self.collection_name = collection_name
        self.vector_store = MilvusVectorStore(
            collection_name=collection_name,
            host=host,
            port=port
        )
        logger.info("Retriever initialized successfully")
    
    def retrieve(
        self,
        query_embedding: np.ndarray,
        top_k: int = 4,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query embedding.
        
        Args:
            query_embedding: Query vector (384,) from query_embedder
            top_k: Maximum number of results to return
            min_score: Minimum similarity score threshold (0.0 to 1.0)
                      - 0.3 = Balanced (recommended)
                      - 0.4 = Conservative (higher precision)
                      - 0.2 = Aggressive (more results)
        
        Returns:
            List of relevant chunks, each containing:
            - chunk_id: Unique chunk identifier
            - text: Chunk text content
            - source_file: Source document filename
            - chunk_index: Position in original document
            - score: Similarity score (0.0 to 1.0)
            
        Example:
            >>> retriever = Retriever()
            >>> embedding = embedder.embed_query("What is Theory X?")
            >>> chunks = retriever.retrieve(embedding, top_k=4, min_score=0.3)
            >>> for chunk in chunks:
            ...     print(f"Score: {chunk['score']:.2f}")
            ...     print(f"Text: {chunk['text'][:100]}...")
        """
        logger.debug(f"Retrieving chunks: top_k={top_k}, min_score={min_score}")
        
        if query_embedding is None or query_embedding.size == 0:
            logger.warning("Query embedding is empty or None")
            raise ValueError("Query embedding cannot be empty")
        
        # Perform similarity search
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            min_score=min_score
        )
        
        logger.info(f"Retrieved {len(results)} chunks (top_k={top_k}, min_score={min_score})")
        if results:
            scores = [r['score'] for r in results]
            logger.debug(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
        
        return results
    
    def retrieve_with_filter(
        self,
        query_embedding: np.ndarray,
        source_file: Optional[str] = None,
        top_k: int = 4,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve chunks with optional source file filtering.
        
        Args:
            query_embedding: Query vector (384,)
            source_file: Filter by specific source file (optional)
            top_k: Maximum number of results
            min_score: Minimum similarity score
            
        Returns:
            List of filtered relevant chunks
        """
        logger.debug(f"Retrieving with filter: source_file={source_file}")
        
        # Get all results
        results = self.retrieve(query_embedding, top_k=top_k*2, min_score=min_score)
        
        # Apply source file filter if specified
        if source_file:
            original_count = len(results)
            results = [r for r in results if r['source_file'] == source_file]
            logger.debug(f"Filtered {original_count} -> {len(results)} results by source_file")
        
        # Return top_k results
        return results[:top_k]
    
    def get_store_stats(self) -> Dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with collection stats (name, count, dimensions)
        """
        return self.vector_store.get_stats()
    
    def close(self):
        """Close connection to Milvus."""
        if self.vector_store:
            self.vector_store.close()


# Singleton instance for reuse across requests
_retriever_instance: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """
    Get or create a singleton Retriever instance.
    
    This avoids reconnecting to Milvus on every request.
    The connection is established once and reused.
    
    Returns:
        Retriever instance
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    
    return _retriever_instance


if __name__ == "__main__":
    """Test the retriever with existing data in Milvus"""
    print("\n" + "="*60)
    print("STEP 10: Retriever Test")
    print("="*60 + "\n")
    
    try:
        # Initialize retriever
        print("1. Initializing retriever (connecting to Milvus)...")
        retriever = get_retriever()
        print("   ✅ Connected to Milvus")
        
        # Get collection stats
        print("\n2. Checking collection stats...")
        stats = retriever.get_store_stats()
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Documents: {stats['num_entities']} chunks")
        print(f"   Dimensions: {stats['embedding_dim']}")
        
        if stats['num_entities'] == 0:
            print("\n   ⚠️  No documents in collection!")
            print("   Run offline pipeline first to add documents.")
        else:
            # Test retrieval with sample queries
            print("\n3. Testing retrieval with sample queries...")
            from app.rag.online.query_embedder import get_query_embedder
            
            embedder = get_query_embedder()
            
            test_queries = [
                ("What is Theory X?", 0.3),
                ("How do managers motivate employees?", 0.3),
                ("What is quantum physics?", 0.3)
            ]
            
            for query_text, min_score in test_queries:
                print(f"\n   Query: '{query_text}'")
                print(f"   Min score: {min_score}")
                
                # Embed query
                query_embedding = embedder.embed_query(query_text)
                
                # Retrieve chunks
                results = retriever.retrieve(
                    query_embedding=query_embedding,
                    top_k=4,
                    min_score=min_score
                )
                
                if results:
                    print(f"   ✅ Found {len(results)} relevant chunks:")
                    for i, chunk in enumerate(results, 1):
                        print(f"      {i}. Score: {chunk['score']:.4f}")
                        print(f"         Source: {chunk['source_file']}")
                        print(f"         Text: {chunk['text'][:100]}...")
                else:
                    print(f"   ❌ No relevant chunks found (all scores < {min_score})")
        
        print("\n" + "="*60)
        print("✅ Step 10 Complete: Retriever Working!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. Milvus is running (docker-compose up)")
        print("2. Collection exists (run offline pipeline)")
        print("="*60 + "\n")
