# OCR Setup Guide for Image-based PDFs

## Problem
When uploading PDFs with images/scanned text, no chunks are detected because standard text extraction returns empty/sparse results.

## Solution
The text extractor now has **enhanced OCR detection** that automatically:
1. Tries standard PDF text extraction first
2. Detects sparse/empty results using multiple heuristics
3. Automatically triggers OCR conversion (PDF → Image → Text)
4. Provides detailed logging for debugging

## Required Components

### 1. Python Packages
```bash
pip install pytesseract pdf2image Pillow
```

### 2. Tesseract OCR (Text Recognition Engine)

**Windows:**
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Get the latest installer (e.g., `tesseract-ocr-w64-setup-5.3.3.exe`)
- Install to default location: `C:\Program Files\Tesseract-OCR`
- The installer will add it to PATH automatically

**Verify installation:**
```bash
tesseract --version
```

### 3. Poppler (PDF Renderer)

**Windows:**
- Download: https://github.com/oschwartz10612/poppler-windows/releases/
- Get `Release-24.02.0-0.zip` (or latest)
- Extract to `C:\poppler`
- Ensure `C:\poppler\Library\bin\pdftoppm.exe` exists

**No need to add to PATH** - the code will find it automatically in:
- `C:\poppler\Library\bin`
- `C:\Program Files\poppler\Library\bin`
- Other standard locations

## Quick Check

Run the setup checker:
```bash
cd c:\chatbot\backend
python check_ocr_setup.py
```

This will:
- ✅ Check if Python packages are installed
- ✅ Verify Tesseract executable is found
- ✅ Verify Poppler is found
- ✅ Run a test OCR operation

## What Changed

### Enhanced OCR Detection (`text_extractor.py`)

**Better sparse text detection:**
- Increased minimum character threshold (50 → 100)
- Checks for readable words (needs 5+ words with 3+ letters)
- Analyzes text density (chars per line)
- Detects scanning artifacts

**Automatic path detection:**
- Finds Tesseract in standard Windows locations
- Finds Poppler in standard locations
- Sets paths at module load time
- Logs warnings if not found

**Detailed logging:**
- Every extraction step is logged
- Shows which method was used (standard/OCR)
- Displays character counts
- Shows OCR conversion progress
- Provides helpful error messages

**Better error handling:**
- Specific error messages for missing Tesseract
- Specific error messages for missing Poppler
- Links to download pages
- Falls back gracefully when OCR unavailable

## Usage

Just upload a PDF as before. The logs will show:

```
📄 Starting text extraction: scanned_document.pdf
OCR mode: enabled, OCR available: True
📖 Processing 3 page(s)...
Page 1: Standard extraction got 15 chars
Page 1: Text sparse/empty (got 15 chars), applying OCR...
🔍 Converting PDF page 1 to image at 300 DPI...
✅ PDF converted to image, now applying Tesseract OCR...
✅ OCR complete: extracted 1247 characters from page 1
Page 1: OCR successful, extracted 1247 chars
...
✅ Extraction complete: 3891 total characters
   📊 Methods: 0 standard, 3 OCR, 0 OCR-failed, 0 failed
   🔍 Used OCR on 3/3 page(s)
```

## Log File Location

All logs are written to:
- Console: INFO level (real-time)
- File: `backend/logs/app.log` (DEBUG level, rotating 10MB files)

## Troubleshooting

### "OCR libraries not available"
→ Run: `pip install pytesseract pdf2image Pillow`

### "Tesseract not found"
→ Install from: https://github.com/UB-Mannheim/tesseract/wiki
→ Install to: `C:\Program Files\Tesseract-OCR`

### "Poppler not found"
→ Download: https://github.com/oschwartz10612/poppler-windows/releases/
→ Extract to: `C:\poppler`
→ Verify: `C:\poppler\Library\bin\pdftoppm.exe` exists

### OCR is slow
→ Normal - OCR processes at ~2-3 seconds per page at 300 DPI
→ For faster processing, reduce DPI (lower quality):
  - Edit `pdf_processing_service.py`
  - Change `dpi=300` to `dpi=200` or `dpi=150`

### Still no text extracted
→ Check logs in `backend/logs/app.log`
→ Run `python check_ocr_setup.py`
→ Verify PDF is not encrypted/password-protected

## Files Modified

1. **`backend/app/rag/offline/text_extractor.py`**
   - Added automatic Tesseract path detection
   - Added automatic Poppler path detection
   - Enhanced sparse text detection algorithm
   - Improved logging throughout extraction pipeline
   - Better error messages with installation links

2. **`backend/check_ocr_setup.py`** (NEW)
   - Automated setup verification script
   - Checks all dependencies
   - Tests OCR functionality

3. **`backend/OCR_SETUP.md`** (NEW - this file)
   - Complete installation guide
   - Troubleshooting tips

## Next Steps

1. **Install dependencies:**
   ```bash
   pip install pytesseract pdf2image Pillow
   ```

2. **Install Tesseract** (Windows executable)
   - https://github.com/UB-Mannheim/tesseract/wiki

3. **Install Poppler** (extract to C:\poppler)
   - https://github.com/oschwartz10612/poppler-windows/releases/

4. **Verify setup:**
   ```bash
   python check_ocr_setup.py
   ```

5. **Test with your PDF:**
   - Start backend: `uvicorn app.main:app --reload`
   - Upload an image-based PDF
   - Check logs for OCR activity

---

**Need more help?** Check the logs in `backend/logs/app.log` for detailed debugging info.
