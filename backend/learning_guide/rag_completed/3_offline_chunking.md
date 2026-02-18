# 3. Offline Process: Chunking (Step 5)

## 📂 Relevant Files
1.  **`app/rag/offline/chunker.py`**

---

## 🍰 Step 5: Text Chunking

### **What is it?**
Imagine trying to swallow a whole watermelon. You can't. You have to slice it into bite-sized pieces.
"Chunking" is splitting your long documents into smaller, manageable pieces ("chunks") that fit into the AI's memory.

### **The Code: `chunker.py`**
This file takes the long, cleaned text string and cuts it up.

#### **Key Function: `chunk_text`**
```python
def chunk_text(text: str, max_chars: int = 2000, overlap_sentences: int = 3) -> List[TextChunk]:
    # ... logic to split text ...
```

**Parameter Explanation:**
- `max_chars=2000`: Maximum **CHARACTERS** per chunk (~300 words)
- `overlap_sentences=3`: Number of **SENTENCES** to overlap between chunks

### **Strategy Used: "Sentence-Based Chunking"**
There are many ways to chunk (by character count, by paragraph). We use **Sentence-Based Chunking**.

1.  **Split into sentences first:** We use logic to find periods (`.`), question marks (`?`), etc.
2.  **Group sentences:** We add sentence 1, then sentence 2, then sentence 3... until we reach `max_chars` (e.g., 2000 **characters**).
3.  **Create Chunk:** That group becomes "Chunk 1".
4.  **Overlap:** This is the secret sauce (we keep last 3 **sentences** from previous chunk).

### **The "Overlap" Concept (Crucial!)**
We don't just cut cleanly. We include the *last few sentences* of Chunk 1 at the *beginning* of Chunk 2.

*   **Why?** Context.
*   **Example without overlap:**
    *   Chunk 1 ends with: "The password is..."
    *   Chunk 2 starts with: "...12345."
    *   **Problem:** If we search for "password", we find Chunk 1, but it doesn't have the answer. If we search for "12345", we find Chunk 2, but we don't know what it's for.
*   **Example WITH overlap:**
    *   Chunk 1: "...The password is 12345."
    *   Chunk 2: "The password is 12345. Please keep it safe..."
    *   **Result:** Both chunks contain the complete thought.

### **Why is this "Bad" or Difficult?**
*   **Cutting the thought:** Even with overlap, you might cut a very long explanation in half.
*   **Size matters:**
    *   **Too small:** The AI lacks context ("It says 'yes'", but 'yes' to what?).
    *   **Too big:** You confuse the AI with too much irrelevant info, and it fills up the "Context Window" (memory limit).

---

## ❓ Frequently Asked Questions

**Q: Why 2000 characters?**
*   **A:** It's a balance. It's roughly 300-400 words. Enough to contain a full concept, but small enough to retrieve multiple chunks without hitting limits.

**Q: Do we split words in half?**
*   **A:** No. Because we split by *sentence* first, we never cut a word in the middle. Simpler chunkers (character-based) might cut "Apple" into "Ap-" and "-ple", which destroys the meaning. This code is smarter than that.

