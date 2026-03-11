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


class WidgetUpdate(BaseModel):
    """Request body for updating widget embed settings."""

    widget_color: Optional[str] = None
    widget_welcome_message: Optional[str] = None
    widget_position: Optional[str] = None  # "bottom-right" | "bottom-left"


class ChatbotResponse(BaseModel):
    """Response body returned after chatbot read/create operations."""

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    embed_key: Optional[str] = None
    widget_color: str = "#2563EB"
    widget_welcome_message: str = "Hi! How can I help you?"
    widget_position: str = "bottom-right"

    class Config:
        from_attributes = True
