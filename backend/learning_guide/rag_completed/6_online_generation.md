# 6. Online Process: Context, Prompting & Generation (Steps 11-13)

## 📂 Relevant Files
1.  **`app/rag/online/context_builder.py`** (Stitching text together)
2.  **`app/rag/online/prompt_builder.py`** (Creating instructions)
3.  **`app/rag/online/generator.py`** (Talking to the AI)

---

## 🧩 Step 11: Context Assembly

### **What is it?**
We found 5 relevant chunks (Step 10). Now we need to glue them together into one readable block of text to show the AI.

### **The Code: `context_builder.py`**
It takes the list of chunks and formats them nicely.
```text
[Source: manual.pdf]
Step 1 is to restart the computer.

[Source: troubleshooting.pdf]
If restart fails, check the power cable.
```

---

## 📝 Step 12: Prompt Building (The Most Important Part!)

### **What is it?**
This is where we "brainwash" the AI to follow our rules. We wrap the user's question in a strict set of instructions.

### **The Code: `prompt_builder.py`**

#### **The Strict Template:**
```python
STRICT_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based ONLY on the provided context.

CRITICAL RULES:
1. Answer ONLY using information explicitly stated in the context below
2. If the context does not contain enough information, respond EXACTLY with: "I don't know based on the available information."
3. Do NOT use external knowledge.

CONTEXT:
{context}

USER QUESTION:
{question}
"""
```

### **Why so strict?**
*   **Hallucination Prevention:** If we just asked "What does the document say?", the AI might use its own training data (ChatGPT knowledge) to fill in gaps. We don't want that. We want *only* what is in *your* PDF.
*   **"I Don't Know":** We explicitly tell it to admit ignorance. This is better than a wrong guess.

---

## 🤖 Step 13: Generation (The LLM)

### **What is it?**
Sending the final prompt to the brain (Groq / Llama 3) to write the English response.

### **The Code: `generator.py`**
This connects to the Groq API.

#### **Key Parameter: `temperature=0.0`**
*   **Creativity (Temperature):**
    *   **1.0:** Highly creative, writes poems, might make things up.
    *   **0.0:** Cold, calculating, factual.
*   **For RAG:** We ALWAYS use **0.0**. We want facts, not fiction.

### **Groq vs. Others**
*   We use **Groq** because it runs Llama 3 at **300+ tokens per second**. It feels instant to the user. Standard GPT-4 might take 5-10 seconds to read the prompt and answer.

---

## ❓ Frequently Asked Questions

**Q: Can it answer questions about two different PDFs at once?**
*   **A:** **Yes!** If Chunk 1 comes from "Policy A.pdf" and Chunk 2 comes from "Policy B.pdf" and they are both in the "Top 5", the `context_builder` puts them both in the prompt. The AI reads both and synthesizes the answer.

**Q: What is the "Context Window"?**
*   **A:** The AI has a memory limit (e.g., 8,000 words). If we try to feed it 50 chunks, it will cut off the end or crash. This is why we stick to `top_k=5` — to stay safely inside the limit.

