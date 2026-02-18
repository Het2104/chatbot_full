# 📚 Part 6: PDF Processing & OCR (app/services/pdf_processing_service.py)

## 🎯 What This Service Does

The PDF Processing Service handles the **offline part of RAG** (Steps 1-8):
1. Accept PDF uploads
2. Extract text (with OCR for scanned PDFs)
3. Clean the text
4. Split into chunks
5. Generate embeddings
6. Store in Milvus vector database

---

## 🔄 Complete PDF Processing Pipeline

```
User uploads PDF
        ↓
Step 1: Extract text from PDF
        ├─ Regular PDF → PyPDF2
        └─ Scanned PDF → Tesseract OCR
        ↓
Step 2: Clean text (remove extra spaces, special chars)
        ↓
Step 3: Split into chunks (small sections)
        ↓
Step 4: Generate embeddings for each chunk
        ↓
Step 5: Store chunks + embeddings in Milvus
        ↓
Ready for RAG queries!
```

---

## 📋 Complete Code Walkthrough

### **1. PDFProcessingService Class**

```python
class PDFProcessingService:
    """Service for processing PDFs and adding them to the vector store"""
    
    def __init__(self):
        self.embedder = None
        self.vector_store = None
```

**Why components start as None:**
- Heavy dependencies (embedding model, Milvus connection)
- Only loaded when actually processing a PDF
- Saves memory and startup time

---

### **2. Main Processing Function**

```python
def process_pdf(self, file_path: str, filename: str) -> Dict[str, Any]:
    """
    Process a single PDF file and add to vector store
    Uses OCR automatically for scanned/image-based PDFs
    """
```

---

#### **Step 1: Extract Text from PDF**

```python
# Try smart extraction (standard first, OCR fallback for scanned PDFs)
text = get_full_text_smart(file_path, use_ocr=True)
text_length = len(text.strip())
```

**What `get_full_text_smart()` does:**

1. **First try**: Standard extraction (PyPDF2)
   ```python
   text = extract_with_pypdf2(file_path)
   ```

2. **Check if enough text** was extracted
   ```python
   if len(text) < 50:  # Very little text
       # PDF might be scanned/image-based
   ```

3. **Auto-detect if OCR needed**
   ```python
   # Count characters per page
   chars_per_page = len(text) / num_pages
   
   if chars_per_page < 50:  # Sparse text
       # Use OCR automatically
       text = extract_with_ocr(file_path)
   ```

4. **OCR Extraction Process**
   ```
   PDF → Poppler converts to images → Tesseract extracts text
   ```

**Example Scenarios:**

| PDF Type | Text Extracted | Action |
|----------|----------------|--------|
| Regular PDF | 5,000 chars | Use as-is |
| Scanned PDF | 20 chars | Trigger OCR |
| Image-based | 0 chars | Trigger OCR |
| Encrypted | 0 chars | Error |

**Error Handling:**
```python
# Check if we got any text at all
if text_length == 0:
    raise ValueError(ocr_extraction_failed_error(OCR_AVAILABLE))

# Warn if very little text
if text_length < 50:
    logger.warning(f"Very little text extracted ({text_length} chars)")
```

---

#### **Step 2: Clean Text**

```python
cleaned = clean_text(text)
cleaned_length = len(cleaned)
```

**What `clean_text()` does:**

1. **Remove extra whitespace**
   ```python
   "Hello    world" → "Hello world"
   ```

2. **Normalize line breaks**
   ```python
   "Line1\r\n\r\n\r\nLine2" → "Line1\n\nLine2"
   ```

3. **Remove special characters**
   ```python
   "Text ︎ with ️ symbols" → "Text with symbols"
   ```

4. **Fix encoding issues**
   ```python
   "Café" → "Café"  (proper UTF-8)
   ```

**Validation:**
```python
if not cleaned or cleaned_length < 10:
    raise ValueError(
        f"Text too short after cleaning (from {text_length} to {cleaned_length} chars)"
    )
```

---

#### **Step 3: Create Chunks**

```python
chunks = chunk_document(cleaned, filename)
num_chunks = len(chunks)
```

**What `chunk_document()` does:**

Splits document into small, overlapping sections using **SENTENCE-BASED chunking**.

