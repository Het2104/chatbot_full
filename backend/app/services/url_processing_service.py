"""
URL Processing Service
Orchestrates the full pipeline: scrape URL → clean text → chunk → embed → store in Milvus.
Mirrors PDFProcessingService so the same RAG infrastructure handles both source types.
"""
import time
from typing import Dict, Any

from app.rag.offline.text_cleaner import clean_text
from app.rag.offline.chunker import chunk_document
from app.services.url_scraping_service import URLScrapingService
from app.logging_config import get_logger

logger = get_logger(__name__)


class URLProcessingService:
    """Processes a public URL and indexes its content into the vector store."""

    def __init__(self):
        self._scraper = URLScrapingService()
        self._embedder = None
        self._vector_store = None

    def _ensure_initialized(self):
        """Lazy-load heavy ML dependencies only on first use."""
        if self._embedder is None:
            logger.debug("Initializing embedder...")
            from app.rag.offline.embedder import Embedder
            self._embedder = Embedder()
        if self._vector_store is None:
            logger.debug("Initializing vector store...")
            from app.rag.storage.milvus_store import MilvusVectorStore
            self._vector_store = MilvusVectorStore(collection_name="rag_chunks")

    def delete_url_chunks(self, url: str) -> None:
        """
        Remove all Milvus chunks whose source_file matches this URL.
        Called before re-ingesting a URL to avoid duplicate vectors.
        """
        self._ensure_initialized()
        logger.info(f"Deleting existing chunks for URL: {url}")
        self._vector_store.delete_by_source_file(url)

    def process_url(self, url: str) -> Dict[str, Any]:
        """
        Full ingestion pipeline for a single URL.

        Steps:
          1. Scrape → plain text
          2. Clean text
          3. Chunk document
          4. Embed chunks
          5. Store in Milvus (source_file = URL string)

        Args:
            url: Fully-qualified http/https URL.

        Returns:
            {
                "success":  bool,
                "url":      str,
                "title":    str,
                "stats": {
                    "text_length":           int,
                    "cleaned_length":        int,
                    "num_chunks":            int,
                    "processing_time_seconds": float,
                },
            }

            On failure returns the same dict with "success": False and "error": str.
        """
        start_time = time.time()
        logger.info(f"Starting URL processing: {url}")

        try:
            self._ensure_initialized()

            # Step 1: Scrape
            logger.info("Step 1: Scraping URL...")
            scraped = self._scraper.scrape(url)
            text = scraped["text"]
            title = scraped["title"]
            text_length = len(text)

            # Step 2: Clean
            logger.info("Step 2: Cleaning text...")
            cleaned = clean_text(text)
            cleaned_length = len(cleaned)

            if not cleaned or cleaned_length < 10:
                raise ValueError(
                    f"Text too short after cleaning ({cleaned_length} chars). "
                    "The page may contain only boilerplate or special characters."
                )

            # Step 3: Chunk
            logger.info("Step 3: Creating chunks...")
            chunks = chunk_document(cleaned, url)
            num_chunks = len(chunks)

            if num_chunks == 0:
                raise ValueError("No chunks produced from page content.")

            logger.info(f"Created {num_chunks} chunks")

            # Step 4: Embed
            logger.info("Step 4: Generating embeddings...")
            embeddings = self._embedder.embed_chunks(chunks, show_progress=False)

            # Step 5: Store
            logger.info("Step 5: Storing in Milvus...")
            self._vector_store.add_chunks(chunks, embeddings)

            processing_time = round(time.time() - start_time, 2)
            logger.info(
                f"URL processing complete: {url} — "
                f"{num_chunks} chunks in {processing_time}s"
            )

            return {
                "success": True,
                "url": url,
                "title": title,
                "stats": {
                    "text_length": text_length,
                    "cleaned_length": cleaned_length,
                    "num_chunks": num_chunks,
                    "processing_time_seconds": processing_time,
                },
            }

        except Exception as exc:
            processing_time = round(time.time() - start_time, 2)
            logger.error(f"URL processing failed for {url}: {exc}", exc_info=True)
            return {
                "success": False,
                "url": url,
                "title": "",
                "stats": {},
                "error": str(exc),
                "processing_time_seconds": processing_time,
            }
