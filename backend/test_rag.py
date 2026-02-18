"""Test RAG service with user's query"""
from app.services.rag_service import get_rag_service

print("="*60)
print("Testing RAG Service")
print("="*60)

# Initialize RAG
rag = get_rag_service()

# Check availability
available = rag.is_available()
print(f"\nRAG Available: {available}")

if available:
    # Test with user's actual query
    query = "features of PyPDF2"
    print(f"\nQuery: {query}")
    print("-"*60)
    
    answer = rag.get_rag_response(query)
    
    if answer:
        print(f"\nAnswer:\n{answer}")
    else:
        print("\nNo answer returned (None)")
else:
    print("\nRAG not available - check Milvus and configuration")

print("\n" + "="*60)
