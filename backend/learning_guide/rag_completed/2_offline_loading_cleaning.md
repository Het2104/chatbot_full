# 2. Offline Process: PDF Loading & Cleaning (Steps 1-4)

## 📂 Relevant Files
1.  **`app/rag/offline/document_loader.py`** (Loading PDFs)
2.  **`app/rag/offline/text_cleaner.py`** (Cleaning Text)

---

## 🏗️ Step 1-2: Document Ingestion (Loading PDFs)

### **What is it?**
Before the chatbot can answer questions, it needs to read the books. "Ingestion" is simply the process of opening your PDF files and extracting the raw text from them.

### **The Code: `document_loader.py`**
This file handles finding PDF files in a folder and using a library called `pdfplumber` to read them.

#### **Key Function: `load_pdfs_from_folder`**
```python
def load_pdfs_from_folder(folder_path": str) -> List[DocumentInfo]:
    # ... checks if folder exists ...
    pdf_files = list(folder.glob("*.pdf"))
    # ... loops through files and loads them ...
```
*   **Why use `pdfplumber`?** It is better than other libraries (like PyPDF2) at handling complex layouts and extracting tables.
*   **Output:** It returns a list of `DocumentInfo` objects containing the filename and page count.

#### **Key Function: `extract_text_from_pdf`**
```python
def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
    # ... opens the PDF ...
    text = page.extract_text()
    # ... returns a dictionary: {page_1: "text...", page_2: "text..."}
```

---

## 🧹 Step 3-4: Text Cleaning

### **What is it?**
PDFs are built for *printing*, not for computers to read. They are often full of "garbage" like:
*   Page numbers ("Page 1 of 10")
*   Headers/Footers ("Confidential - Do Not Distribute")
*   Weird line breaks (lines split in the middle of sentences)
*   Extra spaces

If we feed this garbage to the AI, it gets confused. Cleaning makes the text smooth and readable.

### **The Code: `text_cleaner.py`**

#### **Key Function: `clean_text`**
This function applies a series of "scrubbing" operations to the text.

```python
def clean_text(raw_text: str, preserve_structure: bool = True) -> str:
    # 1. Normalize whitespace (fix line breaks)
    text = normalize_whitespace(text)
    # 2. Fix artifacts (remove weird characters)
    text = fix_pdf_artifacts(text)
    # 3. Clean punctuation (remove ".....")
    text = clean_punctuation(text)
    return text
```

### **Why is this "Bad" or Difficult?**
*   **Over-cleaning:** If you are too aggressive, you might accidentally merge two separate paragraphs into one massive wall of text.
*   **Under-cleaning:** If you leave in "Page 12", the AI might think "Page 12" is part of a sentence.
*   **Tables:** cleaning text from tables is notoriously difficult because the visual structure (rows/columns) is lost when extracted as plain text.

### **Specific Cleaning Tricks in our Code:**
1.  **`fix_pdf_artifacts`**: Removes invisible characters and "soft hyphens" (hyphens used only for line wrapping).
2.  **`normalize_whitespace`**: Changes multiple newlines to a paragraph break, but joins single newlines (fixing sentences split across lines).

---

## ❓ Frequently Asked Questions

**Q: Why not one giant text file?**
*   **A:** We keep track of page numbers and filenames so we can tell the user *where* the answer came from later (e.g., "Source: EmployeeHandbook.pdf, Page 12").

**Q: Can it read scanned images?**
*   **A:** No. `pdfplumber` only reads "text-based" PDFs. If you have a scanned image of a document, you need **OCR** (Optical Character Recognition) to convert the image to text first. Our current code does not do OCR.

