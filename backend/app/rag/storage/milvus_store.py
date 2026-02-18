"""
Milvus Vector Store

Manages vector storage and retrieval using Milvus database.
This is Step 7 of the RAG pipeline: Vector Database Storage.
"""
from typing import List, Dict, Optional, Tuple
import numpy as np
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)

from app.logging_config import get_logger
from app.config import (
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_COLLECTION_NAME,
    EMBEDDING_DIMENSION,
)

logger = get_logger(__name__)

class MilvusVectorStore:
    """
    Vector store using Milvus database with MinIO backend.
    
    Architecture:
    - Stores embeddings (384-dimensional vectors)
    - Stores metadata (chunk text, document info)
    - Performs fast similarity search
    """
    
    def __init__(
        self,
        collection_name: str = MILVUS_COLLECTION_NAME,
        host: str = MILVUS_HOST,
        port: int = MILVUS_PORT,
        embedding_dim: int = EMBEDDING_DIMENSION
    ):
        """
        Initialize Milvus connection and collection.
        
        Args:
            collection_name: Name of Milvus collection
            host: Milvus server host
            port: Milvus server port
            embedding_dim: Dimension of embeddings (384 for all-MiniLM-L12-v2)
        """
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.collection = None
        
        # Connect to Milvus
        logger.info(f"Connecting to Milvus at {host}:{port}...")
        connections.connect(
            alias="default",
            host=host,
            port=port
        )
        logger.info("Connected to Milvus successfully")
        
        # Create or load collection
        self._init_collection()
    
    def _init_collection(self):
        """Create collection if not exists, otherwise load it."""
        
        if utility.has_collection(self.collection_name):
            logger.info(f"Loading existing collection: {self.collection_name}")
            self.collection = Collection(self.collection_name)
            self.collection.load()
            logger.debug(f"Collection loaded: {self.collection.num_entities} entities")
        else:
            logger.info(f"Creating new collection: {self.collection_name}")
            self._create_collection()
    
    def _create_collection(self):
        """
        Create Milvus collection with schema.
        
        Schema:
        - chunk_id: Primary key (auto-generated)
        - embedding: Vector field (384 dimensions)
        - text: Chunk text content
        - source_file: Source document filename
        - chunk_index: Position in document
        """
        
        # Define fields
        fields = [
            FieldSchema(
                name="chunk_id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
                description="Auto-generated chunk ID"
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.embedding_dim,
                description="Text embedding vector"
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Original chunk text"
            ),
            FieldSchema(
                name="source_file",
                dtype=DataType.VARCHAR,
                max_length=512,
                description="Source document filename"
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64,
                description="Chunk position in document"
            )
        ]
        
        # Create schema
        schema = CollectionSchema(
            fields=fields,
            description="RAG document chunks with embeddings"
        )
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # Create index for fast search
        index_params = {
            "metric_type": "IP",  # Inner Product (cosine similarity with normalized vectors)
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        # Load collection into memory
        self.collection.load()
        
        logger.info(f"Collection created: {self.collection_name}")
    
    def add_chunks(
        self,
        chunks: List,
        embeddings: np.ndarray
    ) -> List[int]:
        """
        Add chunks with embeddings to Milvus.
        
        Args:
            chunks: List of TextChunk objects (from chunker.py)
            embeddings: Array of embeddings (N, 384)
            
        Returns:
            List of inserted chunk IDs
        """
        
        if len(chunks) == 0:
            logger.warning("No chunks to add")
            return []
        
        logger.debug(f"Preparing {len(chunks)} chunks for insertion")
        # Extract data from chunks
        texts = [chunk.text for chunk in chunks]
        source_files = [chunk.source_file for chunk in chunks]
        chunk_indices = [chunk.chunk_id for chunk in chunks]
        
        # Prepare data for insertion
        data = [
            embeddings.tolist(),  # Convert numpy to list
            texts,
            source_files,
            chunk_indices
        ]
        
        # Insert into Milvus
        logger.info(f"Inserting {len(chunks)} chunks into Milvus...")
        insert_result = self.collection.insert(data)
        
        # Flush to ensure data is persisted
        self.collection.flush()
        
        logger.info(f"Successfully inserted {len(texts)} chunks")
        
        return insert_result.primary_keys
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 4,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query vector (384,)
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of results with chunk_id, text, score, etc.
        """
        logger.debug(f"Searching Milvus: top_k={top_k}, min_score={min_score}")
        
        # Ensure 2D array for search
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search parameters
        search_params = {
            "metric_type": "IP",
            "params": {"nprobe": 10}
        }
        
        # Perform search
        results = self.collection.search(
            data=query_embedding.tolist(),
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["chunk_id", "text", "source_file", "chunk_index"]
        )
        
        # Format results
        formatted_results = []
        for hits in results:
            for hit in hits:
                if hit.score >= min_score:
                    formatted_results.append({
                        "chunk_id": hit.id,
                        "text": hit.entity.get("text"),
                        "source_file": hit.entity.get("source_file"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "score": hit.score
                    })
        
        logger.debug(f"Search returned {len(formatted_results)} results")
        return formatted_results
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        
        stats = {
            "collection_name": self.collection_name,
            "num_entities": self.collection.num_entities,
            "embedding_dim": self.embedding_dim
        }
        
        return stats
    
    def delete_by_source_file(self, filename: str) -> int:
        """
        Delete all chunks associated with a specific source file.
        
        Args:
            filename: Name of the source PDF file
            
        Returns:
            Number of chunks deleted
            
        Usage:
            When a PDF is deleted, call this to remove all its chunks from Milvus.
        """
        logger.info(f"Deleting chunks for source file: {filename}")
        
        # Build delete expression
        expr = f'source_file == "{filename}"'
        
        try:
            # Get count before deletion (for logging)
            count_before = self.collection.num_entities
            
            # Delete entities matching the expression
            self.collection.delete(expr)
            
            # Flush to ensure deletion is persisted
            self.collection.flush()
            
            # Get count after deletion
            count_after = self.collection.num_entities
            deleted_count = count_before - count_after
            
            logger.info(f"Deleted {deleted_count} chunks for file: {filename}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for {filename}: {str(e)}", exc_info=True)
            raise
    
    def delete_collection(self):
        """Delete the entire collection (use with caution!)."""
        
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' deleted")
    
    def close(self):
        """Release collection and disconnect."""
        
        if self.collection:
            try:
                self.collection.release()
            except Exception:
                # Collection may already be deleted/released
                pass
        
        connections.disconnect("default")
        logger.info("Milvus connection closed")


if __name__ == "__main__":
    # Simple test
    print("\n" + "=" * 60)
    print("  MILVUS VECTOR STORE TEST")
    print("=" * 60 + "\n")
    
    try:
        # Initialize store
        store = MilvusVectorStore(
            collection_name="test_collection",
            embedding_dim=384
        )
        
        print("\n📊 Collection Stats:")
        stats = store.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ Test passed - Milvus Vector Store is ready!")
        
        # Cleanup
        store.close()
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Milvus is running:")
        print("  cd backend/docker/milvus")
        print("  .\\start.bat")
