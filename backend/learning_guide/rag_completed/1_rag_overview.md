# 1. RAG Overview (Retrieval-Augmented Generation)

## 📂 Relevant Files in Codebase
The core logic for RAG in this project is primarily located in:
1.  **`app/services/rag_service.py`** (The "Brain" / Orchestrator)
2.  **`app/rag/online/`** (Real-time search components)
    -   `query_embedder.py`
    -   `retriever.py`
    -   `generator.py`
3.  **`app/rag/offline/`** (Data preparation components)
    -   `document_loader.py`
    -   `chunker.py`
    -   `embedder.py`
4.  **`app/rag/storage/milvus_store.py`** (Database interaction)

---

## 🧠 What is RAG? (Retrieval-Augmented Generation)

Imagine you are taking an exam.
-   **Standard LLM (ChatGPT/Llama)** is like a student who memorized a textbook 2 years ago. They can answer general questions well, but they don't know about events from yesterday or your company's private specific documents.
-   **RAG** is like allowing that same student to take the exam with an **open book** (your specific PDF documents). When you ask a question, they first look up the relevant page in the book, read it, and then answer you based *only* on that information.

**In technical terms:**
RAG combines the power of a Large Language Model (LLM) with your own custom data. It retrieves relevant information from your database and "augments" (adds to) the prompt sent to the AI, so the AI can generate an accurate answer.

---

## ❓ Why Use This? (The "Pros")

### 1. **Accuracy & Grounding (No Hallucinations)**
*   **Problem:** LLMs sometimes make things up ("hallucinate") when they don't know the answer.
*   **RAG Solution:** By forcing the AI to use *only* the retrieved context (the specific text found in your PDFs), we drastically reduce lies. If the answer isn't in your document, the bot can say "I don't know" instead of guessing.

### 2. **Privacy & Security**
*   **Problem:** You can't train a public AI model (like GPT-4) on your company's secret financial data because that data might leak or become public.
*   **RAG Solution:** Your data stays in your local database (Milvus). We only send small, relevant snippets to the LLM for processing, not your entire database.

### 3. **Up-to-Date Information**
*   **Problem:** Re-training an AI model takes weeks and costs thousands of dollars.
*   **RAG Solution:** If your company policy updates today, you just upload the new PDF. The system indexes it in seconds, and the chatbot immediately knows the new answer. No re-training required.

---

## ⚠️ Why is it "Bad"? (The Challenges/Cons)

### 1. **"Garbage In, Garbage Out"**
*   **Explanation:** The AI is only as smart as the documents you give it. If your PDF is poorly written, scanned with bad OCR (unreadable text), or has conflicting information, the chatbot will give bad answers.
*   **Code Reference:** This is why `app/rag/offline/text_cleaner.py` is crucial—to try and clean up messy text before the AI sees it.

### 2. **Complexity**
*   **Explanation:** A simple chatbot is just one call to an API. RAG requires a whole "pipeline": loading PDFs -> chunking text -> embedding (converting to numbers) -> storing in a vector DB -> searching -> ranking -> generating. If any part breaks (e.g., the vector DB goes down), the whole feature fails.
*   **Code Reference:** See `RAGService` in `app/services/rag_service.py`. It has to coordinate 5-6 different steps just to answer one question.

### 3. **Latency (Speed)**
*   **Explanation:** Searching a database takes time. Adding the retrieved text to the prompt makes the prompt longer, which takes the LLM longer to process. RAG is always slower than a direct chat.
*   **Code Reference:** The `get_rag_response` function has multiple `await` or blocking calls which add milliseconds to the response time.

---

## 🔍 Detailed Component Explanation

### 1. The Orchestrator (`app/services/rag_service.py`)
**Analogy:** The Conductor of an orchestra.
*   **What it does:** It doesn't do the heavy lifting itself. It tells other parts what to do.
*   **Key Function:** `get_rag_response(user_question)`
*   **Flow:**
    1.  "Hey Embedder, turn this question into numbers!"
    2.  "Hey Retriever, find me documents matching these numbers!"
    3.  "Hey PromptBuilder, combine the question and these documents into a prompt!"
    4.  "Hey Generator, send this to the LLM and get the answer!"

### 2. The Embedder (`app/rag/online/query_embedder.py`)
**Analogy:** The Translator.
*   **What it does:** Computers don't understand English meanings; they understand numbers. The embedder converts "How do I reset my password?" into a list of 384 numbers (a vector) like `[0.1, -0.5, 0.8...]`.
*   **Why Important:** Words with similar meanings (e.g., "reset" and "change") get similar numbers, allowing us to find relevant answers even if keywords don't match exactly.

### 3. The Vector Database (Milvus / `app/rag/storage/milvus_store.py`)
**Analogy:** The High-Speed Library.
*   **What it does:** it stores the numerical representations (vectors) of your PDF sentences. It is optimized to perform "similarity searches" incredibly fast.
*   **Why use Milvus:** It's open-source, fast, and scalable.

### 4. The Generator (`app/rag/online/generator.py`)
**Analogy:** The Writer.
*   **What it does:** This is the interface to the LLM (Large Language Model), in your case, Groq (Llama 3).
*   **Why Important:** It takes the *messy* raw text retrieved from the database and writes a *clean*, human-readable answer.

---

## 💡 Important Concepts

### **Chunking** (`app/rag/offline/chunker.py`)
*   **Concept:** You can't feed an entire 100-page book to an LLM at once (it's too expensive and confuses the model).
*   **Solution:** We break the PDF into small "chunks" (e.g., 5-10 sentences).
*   **Why:** When we search, we find the specific *paragraph* that contains the answer, rather than retrieving the whole book.

### **Prompt Engineering** (`app/rag/online/prompt_builder.py`)
*   **Concept:** The strict instructions we give the AI.
*   **Example in Code:**
    ```text
    "You are a helpful assistant. Use ONLY the following context to answer the user's question. If you don't know, say 'I don't know'."
    ```
*   **Why:** This is the primary guardrail against hallucinations.

---

## ❓ Frequently Asked Questions (from a learner's perspective)

**Q: Can I just use a database like SQL?**
*   **A:** No. SQL is good for exact matches (e.g., Find user with ID=123). It is terrible at understanding *meaning*. If you search SQL for "dog", it won't find "puppy". Vector databases (used in RAG) understand that "dog" and "puppy" are related.

**Q: Is RAG hard to maintain?**
*   **A:** Moderately. The hardest part is usually keeping the data clean. If users upload low-quality PDFs, the chatbot will be bad. You need a process to vet documents before uploading.

**Q: Why Groq? Why not OpenAI?**
*   **A:** In this specific project, Groq is used because it is extremely fast and offers a free tier for Llama models. OpenAI is great but costs money per request.

