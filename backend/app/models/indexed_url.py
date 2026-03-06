from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .base import Base


class IndexedURL(Base):
    __tablename__ = "indexed_urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=True)
    num_chunks = Column(Integer, nullable=False, default=0)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
