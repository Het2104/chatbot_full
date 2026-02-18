# 📚 Part 5: RAG Service - Answer Questions from PDFs (app/services/rag_service.py)

## 🎯 What RAG Does

**RAG = Retrieval-Augmented Generation**

Your RAG system allows the chatbot to answer questions based on uploaded PDF documents.

**Simple Example:**
- You upload a PDF about "Company Policies"
- User asks: "What is the vacation policy?"
- RAG finds relevant sections in the PDF and generates an answer

---

## 🔄 RAG Pipeline - Complete Flow

```
User Question: "What is Theory X?"
        ↓
Step 9: Convert question to embedding (vector)
        ↓
Step 10: Search Milvus for similar document chunks
        ↓
Step 11: Assemble context from top chunks
        ↓
Step 12: Build prompt with question + context
        ↓
Step 13: Send to LLM (Groq) to generate answer
        ↓
Step 14: Format and return answer
```

---

## 📋 Complete Code Walkthrough

### **1. RAGService Class Initialization**

```python
class RAGService:
    def __init__(
        self,
        min_score: float = RAG_DEFAULT_MIN_SCORE,  # 0.3
        top_k: int = RAG_DEFAULT_TOP_K,            # 5
        temperature: float = RAG_DEFAULT_TEMPERATURE  # 0.0
    ):
```

**Parameters Explained:**

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `min_score` | 0.3 | Only use chunks with 30%+ similarity |
| `top_k` | 5 | Retrieve top 5 most relevant chunks |
| `temperature` | 0.0 | LLM creativity (0 = factual, 1 = creative) |

**Similarity Score Examples:**
```python
0.9-1.0 = Almost identical text
0.7-0.9 = Very relevant
0.5-0.7 = Somewhat relevant
0.3-0.5 = Slightly relevant
0.0-0.3 = Not relevant (filtered out)
```

---

### **2. Lazy Initialization**

```python
def _initialize(self):
    """Lazy initialization of RAG components."""
    if self._initialized:
        return
    
    try:
        # Initialize components
        self._embedder = get_query_embedder()
        self._retriever = get_retriever()
        self._generator = get_generator()
        
        self._initialized = True
        logger.info("RAG service ready")
        
    except Exception as e:
        logger.error(f"RAG initialization failed: {e}")
        self._initialized = False
```

**What "Lazy Initialization" Means:**
- Components are NOT initialized when RAGService is created
- They're initialized only when first needed
- This speeds up app startup

