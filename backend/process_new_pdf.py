"""Process a specific new PDF"""

import os
from app.rag.offline.document_loader import load_pdfs_from_folder, get_full_text
from app.rag.offline.text_cleaner import clean_text
from app.rag.offline.chunker import chunk_document
from app.rag.offline.embedder import Embedder
from app.rag.storage.milvus_store import MilvusVectorStore

# Change this to your new PDF filename
NEW_PDF_NAME = "C:\\chatbot\\backend\\data\\raw_pdfs\\102014-92488-I-1 (1).pdf"

def process_single_pdf(filename):
    """Process a single PDF by name"""
    
    pdf_path = os.path.join('data/raw_pdfs', filename)
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"📖 Processing: {filename}")
    
    # Extract text
    text = get_full_text(pdf_path)
    print(f"   Extracted {len(text)} characters")
    
    # Clean text
    cleaned = clean_text(text)
    print(f"   Cleaned to {len(cleaned)} characters")
    
    # Chunk document
    chunks = chunk_document(cleaned, filename)
    print(f"   Created {len(chunks)} chunks")
    
    # Generate embeddings
    embedder = Embedder()
    embeddings = embedder.embed_chunks(chunks, show_progress=True)
    
    # Store in Milvus
    store = MilvusVectorStore(collection_name='rag_chunks')
    store.add_chunks(chunks, embeddings)
    
    print(f"   ✅ Successfully added {filename} to vector database!")

if __name__ == "__main__":
    process_single_pdf(NEW_PDF_NAME)