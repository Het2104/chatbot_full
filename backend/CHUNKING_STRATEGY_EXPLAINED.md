# 📖 Chunking Strategy Explained

## ⚙️ Our Strategy: **SENTENCE-BASED CHUNKING**

### 🎯 Two Different Measurements (DO NOT CONFUSE!)

#### 1️⃣ **max_chars = 2000** (CHARACTERS)
- **Purpose:** Limits the SIZE of each chunk
- **Unit:** CHARACTERS (not sentences!)
- **Why 2000?** 
  - ~300 words per chunk
  - ~250 tokens (AI model limit)
  - Balances context vs. precision

#### 2️⃣ **overlap_sentences = 3** (SENTENCES)
- **Purpose:** Provides CONTEXT between chunks
- **Unit:** SENTENCES (not characters!)
- **Why 3 sentences?**
  - Enough to maintain context
  - Not too much redundancy
  - Prevents information loss at boundaries

---

## 🔧 How It Works (Step-by-Step)

### Example Text:
```
[Sentence 1] Our company was founded in 1990.
[Sentence 2] We started with just 5 employees.
[Sentence 3] Today we have 500 staff worldwide.
[Sentence 4] Our headquarters is in New York.
[Sentence 5] We have offices in 10 countries.
[Sentence 6] Our revenue grew 25% last year.
[Sentence 7] We focus on customer satisfaction.
```

### Process:

**Step 1:** Split into sentences ✅
```
✓ 7 sentences detected
```

**Step 2:** Group sentences until reaching max_chars (2000 characters)
```
Chunk 1:
  [Sentence 1] Our company was founded in 1990.
  [Sentence 2] We started with just 5 employees.
  [Sentence 3] Today we have 500 staff worldwide.
  [Sentence 4] Our headquarters is in New York.
  [Sentence 5] We have offices in 10 countries.
  
  Total: 189 characters (< 2000 ✓)
```

**Step 3:** Create next chunk with 3-sentence overlap
```
Chunk 2 (starts with last 3 sentences from Chunk 1):
  [Sentence 3] Today we have 500 staff worldwide.        ← overlap
  [Sentence 4] Our headquarters is in New York.          ← overlap  
  [Sentence 5] We have offices in 10 countries.          ← overlap
  [Sentence 6] Our revenue grew 25% last year.           ← new
  [Sentence 7] We focus on customer satisfaction.        ← new
  
  Total: 178 characters (< 2000 ✓)
```

---

## 📊 Configuration Values (Consistent Everywhere)

### In `app/config.py`:
```python
CHUNK_SIZE: int = 2000              # Maximum CHARACTERS per chunk
CHUNK_OVERLAP_SENTENCES: int = 3   # Number of SENTENCES to overlap
```

### In `app/rag/offline/chunker.py`:
```python
def chunk_text(
    text: str,
    max_chars: int = 2000,          # Maximum CHARACTERS per chunk
    overlap_sentences: int = 3,     # Number of SENTENCES to overlap
    min_chunk_chars: int = 100      # Minimum CHARACTERS for valid chunk
) -> List[TextChunk]:
    ...
```

### In `app/rag/offline/chunker.py`:
```python
def chunk_document(
    text: str,
    source_file: str = "",
    max_chars: int = 2000,          # Maximum CHARACTERS per chunk
    overlap_sentences: int = 3      # Number of SENTENCES to overlap
) -> List[TextChunk]:
    ...
```

---

## ✅ Why These Values?

### max_chars = 2000 (characters)
- ✅ ~300 words = good context size
- ✅ ~250 tokens = fits in AI model
- ✅ Not too small (loses context)
- ✅ Not too large (loses precision)

### overlap_sentences = 3 (sentences)
- ✅ Maintains context across chunks
- ✅ Prevents split thoughts/ideas
- ✅ Not too much redundancy (3-5 is optimal)
- ✅ Better retrieval accuracy

---

## 🚫 Common Mistakes (AVOID!)

### ❌ **WRONG:** `overlap_sentences = 200`
- **Problem:** 200 SENTENCES is way too much!
- **Impact:** Chunks would be 99% duplicate
- **Correct:** Should be 2-5 sentences

### ❌ **WRONG:** `max_chars = 3` 
- **Problem:** Confusing characters with sentences
- **Impact:** Tiny 3-character chunks unusable
- **Correct:** 2000 characters is right

---

## 📈 Tuning Guide

### If chunks are TOO LARGE:
```python
max_chars = 1500  # Reduce character limit
```

### If chunks are TOO SMALL:
```python
max_chars = 2500  # Increase character limit
```

### If losing context between chunks:
```python
overlap_sentences = 5  # More overlap sentences
```

### If too much redundancy:
```python
overlap_sentences = 2  # Fewer overlap sentences
```

---

## 📁 Files Configured Consistently

All these files now use the SAME values:

1. ✅ `app/config.py` - Configuration constants
2. ✅ `app/rag/offline/chunker.py` - Chunking implementation
3. ✅ `learning_guide/06_PDF_Processing_README.md` - Documentation
4. ✅ `learning_guide/rag_completed/3_offline_chunking.md` - Tutorial

**All values are now CONSISTENT across the entire codebase! 🎉**
