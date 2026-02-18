"""
Application Configuration Module

Centralizes all configuration constants, magic numbers, and environment variables.
This improves maintainability and makes it easier to change settings.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
_env_path = Path(__file__).parent.parent / '.env'
load_dotenv(_env_path)


# ============================================================================
# Database Configuration
# ============================================================================

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")


# ============================================================================
# CORS Configuration
# ============================================================================

CORS_ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


# ============================================================================
# File Upload Configuration
# ============================================================================

# Maximum file size for uploads (10MB)
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
MAX_FILE_SIZE_MB: int = 10

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS: List[str] = ['.pdf']

# Storage directories
DATA_DIR = Path("data")
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = Path("logs")


# ============================================================================
# OCR Configuration
# ============================================================================

# DPI for OCR image conversion (higher = better quality but slower)
OCR_DEFAULT_DPI: int = 300

# Text extraction thresholds
TEXT_SPARSE_MIN_CHARS: int = 100
TEXT_SPARSE_MIN_READABLE_WORDS: int = 5
TEXT_SPARSE_MIN_WORD_LENGTH: int = 3
TEXT_SPARSE_MIN_CHARS_PER_LINE: int = 10

# Tesseract paths to check (Windows)
TESSERACT_PATHS: List[str] = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Tesseract-OCR\tesseract.exe',
]

# Poppler paths to check (Windows)
POPPLER_PATHS: List[str] = [
    r'C:\Program Files\poppler\Library\bin',
    r'C:\Program Files (x86)\poppler\Library\bin',
    r'C:\poppler\Library\bin',
    r'C:\poppler-24.02.0\Library\bin',
    r'C:\Program Files\poppler-24.02.0\Library\bin',
]


# ============================================================================
# RAG Configuration
# ============================================================================

# Embedding model
EMBEDDING_MODEL: str = "all-MiniLM-L12-v2"
EMBEDDING_DIMENSION: int = 384

# Retrieval parameters
RAG_DEFAULT_TOP_K: int = 4
RAG_DEFAULT_MIN_SCORE: float = 0.3
RAG_DEFAULT_TEMPERATURE: float = 0.0

# Similarity score thresholds
SIMILARITY_BALANCED: float = 0.3
SIMILARITY_CONSERVATIVE: float = 0.4
SIMILARITY_AGGRESSIVE: float = 0.2

# Chunking parameters (Sentence-Based Strategy)
CHUNK_SIZE: int = 2000              # Maximum CHARACTERS per chunk
CHUNK_OVERLAP_SENTENCES: int = 3   # Number of SENTENCES to overlap between chunks


# ============================================================================
# Milvus Configuration
# ============================================================================

MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION_NAME: str = "rag_chunks"


# ============================================================================
# MinIO Configuration (PDF Storage)
# ============================================================================

MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "pdfs")
MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"


# ============================================================================
# LLM Configuration
# ============================================================================

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3-8b-8192")
LLM_MAX_TOKENS: int = 1024


# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = str(LOGS_DIR / "app.log")
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT: int = 5


# ============================================================================
# Chat Configuration
# ============================================================================

# Default response when no match is found
DEFAULT_BOT_RESPONSE: str = "I didn't understand"


# ============================================================================
# Helper Functions
# ============================================================================

def ensure_directories() -> None:
    """Create all required directories if they don't exist."""
    directories = [
        DATA_DIR,
        RAW_PDFS_DIR,
        PROCESSED_DIR,
        LOGS_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def validate_config() -> bool:
    """
    Validate that all critical configuration is present.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    errors = []
    
    if not DATABASE_URL:
        errors.append("DATABASE_URL is not set")
    
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY is not set (RAG features will be limited)")
    
    if errors:
        for error in errors:
            print(f"⚠️  Configuration error: {error}")
        return False
    
    return True


# Initialize directories on import
ensure_directories()
