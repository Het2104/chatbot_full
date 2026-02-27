"""
Chatbot Pydantic schemas.

Defines request/response shapes for chatbot CRUD endpoints.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatbotCreate(BaseModel):
    """Request body for creating a new chatbot."""

    name: str                          # Display name shown in the UI
    description: Optional[str] = None  # Optional description of the chatbot's purpose


class ChatbotResponse(BaseModel):
    """Response body returned after chatbot read/create operations."""

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
