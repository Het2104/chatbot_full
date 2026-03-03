"""
Embedder Module

Generates embeddings (vector representations) for text chunks.
This is Step 6 of the RAG pipeline: Embedding Generation.

Uses sentence-transformers with BAAI/bge-large-en-v1.5 model for semantic embeddings.
"""

import numpy as np
from typing import List, Optional
import os
from pathlib import Path

from app.logging_config import get_logger

logger = get_logger(__name__)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Note: logger not available yet at import time, will log when used


class Embedder:
    """
    Generates embeddings for text using sentence-transformers.
    
    Model: BAAI/bge-large-en-v1.5
    - 1024 dimensions
    - Large transformer model
    - Excellent quality for text, tables, and OCR content
    - ~1.3GB model size
    """
    
    def __init__(self, model_name: str = 'BAAI/bge-large-en-v1.5', cache_dir: Optional[str] = None):
        """
        Initialize the embedder with a specific model.
        
        Args:
            model_name: HuggingFace model name
            cache_dir: Directory to cache downloaded models (optional)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
        
        self.model_name = model_name
        self.cache_dir = cache_dir
        
        logger.info(f"Loading embedding model: {model_name}")
        logger.info("First run will download ~1.3GB model")
        
        try:
            self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully! Embedding dimensions: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load model {model_name}: {e}")
    
    def embed_texts(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            show_progress: Show progress bar during embedding
            
        Returns:
            NumPy array of shape (len(texts), embedding_dim)
        """
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        logger.info(f"Generated {len(embeddings)} embeddings with dimension {self.embedding_dim}")
        return embeddings
    
    def embed_chunks(self, chunks: List, show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for TextChunk objects.
        
        Args:
            chunks: List of TextChunk objects (from chunker.py)
            show_progress: Show progress bar during embedding
            
        Returns:
            NumPy array of shape (len(chunks), embedding_dim)
        """
        texts = [chunk.text for chunk in chunks]
        return self.embed_texts(texts, show_progress)
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (e.g., user query).
        
        Args:
            text: Single text string to embed
            
        Returns:
            NumPy array of shape (embedding_dim,)
        """
        embedding = self.model.encode(
            [text],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding[0]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.embedding_dim
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'max_seq_length': self.model.max_seq_length,
            'cache_dir': self.cache_dir
        }


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Similarity score between -1 and 1 (higher = more similar)
    """
    # Normalized embeddings: dot product = cosine similarity
    return np.dot(embedding1, embedding2)


def compute_similarity_matrix(query_embedding: np.ndarray, 
                              chunk_embeddings: np.ndarray) -> np.ndarray:
    """
    Compute similarity between a query and multiple chunks.
    
    Args:
        query_embedding: Query embedding (embedding_dim,)
        chunk_embeddings: Chunk embeddings (num_chunks, embedding_dim)
        
    Returns:
        Array of similarity scores (num_chunks,)
    """
    # Normalized embeddings: matrix multiplication = cosine similarities
    similarities = np.dot(chunk_embeddings, query_embedding)
    return similarities


if __name__ == "__main__":
    # Test the embedder
    import sys
    
    print("\n🧮 Testing Embedding Generation")
    print("=" * 60)
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("\n❌ sentence-transformers not installed")
        print("   Run: pip install sentence-transformers")
        sys.exit(1)
    
    # Test 1: Simple text embedding
    print("\n📝 Test 1: Simple Text Embedding")
    print("-" * 60)
    
    try:
        embedder = Embedder()
        
        test_texts = [
            "The cat sits on the mat.",
            "A feline rests on the rug.",  # Similar meaning
            "Python is a programming language."  # Different meaning
        ]
        
        print(f"\nEmbedding {len(test_texts)} sample texts...")
        embeddings = embedder.embed_texts(test_texts, show_progress=False)
        
        print(f"\n✅ Embeddings generated!")
        print(f"   Shape: {embeddings.shape}")
        print(f"   Each embedding: {embeddings.shape[1]} dimensions")
        
        # Show similarity
        print(f"\n🔗 Similarity Analysis:")
        sim_1_2 = compute_similarity(embeddings[0], embeddings[1])
        sim_1_3 = compute_similarity(embeddings[0], embeddings[2])
        
        print(f"   Text 1 vs Text 2 (similar meaning): {sim_1_2:.4f}")
        print(f"   Text 1 vs Text 3 (different meaning): {sim_1_3:.4f}")
        print(f"   → Higher score = more similar ✅")
        
    except Exception as e:
        print(f"\n❌ Error in Test 1: {e}")
        sys.exit(1)
    
    # Test 2: Real PDF chunks
    data_folder = r"c:\chatbot\backend\data\raw_pdfs"
    
    if len(sys.argv) > 1:
        data_folder = sys.argv[1]
    
    print(f"\n\n📂 Test 2: Real PDF Embedding")
    print("-" * 60)
    print(f"Folder: {data_folder}")
    
    try:
        from app.rag.offline.document_loader import load_pdfs_from_folder
        from app.rag.offline.text_extractor import get_full_text_smart
        from app.rag.offline.text_cleaner import clean_text
        from app.rag.offline.chunker import chunk_document, get_chunking_stats
        
        documents = load_pdfs_from_folder(data_folder)
        
        if documents:
            first_doc = documents[0]
            print(f"\n📖 Processing: {first_doc.filename}")
            
            # Full pipeline: Extract → Clean → Chunk → Embed
            print(f"\n  Step 1: Extracting text...")
            raw_text = get_full_text_smart(first_doc.file_path)
            
            print(f"  Step 2: Cleaning text...")
            cleaned_text = clean_text(raw_text)
            
            print(f"  Step 3: Chunking text...")
            chunks = chunk_document(
                text=cleaned_text,
                source_file=first_doc.filename,
                max_chars=2000
            )
            
            stats = get_chunking_stats(chunks)
            print(f"    → Created {stats['total_chunks']} chunk(s)")
            
            print(f"\n  Step 4: Generating embeddings...")
            embeddings = embedder.embed_chunks(chunks, show_progress=True)
            
            print(f"\n  ✅ Embeddings Complete!")
            print(f"    - Shape: {embeddings.shape}")
            print(f"    - {embeddings.shape[0]} chunks × {embeddings.shape[1]} dimensions")
            print(f"    - Memory: ~{embeddings.nbytes / 1024:.1f} KB")
            
            # Preview first embedding
            print(f"\n  📊 Sample Embedding (Chunk 0, first 10 values):")
            print(f"    {embeddings[0][:10]}")
            
            # Test query similarity
            print(f"\n  🔍 Test Query Similarity:")
            test_queries = [
                "What is Theory X?",
                "How do managers motivate employees?",
                "What is quantum physics?"  # Unrelated
            ]
            
            for query in test_queries:
                query_emb = embedder.embed_single(query)
                similarities = compute_similarity_matrix(query_emb, embeddings)
                
                best_chunk_idx = np.argmax(similarities)
                best_score = similarities[best_chunk_idx]
                
                print(f"\n    Query: '{query}'")
                print(f"    → Best match: Chunk {best_chunk_idx} (score: {best_score:.4f})")
                print(f"      Preview: {chunks[best_chunk_idx].text[:100]}...")
        
        else:
            print("\n⚠️  No PDF files found. Add PDFs to test embedding.")
    
    except Exception as e:
        print(f"\n❌ Error in Test 2: {e}")
        import traceback
        traceback.print_exc()