**Why it's useful:**
- If Milvus is down, app still starts (RAG just won't work)
- If no one uses RAG, no resources are wasted

---

### **3. Main Function: get_rag_response()**

This is the complete RAG pipeline in one function.

#### **Step 9: Embed the User's Question**

```python
# Convert question text to vector
query_embedding = self._embedder.embed_query(user_question)
```

**What this does:**
- Takes text: "What is Theory X?"
- Converts to 384-dimensional vector: `[0.123, -0.456, 0.789, ...]`
- This vector represents the semantic meaning of the question

**Example:**
```python
"What is Theory X?" → [0.12, -0.34, 0.56, 0.78, ...]
"Theory X definition" → [0.13, -0.33, 0.54, 0.77, ...]  # Similar!
"How to cook pasta" → [-0.89, 0.23, -0.45, 0.12, ...]  # Different!
```

---

#### **Step 10: Retrieve Relevant Chunks**

```python
chunks = self._retriever.retrieve(
    query_embedding=query_embedding,
    top_k=self.top_k,        # Get top 5 chunks
    min_score=self.min_score  # Only if score >= 0.3
)
```

**What this does:**
- Searches Milvus vector database
- Finds chunks with embeddings similar to the query embedding
- Returns top 5 chunks with highest similarity scores

**Example result:**
```python
chunks = [
    {
        'text': 'Theory X assumes employees are lazy...',
        'score': 0.87,
        'source_file': 'management_theories.pdf',
        'chunk_index': 5
    },
    {
        'text': 'McGregor introduced Theory X in 1960...',
        'score': 0.82,
        'source_file': 'management_theories.pdf',
        'chunk_index': 6
    },
    # ... 3 more chunks
]
```

**If no chunks found:**
```python
if not chunks or len(chunks) == 0:
    return NO_RELEVANT_DOCS_MESSAGE  # "I don't know based on the provided documents."
```

---

#### **Step 11: Assemble Context**

```python
context = assemble_context(
    chunks,
    include_scores=False,
    include_sources=True
)
```

**What this does:**
- Combines all chunks into one text block
- Adds source information (which PDF)
- Removes duplicate information

**Example output:**
```
[Source: management_theories.pdf]
Theory X assumes employees are inherently lazy and dislike work. 
McGregor introduced Theory X in 1960 as part of his management theory.
Managers using Theory X tend to micromanage and use strict control.
...
```

---

#### **Step 12: Build Prompt**

```python
prompt = build_prompt(
    question=user_question,
    context=context,
    prompt_type="strict"
)
```

**What this does:**
- Creates a prompt for the LLM
- Includes the user's question
- Includes the retrieved context
- Sets instructions for how to answer

**Example prompt:**
```
You are a helpful assistant. Answer the question based ONLY on the provided context.
If the answer is not in the context, say "I don't know based on the documents."

Context:
[Source: management_theories.pdf]
Theory X assumes employees are inherently lazy...

Question:
What is Theory X?

Answer:
```

**Prompt Types:**
- `"strict"`: Answer only from context (default)
- `"flexible"`: Can use general knowledge too

---

#### **Step 13: Generate Answer with LLM**

```python
llm_answer = self._generator.generate(
    prompt=prompt,
    temperature=self.temperature  # 0.0 = deterministic
)
```

**What this does:**
- Sends prompt to Groq API (Llama 3.1 70B model)
- Gets AI-generated answer
- Temperature controls creativity

**Temperature Effects:**
```python
temperature=0.0  # Same answer every time (factual)
temperature=0.5  # Slightly varied answers
temperature=1.0  # Creative, different answers
```

---

#### **Step 14: Format Response**

```python
formatted_answer = format_response_simple(llm_answer)
```

**What this does:**
- Cleans up the LLM response
- Removes extra whitespace
- Ensures proper formatting

---

### **4. Check RAG Availability**

```python
def is_available(self) -> bool:
    """Check if RAG system is available and working."""
    self._initialize()
    return self._initialized
```

**When RAG is NOT available:**
- Milvus is not running
- Groq API key is missing or invalid
- No PDFs have been uploaded

---

### **5. Singleton Pattern**

```python
_rag_service_instance: Optional[RAGService] = None

def get_rag_service(reinit: bool = False) -> RAGService:
    """Get or create singleton RAG service instance."""
    global _rag_service_instance
    
    if _rag_service_instance is None or reinit:
        _rag_service_instance = RAGService()
    
    return _rag_service_instance
```

**What "Singleton" Means:**
- Only ONE instance of RAGService exists
- All requests share the same instance
- This saves memory and initialization time

**Usage:**
```python
# First call: Creates the instance
rag = get_rag_service()

# Second call: Returns the SAME instance
rag2 = get_rag_service()  # rag2 is rag == True
```

---

## 🎓 How RAG Answers a Question - Example

**User asks:** "What are the features of PyPDF2?"

### **Step-by-Step:**

1. **Embed Query**
   ```
   "What are the features of PyPDF2?" 
   → [0.23, -0.45, 0.67, ..., 0.89]  (384 numbers)
   ```

2. **Search Milvus**
   ```
   Find chunks with similar embeddings:
   - Chunk 1: "PyPDF2 can extract text from PDFs..." (score: 0.89)
   - Chunk 2: "Main features include merging PDFs..." (score: 0.85)
   - Chunk 3: "PyPDF2 supports PDF encryption..." (score: 0.78)
   ```

3. **Assemble Context**
   ```
   [Source: pypdf2_documentation.pdf]
   PyPDF2 can extract text from PDFs. Main features include merging 
   PDFs, splitting PDFs, rotating pages, and encrypting documents.
   PyPDF2 supports PDF encryption and watermarking...
   ```

4. **Build Prompt**
   ```
   Answer the question based on the context:
   
   Context: [PyPDF2 features text...]
   Question: What are the features of PyPDF2?
   ```

5. **LLM Generates Answer**
   ```
   "PyPDF2 is a Python library with several key features:
   1. Extract text from PDF documents
   2. Merge multiple PDFs into one
   3. Split PDFs into separate files
   4. Rotate PDF pages
   5. Encrypt and decrypt PDFs
   6. Add watermarks..."
   ```

6. **Format and Return**
   ```
   Clean up, return to user
   ```

---

## 🔧 How RAG Integrates with Chat

In `chat_service.py`:

```python
def process_message(session_id, user_message, db):
    # Try workflow match first
    workflow_response = _find_workflow_response(...)
    if workflow_response:
        return workflow_response
    
    # Try FAQ match
    faq_response = _find_faq_response(...)
    if faq_response:
        return faq_response
    
    # Try RAG if no workflow/FAQ match
    rag_response = _find_rag_response(user_message, db)
    if rag_response:
        return rag_response
    
    # Fallback to default
    return DEFAULT_BOT_RESPONSE
```

**Priority Order:**
1. Exact workflow match (highest priority)
2. Exact FAQ match
3. RAG semantic search (if available)
4. Default response (fallback)

---

## 💡 Configuration Options

### **Adjust Retrieval Quality**

```python
# More strict (fewer but more relevant results)
rag = RAGService(
    min_score=0.5,  # Higher threshold
    top_k=3         # Fewer chunks
)

# More lenient (more results, some less relevant)
rag = RAGService(
    min_score=0.2,  # Lower threshold
    top_k=10        # More chunks
)
```

### **Adjust LLM Behavior**

```python
# Factual and consistent
rag = RAGService(temperature=0.0)

# More creative/varied
rag = RAGService(temperature=0.7)
```

---

## 🔗 What's Next?

Now that you understand how RAG works:
- **Part 6**: PDF Processing (how PDFs are uploaded and prepared for RAG)
- **Part 7**: Chat Service (how all pieces work together in conversations)

---

## ❓ Common Questions

**Q: Why doesn't RAG work for all questions?**
A: RAG only works if:
- PDFs are uploaded and indexed
- Question is related to PDF content
- Similarity score is high enough

**Q: Can RAG answer without uploading PDFs?**
A: No! RAG needs documents to search. Without PDFs, it returns "I don't know based on the provided documents."

**Q: How do I improve RAG accuracy?**
A: 
1. Upload more comprehensive PDFs
2. Adjust `min_score` threshold
3. Increase `top_k` to consider more chunks
4. Use better quality PDFs (not scanned)

**Q: What happens if Milvus is down?**
A: RAG gracefully fails. Chat still works but falls back to workflow/FAQ/default responses.

