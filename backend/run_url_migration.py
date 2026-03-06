"""
Migration: create indexed_urls table

Run with:
    cd backend
    python run_url_migration.py
"""
import sys
import os

# Add backend directory to path so imports work when run directly
sys.path.insert(0, os.path.dirname(__file__))

from database import engine
from app.models import Base
from app.models.indexed_url import IndexedURL  # noqa: F401 — ensures table is registered

if __name__ == "__main__":
    print("Creating indexed_urls table...")
    Base.metadata.create_all(bind=engine, tables=[IndexedURL.__table__])
    print("Done. Table 'indexed_urls' is ready.")
