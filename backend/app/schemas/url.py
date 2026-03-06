from datetime import datetime
from typing import Optional
from pydantic import BaseModel, AnyHttpUrl


class URLIngestRequest(BaseModel):
    url: AnyHttpUrl


class URLResponse(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    num_chunks: int
    indexed_at: datetime

    model_config = {"from_attributes": True}


class URLIngestResponse(BaseModel):
    success: bool
    message: str
    url: str
    title: Optional[str] = None
    stats: Optional[dict] = None
    error: Optional[str] = None