**Why chunk?**
- LLMs have token limits (can't process entire PDF at once)
- Smaller chunks = more precise retrieval
- Overlapping chunks = no information lost at boundaries

**Chunking Strategy: Sentence-Based**
```python
max_chars = 2000 characters     # Maximum CHARACTERS per chunk (~300 words)
overlap_sentences = 3 sentences # Number of SENTENCES to overlap

Strategy:
1. Split text by sentences (not by fixed character count)
2. Group sentences until we reach max_chars (2000 characters)
3. Keep last 3 sentences from previous chunk for context overlap
4. Create next chunk starting with those overlapping sentences

Example:
Chunk 1: [Sentence 1][Sentence 2][Sentence 3][Sentence 4][Sentence 5]
Chunk 2:                         [Sentence 3][Sentence 4][Sentence 5][Sentence 6][Sentence 7]
                                  ↑―――――――――overlap (3 sentences)―――――――――↑
```

**Example:**
```python
# Original text
text = """
Theory X assumes employees dislike work and avoid responsibility. 
Managers must closely supervise and control workers. Theory Y 
assumes employees are self-motivated and seek responsibility.
"""

# After chunking
chunks = [
    {
        'text': 'Theory X assumes employees dislike work and avoid responsibility. Managers must closely supervise...',
        'source_file': 'management.pdf',
        'chunk_index': 0,
        'start_char': 0,
        'end_char': 500
    },
    {
        'text': '...closely supervise and control workers. Theory Y assumes employees are self-motivated...',
        'source_file': 'management.pdf',
        'chunk_index': 1,
        'start_char': 450,  # Overlap with previous
        'end_char': 950
    },
    # ...
]
```

**Validation:**
```python
if num_chunks == 0:
    raise ValueError(
        f"No chunks created. Text length: {cleaned_length} chars. "
        "Document may be too short or fragmented."
    )
```

---

#### **Step 4: Generate Embeddings**

```python
embeddings = self.embedder.embed_chunks(chunks, show_progress=False)
```

**What this does:**
- Converts each chunk text to a 384-dimensional vector
- Uses sentence-transformers model (all-MiniLM-L6-v2)
- Captures semantic meaning

**Example:**
```python
chunk_1 = "Theory X assumes employees are lazy"
embedding_1 = [0.23, -0.45, 0.67, ..., 0.89]  # 384 numbers

chunk_2 = "Workers dislike work according to Theory X"
embedding_2 = [0.25, -0.43, 0.64, ..., 0.87]  # Similar to chunk_1!

chunk_3 = "How to make pizza"
embedding_3 = [-0.78, 0.12, -0.34, ..., 0.23]  # Very different!
```

**Processing Time:**
```python
# Typical speeds (on CPU)
50 chunks → ~5 seconds
100 chunks → ~10 seconds
500 chunks → ~50 seconds
```

---

#### **Step 5: Store in Milvus**

```python
self.vector_store.add_chunks(chunks, embeddings)
```

**What this does:**
- Inserts chunks and their embeddings into Milvus collection
- Creates index for fast similarity search
- Chunks are now searchable by RAG system

**Milvus Storage Structure:**
```
Collection: rag_chunks
├── id: auto-generated
├── chunk_id: unique identifier
├── text: chunk content
├── embedding: [384 floats]
├── source_file: PDF filename
├── chunk_index: position in document
```

---

### **3. Return Processing Results**

```python
return {
    "success": True,
    "filename": filename,
    "stats": {
        "text_length": text_length,
        "cleaned_length": cleaned_length,
        "num_chunks": num_chunks,
        "processing_time_seconds": processing_time
    }
}
```

**Example Success Response:**
```json
{
  "success": true,
  "filename": "company_handbook.pdf",
  "stats": {
    "text_length": 45230,
    "cleaned_length": 43180,
    "num_chunks": 87,
    "processing_time_seconds": 12.5
  }
}
```

**Example Error Response:**
```json
{
  "success": false,
  "filename": "scanned_doc.pdf",
  "error": "No text extracted from PDF. OCR not available.",
  "processing_time_seconds": 2.3
}
```

---

## 🔧 OCR (Optical Character Recognition)

### **What is OCR?**

OCR = Converting images to text

**Scanned PDF Example:**
```
Regular PDF:                Scanned PDF:
┌─────────────┐            ┌─────────────┐
│ Text        │            │ [Image of   │
│ is stored   │            │  text]      │
│ as text     │            │             │
└─────────────┘            └─────────────┘
   ↓                          ↓ OCR needed
Can easily                Must convert
extract text              image to text
```

### **OCR Dependencies**

**Tesseract** (OCR Engine):
```bash
# Reads images and extracts text
image.png → "Hello World"
```

**Poppler** (PDF to Image):
```bash
# Converts PDF pages to images
page1.pdf → page1.png → Tesseract → "text"
```

### **OCR Process Flow**

```
1. scanned_document.pdf
        ↓
2. Poppler: Convert PDF pages to images
   ├─ page_1.png
   ├─ page_2.png
   └─ page_3.png
        ↓
3. Tesseract: Extract text from each image
   ├─ "This is page 1 content..."
   ├─ "This is page 2 content..."
   └─ "This is page 3 content..."
        ↓
4. Combine all pages
   "This is page 1 content... This is page 2 content..."
```

### **Smart OCR Detection**

```python
def get_full_text_smart(file_path, use_ocr=True):
    # Try standard extraction first
    text = extract_with_pypdf2(file_path)
    
    # Calculate text density
    chars_per_page = len(text) / num_pages
    
    # If sparse text, assume scanned
    if use_ocr and chars_per_page < 50:
        logger.info("Sparse text detected, using OCR")
        text = extract_with_ocr(file_path)
    
    return text
```

---

## 🎓 Understanding the Complete Flow

### **Example: Processing "company_policy.pdf"**

1. **Upload** (via frontend/API)
   ```
   POST /api/upload/pdf
   File: company_policy.pdf (2.3 MB)
   ```

2. **Save to disk**
   ```
   Saved to: backend/data/raw_pdfs/company_policy.pdf
   ```

3. **Extract text**
   ```
   PyPDF2: SUCCESS
   Extracted: 45,230 characters
   ```

4. **Clean text**
   ```
   Before: 45,230 chars (with extra spaces, symbols)
   After:  43,180 chars (cleaned)
   ```

5. **Chunk document (Sentence-Based Strategy)**
   ```
   Max chars per chunk: 2000 characters
   Overlap: 3 sentences
   Result: 23 chunks
   ```

6. **Generate embeddings**
   ```
   Processing 87 chunks...
   Time: 8.7 seconds
   Created 87 embeddings (384 dimensions each)
   ```

7. **Store in Milvus**
   ```
   Inserted 87 chunks into collection 'rag_chunks'
   Total chunks in DB: 87
   ```

8. **Return success**
   ```json
   {
     "success": true,
     "stats": { "num_chunks": 87, "time": 12.5 }
   }
   ```

9. **Ready for queries!**
   ```
   RAG can now answer questions about company_policy.pdf
   ```

---

## 💡 Troubleshooting Common Issues

### **Issue 1: "No text extracted"**

**Cause:** PDF is scanned/image-based and OCR not installed

**Solution:**
```bash
# Install Tesseract and Poppler
# See OCR_SETUP.md for instructions
```

### **Issue 2: "Text too short after cleaning"**

**Cause:** PDF contains mostly images, tables, or special characters

**Solution:**
- Ensure PDF has actual text content
- Check if PDF is encrypted
- Try OCR if it's a scanned document

### **Issue 3: "No chunks created"**

**Cause:** Text is too short (< 50 characters minimum per chunk)

**Solution:**
- Upload PDFs with more content
- Check if text extraction worked properly

### **Issue 4: "Processing taking too long"**

**Cause:** 
- Large PDF (many pages)
- OCR processing is slow
- Many chunks to embed

**Solution:**
- Be patient (large PDFs take time)
- Consider splitting very large PDFs
- Use GPU for faster embedding (if available)

---

## 🔗 What's Next?

Now that you understand PDF processing:
- **Part 7**: Chat Service (how conversations work and integrate RAG)
- **Part 8**: API Routers (the endpoints that trigger all this)

---

## ❓ Quick Reference

**Processing Pipeline:**
```
PDF → Extract → Clean → Chunk → Embed → Store → Query
```

**File Flow:**
```
Upload → backend/data/raw_pdfs/ → Process → Milvus
```

**Typical Processing Times:**
```
Small PDF (10 pages, regular):    2-5 seconds
Medium PDF (50 pages, regular):   5-15 seconds
Large PDF (200 pages, regular):   30-60 seconds
Scanned PDF (10 pages, OCR):     20-40 seconds
```

**Dependencies:**
```
Text Extraction: PyPDF2
OCR: Tesseract + Poppler
Embeddings: sentence-transformers
Storage: Milvus
```

