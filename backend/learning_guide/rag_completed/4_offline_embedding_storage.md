# 4. Offline Process: Embedding & Storage (Steps 6-7)

## 📂 Relevant Files
1.  **`app/rag/offline/embedder.py`** (Turning text into numbers)
2.  **`app/rag/storage/milvus_store.py`** (Saving to database)

---

## 🔢 Step 6: Embedding Generation

### **What is it?**
This is the magic translation layer. Computers cannot "read". They only understand math.
An **Embedding Model** is a special AI that reads text and turns it into a list of numbers (a "vector").

*   Input: "The dog barked."
*   Output: `[0.12, -0.98, 0.45, ...]` (384 numbers long)

Text with similar *meanings* will have similar *numbers*.
*   "The canine made a sound" -> `[0.11, -0.99, 0.46, ...]` (**Very close numbers**)
*   "The car is red" -> `[0.88, 0.12, -0.33, ...]` (**Very different numbers**)

### **The Code: `embedder.py`**
We use a library called `sentence-transformers`.

#### **Key Function: `embed_chunks`**
```python
def embed_chunks(self, chunks: List, ...):
    texts = [chunk.text for chunk in chunks]
    return self.model.encode(texts)
```

**The Model We Use:** `all-MiniLM-L12-v2`
*   **Why use this?** It is a "Small but Mighty" model.
*   It's fast (runs on CPU).
*   It's free (Open Source).
*   It creates 384-dimensional vectors.

---

## 💾 Step 7: Vector Storage (Milvus)

### **What is it?**
Now that we have thousands of lists of numbers (vectors), we need a place to save them. Standard databases (like PostgreSQL or MySQL) are bad at searching through lists of numbers.
We use a **Vector Database** called **Milvus**.

### **The Code: `milvus_store.py`**
This file manages the connection to the Milvus server (running in Docker).

#### **Key Function: `add_chunks`**
It saves 4 main things for every chunk:
1.  **Chunk ID:** A unique number (1, 2, 3...)
2.  **Embedding:** The vector `[0.12, ...]` (Used for searching)
3.  **Original Text:** "The dog barked..." (Used for reading later)
4.  **Metadata:** Source filename, page number.

#### **Key Function: `create_index`**
Just like a book index makes looking up words fast, a vector index makes comparing numbers fast. We use an index type called `IVF_FLAT`.

---

## ⚠️ Why is it "Bad" or Difficult?

### **1. Dimension Mismatches**
*   **Problem:** If you use Model A (384 dimensions) to save data, but Model B (768 dimensions) to search, the code crashes.
*   **Solution:** You must use the *exact same model* for saving and searching.

### **2. "Drift"**
*   **Problem:** If you update your embedding model to a better one next year, all your old stored vectors are useless. You have to re-process (re-embed) *every document* in your database.

### **3. Infrastructure**
*   **Problem:** Milvus is complex. It runs on Docker. If Docker crashes, your RAG system dies. It's "heavy" software.

---

## ❓ Frequently Asked Questions

**Q: Can I see the vector?**
*   **A:** Yes, it's just a long array of floats (decimals). But it looks like random noise to a human.

**Q: Why Milvus and not Pinecone/Chroma?**
*   **A:**
    *   **Pinecone:** Expensive (Closed source SaaS).
    *   **Chroma:** Good for simple apps, but Milvus handles millions of vectors better (Production grade).
    *   **Milvus:** Open source (Free), runs locally (Private), very fast.

