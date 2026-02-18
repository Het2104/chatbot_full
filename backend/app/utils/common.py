"""
Common Utilities Module

Provides reusable utility functions for file operations, validation,
and common tasks across the application.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing special characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file system
    """
    safe_filename = "".join(
        c for c in filename 
        if c.isalnum() or c in (' ', '.', '_', '-')
    )
    return safe_filename.strip()


def add_timestamp_to_filename(filename: str) -> str:
    """
    Add timestamp to filename before extension.
    
    Args:
        filename: Original filename
        
    Returns:
        Filename with timestamp (e.g., "file_20260210_143022.pdf")
    """
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name}_{timestamp}{ext}"


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB, rounded to 2 decimal places
    """
    size_bytes = os.path.getsize(file_path)
    return round(size_bytes / (1024 * 1024), 2)


def ensure_file_deleted(file_path: str) -> bool:
    """
    Safely delete a file if it exists.
    
    Args:
        file_path: Path to file to delete
        
    Returns:
        True if file was deleted or didn't exist, False if deletion failed
    """
    if not os.path.exists(file_path):
        return True
    
    try:
        os.remove(file_path)
        return True
    except Exception:
        return False


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Check if file has an allowed extension.
    
    Args:
        filename: Name of file to check
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.txt'])
        
    Returns:
        True if extension is allowed, False otherwise
    """
    filename_lower = filename.lower()
    return any(filename_lower.endswith(ext) for ext in allowed_extensions)


def format_bytes(size_bytes: int) -> str:
    """
    Format byte size into human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB", "350 KB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def count_readable_words(text: str, min_word_length: int = 3) -> int:
    """
    Count readable words in text.
    
    Args:
        text: Text to analyze
        min_word_length: Minimum word length to be considered readable
        
    Returns:
        Number of readable words
    """
    words = text.split()
    readable_words = [
        w for w in words 
        if len(w) >= min_word_length and w.isalpha()
    ]
    return len(readable_words)
