"""
Test script to verify RAG answers questions from uploaded PDFs
"""
from app.services.rag_service import get_rag_service

def test_rag_queries():
    print("="*70)
    print("RAG SYSTEM TEST - Verifying Fixes")
    print("="*70)
    
    # Initialize RAG
    print("\n1. Initializing RAG service...")
    rag = get_rag_service()
    
    # Check availability
    if not rag.is_available():
        print("   ❌ RAG not available!")
        return
    
    print("   ✅ RAG initialized successfully")
    
    # Test queries from user's screenshot
    test_queries = [
        "features of PyPDF2",
        "what is pypdf2",
        "how to use pypdf2",
    ]
    
    print(f"\n2. Testing {len(test_queries)} queries...")
    print("-"*70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}: '{query}'")
        print("   " + "-"*66)
        
        answer = rag.get_rag_response(query)
        
        if answer and answer != "I don't know based on the provided documents.":
            print(f"   ✅ Got answer ({len(answer)} chars)")
            print(f"\n   Answer preview:")
            # Show first 200 chars
            preview = answer[:200] + "..." if len(answer) > 200 else answer
            for line in preview.split('\n'):
                print(f"   {line}")
        else:
            print(f"   ❌ No relevant answer: {answer}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_rag_queries()
