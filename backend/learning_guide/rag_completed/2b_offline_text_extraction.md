# 2b. Offline Process: Smarter Text Extraction (Step 3)

## 📂 Relevant Files
1.  **`app/rag/offline/text_extractor.py`** (The Advanced Extractor)

---

## 📷 Step 3: Text Extraction & OCR

### **What is it?**
Sometimes, a PDF file is just a **picture** of text (like a scanned invoice). Standard tools (like `pdfplumber`) look at it and see *nothing* but an image.
To read this, we need **OCR** (Optical Character Recognition). It's "computer vision" for text.

### **The Code: `text_extractor.py`**
This module is smarter than the simple loader. It has a "fallback" mechanism.

#### **The "Smart" Logic (`extract_text_with_fallback`):**
1.  **Try Standard Way:** First, it tries to read the text normally.
2.  **Check for "Sparseness":** It counts the words.
    *   If it finds plenty of text -> Great, we are done. (Fast)
    *   If it finds *almost no text* (or just gibberish) -> It assumes the page is an image.
3.  **Activate OCR:** If the page seems empty, it calls `extract_with_ocr`.
    *   Converts the PDF page to an **Image** (PNG/JPG).
    *   Uses **Tesseract** (an AI tool) to read the text from that image.

### **Key Functions:**

#### **1. `is_text_sparse(text)`**
Decides if the page is "empty enough" to need OCR.
*   **Logic:** If a page has fewer than 50 characters or very few real words, return `True` (needs OCR).

#### **2. `extract_with_ocr(pdf_path)`**
*   **Tools Used:** `pdf2image` (converts PDF to image) and `pytesseract` (reads the image).
*   **Result:** Turns a picture of a document into actual string text.

---

## ⚠️ Why is it "Bad" or Difficult?

### **1. Speed (Slowness)**
*   **Explanation:** Standard extraction takes **0.1 seconds**. OCR extraction takes **2-5 seconds per page**.
*   **Impact:** If you upload a 100-page scanned document, it might take 10 minutes to process instead of 10 seconds.

### **2. Accuracy**
*   **Problem:** OCR typically makes mistakes like confusing `1` and `l`, or `0` and `O`.
*   **Result:** "The bi11 is d0" instead of "The bill is due". This confuses the RAG search.

### **3. Dependencies (Installation Hell)**
*   **Problem:** You can't just `pip install` this. You need to install **Tesseract** software and **Poppler** software on your actual Windows/Linux machine.
*   **Code Reference:** `check_ocr_setup()` tries to help debug if these are missing.

---

## ❓ Frequently Asked Questions

**Q: Do I need this if my PDFs are digital?**
*   **A:** No. If your PDFs were created in Word/Google Docs ("Export to PDF"), standard extraction works perfectly. This is only for scanned papers or "flattened" PDFs.

**Q: What is DPI?**
*   **A:** dots per inch. It's the quality of the image we create before reading it.
    *   Higher DPI (300) = Better reading, Slower speed.
    *   Lower DPI (150) = Faster speed, More mistakes.
    *   We default to **300 DPI**.

