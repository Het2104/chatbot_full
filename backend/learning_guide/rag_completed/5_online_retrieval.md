# 5. Online Process: Retrieval (Step 10)

## 📂 Relevant Files
1.  **`app/rag/online/retriever.py`** (Searching the database)
2.  **`app/rag/online/query_embedder.py`** (Converting question to numbers)

---

## 🔎 Step 10: Similarity Search

### **What is it?**
When a user asks "What is Theory X?", we need to find the specific page in our PDF that talks about Theory X.
This "Google Search" for our database is called **Retrieval**.

### **The Code: `retriever.py`**
This file connects to Milvus and runs the search command.

#### **Key Function: `retrieve`**
```python
def retrieve(self, query_embedding, top_k=5, min_score=0.3):
    # ... searches Milvus ...
    return results
```

### **Crucial Parameters:**

1.  **`query_embedding`**: The user's question converted into a list of numbers (by `query_embedder.py`).
2.  **`top_k=5`**: This means "Bring me the **Top 5** best matches."
    *   *Why not 1?* The best visual match might not be the best answer. We give the LLM a few options to read.
    *   *Why not 100?* Too much reading for the LLM (expensive and confuses it).
3.  **`min_score=0.3`** (The "Bouncer"):
    *   This is a threshold (0.0 to 1.0).
    *   If the best match has a score of `0.1` (terrible match), we ignore it and say "I don't know."
    *   **Goal:** Prevent the AI from trying to answer a question using an unrelated document.

### **The Math: Cosine Similarity**
*   **0.0:** Totally unrelated ("Dog" vs "Car").
*   **0.5:** Somewhat related ("Dog" vs "Cat").
*   **1.0:** Identical ("Dog" vs "Dog").

Our code checks if the `score` is greater than `min_score` (default 0.3).

---

## ⚠️ Why is it "Bad" or Difficult?

### **1. The "Keyword Match" Problem**
*   **User asks:** "How to fix the blue screen?"
*   **Document says:** "system crash recovery guide."
*   **Result:** A keyword search (Ctrl+F) would fail.
*   **RAG Solution:** Vector search *understands* that "blue screen" and "system crash" are semantically similar.

### **2. The "Distractor" Problem**
*   **Scenario:** You have two documents. One about "2020 Policy" and one about "2024 Policy".
*   **Risk:** The retriever might find the 2020 policy because it uses similar words.
*   **Solution:** We need "Metadata Filtering" (filtering by filename or date) to ensure we get the *right* version. Our current code validates the match score, but advanced RAG often adds date filters.

---

## ❓ Frequently Asked Questions

**Q: What if the user asks "Hello"?**
*   **A:** The `retriever` will likely find *nothing* relevant (score < 0.3), or it might find a random sentence. This is why we have the `min_score`. If the score is low, we ignore the results.

**Q: Is it fast?**
*   **A:** Yes! Milvus uses an index (`IVF_FLAT`) which makes searching millions of vectors happen in milliseconds (0.05 seconds).

