"""
MinIO Storage Service

Handles PDF file storage and retrieval from MinIO object storage.
This replaces local filesystem storage while keeping all processing logic unchanged.
"""

import io
from typing import Optional
from minio import Minio
from minio.error import S3Error

from app.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_NAME,
    MINIO_SECURE,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


class MinIOStorage:
    """Service for storing and retrieving PDF files in MinIO"""
    
    def __init__(self):
        """Initialize MinIO client and ensure bucket exists"""
        try:
            self.client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            self.bucket_name = MINIO_BUCKET_NAME
            
            # Create bucket if it doesn't exist
            self._ensure_bucket_exists()
            
            logger.info(f"MinIO client initialized: {MINIO_ENDPOINT}/{MINIO_BUCKET_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't already exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.debug(f"MinIO bucket already exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def upload_pdf(self, file_data: bytes, filename: str) -> bool:
        """
        Upload PDF file to MinIO.
        
        Args:
            file_data: PDF file contents as bytes
            filename: Name to store the file as (should be sanitized)
            
        Returns:
            True if upload succeeded, False otherwise
        """
        try:
            # Convert bytes to file-like object
            file_stream = io.BytesIO(file_data)
            file_size = len(file_data)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=filename,
                data=file_stream,
                length=file_size,
                content_type="application/pdf"
            )
            
            logger.info(f"Uploaded PDF to MinIO: {filename} ({file_size} bytes)")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload PDF to MinIO: {filename}, error: {e}")
            return False
    
    def download_pdf(self, filename: str) -> Optional[bytes]:
        """
        Download PDF file from MinIO.
        
        Args:
            filename: Name of the file to download
            
        Returns:
            PDF file contents as bytes, or None if download failed
        """
        try:
            # Download from MinIO
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=filename
            )
            
            # Read all data
            file_data = response.read()
            response.close()
            response.release_conn()
            
            logger.debug(f"Downloaded PDF from MinIO: {filename} ({len(file_data)} bytes)")
            return file_data
            
        except S3Error as e:
            logger.error(f"Failed to download PDF from MinIO: {filename}, error: {e}")
            return None
    
    def delete_pdf(self, filename: str) -> bool:
        """
        Delete PDF file from MinIO.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=filename
            )
            
            logger.info(f"Deleted PDF from MinIO: {filename}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete PDF from MinIO: {filename}, error: {e}")
            return False
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in MinIO.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=filename
            )
            return True
        except S3Error:
            return False
    
    def list_pdfs(self):
        """
        List all PDF files in the bucket.
        
        Returns:
            List of object information dictionaries
        """
        try:
            objects = self.client.list_objects(self.bucket_name)
            return [
                {
                    "filename": obj.object_name,
                    "size_bytes": obj.size,
                    "size_mb": obj.size / (1024 * 1024),
                    "uploaded_at": obj.last_modified.timestamp() if obj.last_modified else None
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list PDFs from MinIO: {e}")
            return []


# Singleton instance
_minio_storage = None


def get_minio_storage() -> MinIOStorage:
    """Get or create MinIO storage singleton instance"""
    global _minio_storage
    if _minio_storage is None:
        _minio_storage = MinIOStorage()
    return _minio_storage
