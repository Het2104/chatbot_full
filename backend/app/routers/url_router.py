"""
URL Ingestion Router
Handles indexing public web pages into the RAG vector store.

Endpoints:
  POST   /api/upload/url          — Ingest (or re-ingest) a URL
  GET    /api/upload/urls         — List all indexed URLs
  DELETE /api/upload/url/{url_id} — Remove a URL and its vectors
"""
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.url import URLIngestRequest, URLIngestResponse, URLResponse
from app.services.url_processing_service import URLProcessingService
from app.models.indexed_url import IndexedURL
from app.logging_config import get_logger
from app.dependencies.auth import get_current_admin_user
from app.models.user import User
from database import get_db

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/upload",
    tags=["URL Ingestion"],
)


@router.post("/url", response_model=URLIngestResponse)
def ingest_url(request: URLIngestRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    Fetch a public web page, extract text, and index it into the vector store.

    - If the URL was previously indexed, old vectors are deleted first (re-ingest).
    - The URL string is used as the Milvus `source_file` identifier.
    """
    url = str(request.url)
    logger.info(f"Received URL ingest request: {url}")

    processor = URLProcessingService()

    # Check if URL already exists — delete old vectors first to avoid duplicates
    existing = db.query(IndexedURL).filter(IndexedURL.url == url).first()
    if existing:
        logger.info(f"URL already indexed (id={existing.id}), re-ingesting...")
        try:
            processor.delete_url_chunks(url)
        except Exception as exc:
            logger.warning(f"Could not delete old chunks for {url}: {exc}")

    # Run the full processing pipeline
    result = processor.process_url(url)

    if not result["success"]:
        logger.error(f"URL processing failed: {result.get('error')}")
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Failed to process URL"),
        )

    num_chunks = result["stats"].get("num_chunks", 0)
    title = result.get("title", "")

    # Upsert indexed_urls record
    if existing:
        existing.title = title
        existing.num_chunks = num_chunks
    else:
        db.add(IndexedURL(url=url, title=title, num_chunks=num_chunks))

    db.commit()

    return URLIngestResponse(
        success=True,
        message=f"URL indexed successfully ({num_chunks} chunks created).",
        url=url,
        title=title,
        stats=result["stats"],
    )


@router.get("/urls", response_model=List[URLResponse])
def list_indexed_urls(db: Session = Depends(get_db)):
    """Return all URLs that have been indexed into the vector store."""
    return db.query(IndexedURL).order_by(IndexedURL.indexed_at.desc()).all()


@router.delete("/url/{url_id}")
def delete_indexed_url(url_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    Delete a URL's vectors from Milvus and remove its record from the database.
    """
    record = db.query(IndexedURL).filter(IndexedURL.id == url_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="URL not found.")

    url = record.url
    logger.info(f"Deleting URL id={url_id}: {url}")

    # Remove vectors from Milvus
    try:
        processor = URLProcessingService()
        processor.delete_url_chunks(url)
    except Exception as exc:
        logger.warning(f"Could not delete Milvus chunks for {url}: {exc}")

    # Remove DB record
    db.delete(record)
    db.commit()

    logger.info(f"URL deleted successfully: {url}")
    return {"success": True, "message": f"URL '{url}' removed from the knowledge base."}
