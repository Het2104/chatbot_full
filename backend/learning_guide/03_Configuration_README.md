# 📚 Part 3: Configuration & Settings (app/config.py)

## 🎯 What This File Does

The `app/config.py` file is your **central configuration hub**. It:
1. Loads environment variables from `.env` file
2. Defines all constants and settings in one place
3. Validates that required configuration is present
4. Makes it easy to change settings without modifying code

---

## 📋 Complete Code Walkthrough

### **1. Import and Load Environment Variables**

```python
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
_env_path = Path(__file__).parent.parent / '.env'
load_dotenv(_env_path)
```

**What this does:**
- `Path(__file__).parent.parent`: Goes from `app/config.py` → `app/` → `backend/`
- Looks for `.env` file in the `backend/` directory
- Loads all variables from `.env` into `os.environ`

**Example `.env` file:**
```env
DATABASE_URL=postgresql://user:password@localhost/chatbot_db
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

### **2. Database Configuration**

```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
```

**What this does:**
- Gets `DATABASE_URL` from environment variables
- If not found, raises an error (app won't start)
- This ensures you never accidentally run without a database

**Example DATABASE_URL formats:**
```python
# PostgreSQL
"postgresql://user:password@localhost:5432/chatbot_db"

# SQLite (for testing)
"sqlite:///./chatbot.db"
```

---

### **3. CORS Configuration**

```python
CORS_ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

**What this does:**
- Lists which frontend URLs can access your API
- Both `localhost` and `127.0.0.1` are included (they're slightly different)

**When to modify:**
```python
# If your frontend runs on different port
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]  # Vite default

# For production
CORS_ALLOWED_ORIGINS = ["https://yourdomain.com"]
```

---

### **4. File Upload Configuration**

```python
# Maximum file size for uploads (10MB)
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
MAX_FILE_SIZE_MB: int = 10

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS: List[str] = ['.pdf']

# Storage directories
DATA_DIR = Path("data")
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
```

**Explanation:**
- `MAX_FILE_SIZE_BYTES`: Maximum upload size in bytes (10MB = 10,485,760 bytes)
- `ALLOWED_FILE_EXTENSIONS`: Only PDFs are allowed
- `RAW_PDFS_DIR`: Where uploaded PDFs are stored

**File size calculation:**
```python
1 MB = 1024 KB
1 KB = 1024 bytes
10 MB = 10 * 1024 * 1024 = 10,485,760 bytes
```

**To allow more file types:**
```python
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.docx', '.txt']
```

---

### **5. RAG Configuration**

```python
# RAG System Configuration
RAG_DEFAULT_TOP_K: int = 5
RAG_DEFAULT_MIN_SCORE: float = 0.3
RAG_DEFAULT_TEMPERATURE: float = 0.0

# Milvus Configuration
MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
```

**RAG Parameters Explained:**

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `TOP_K` | 5 | Retrieve top 5 most relevant document chunks |
| `MIN_SCORE` | 0.3 | Only use chunks with similarity ≥ 30% |
| `TEMPERATURE` | 0.0 | LLM temperature (0 = deterministic, 1 = creative) |

**Milvus Configuration:**
- `MILVUS_HOST`: Where Milvus vector database is running
- `MILVUS_PORT`: Port number (19530 is default)
- `os.getenv("KEY", "default")`: Use env variable or fallback to default

---

### **6. Logging Configuration**

```python
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path("logs")
```

**Log levels (from most to least verbose):**
```python
"DEBUG"    # Everything including debug info
"INFO"     # General informational messages (default)
"WARNING"  # Warning messages only
"ERROR"    # Error messages only
"CRITICAL" # Critical errors only
```

**Example usage:**
```python
logger.debug("This appears only if LOG_LEVEL=DEBUG")
logger.info("This appears if LOG_LEVEL=INFO or DEBUG")
logger.warning("This appears unless LOG_LEVEL=ERROR or CRITICAL")
```

---

### **7. LLM Configuration**

```python
# Groq API Configuration
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
```

**What this does:**
- Gets Groq API key from environment (required for RAG responses)
- Sets default model to Llama 3.1 70B
- If `GROQ_API_KEY` is empty, RAG will not work

**Available Groq models:**
```python
"llama-3.1-70b-versatile"  # Default - best balance
"llama-3.1-8b-instant"     # Faster, less accurate
"mixtral-8x7b-32768"       # Good alternative
```

---

### **8. OCR Configuration**

```python
# OCR Configuration (for scanned PDFs)
TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
POPPLER_PATH: str = os.getenv("POPPLER_PATH", "")
```

**What this does:**
- Tesseract: OCR engine for extracting text from images
- Poppler: Converts PDF pages to images
- If paths are empty, system will auto-detect installations

**When to set manually:**
```python
# In .env file
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
POPPLER_PATH=C:/poppler/Library/bin
```

---

### **9. Business Logic Configuration**

```python
# Default chatbot response
DEFAULT_BOT_RESPONSE: str = "I don't understand. Can you rephrase?"

# No relevant docs message
NO_RELEVANT_DOCS_MESSAGE: str = "I don't know based on the provided documents."
```

**What these do:**
- `DEFAULT_BOT_RESPONSE`: Fallback when no workflow/FAQ/RAG match is found
- `NO_RELEVANT_DOCS_MESSAGE`: Response when RAG finds no relevant documents

---

### **10. Configuration Validation**

```python
def validate_config() -> bool:
    """
    Validate that all required configuration is present
    Returns False if critical config is missing
    """
    required_vars = {
        "DATABASE_URL": DATABASE_URL,
        "GROQ_API_KEY": GROQ_API_KEY,
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    return True
```

**What this does:**
- Checks if critical environment variables are set
- Logs an error if any are missing
- Returns `True` if all good, `False` if not

---

## 🎓 Configuration Best Practices

### **1. Never Hardcode Secrets**
```python
# ❌ BAD
GROQ_API_KEY = "gsk_abc123xyz"  # Exposed in code!

# ✅ GOOD
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # From .env file
```

### **2. Always Provide Defaults**
```python
# If LOG_LEVEL not set, use "INFO"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

### **3. Group Related Settings**
```python
# All upload settings together
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = ['.pdf']
RAW_PDFS_DIR = Path("data/raw_pdfs")
```

### **4. Use Type Hints**
```python
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # Clear it's an integer
CORS_ALLOWED_ORIGINS: List[str] = [...]      # Clear it's a list of strings
```

---

## 🔗 What's Next?

Now that you understand configuration:
- **Part 4**: Database Models (structure of your tables)
- **Part 5**: RAG Service (how questions are answered from PDFs)

---

## 💡 Quick Reference

**Environment variables you need in `.env`:**
```env
# Required
DATABASE_URL=postgresql://user:password@localhost/chatbot_db
GROQ_API_KEY=gsk_your_api_key_here

# Optional (with defaults)
LOG_LEVEL=INFO
MILVUS_HOST=localhost
MILVUS_PORT=19530
GROQ_MODEL=llama-3.1-70b-versatile
TESSERACT_PATH=
POPPLER_PATH=
```

**How to change settings:**
1. Edit `.env` file (for secrets and environment-specific values)
2. Edit `config.py` file (for business logic and constants)
3. Restart the backend server

