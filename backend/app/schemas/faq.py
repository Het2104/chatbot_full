"""
FAQ Pydantic schemas.

Defines request/response shapes for FAQ CRUD endpoints.

FAQs support a parent-child hierarchy:
  - Parent FAQs (parent_id=None): Shown as top-level options to the user
  - Child FAQs (parent_id=X):     Shown as follow-up questions after a parent is selected
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FAQCreate(BaseModel):
    """Request body for creating a new FAQ."""

    question: str                      # The question text (must be unique per chatbot)
    answer: str                        # The answer text displayed to the user
    parent_id: Optional[int] = None    # Parent FAQ ID; None means this is a top-level FAQ
    is_active: bool = True             # Whether this FAQ is visible to users
    display_order: int = 0             # Sort order; lower numbers appear first


class FAQUpdate(BaseModel):
    """Request body for partially updating an existing FAQ (PATCH)."""

    question: Optional[str] = None      # New question text (None = no change)
    answer: Optional[str] = None        # New answer text (None = no change)
    parent_id: Optional[int] = None     # New parent ID (None = no change)
    is_active: Optional[bool] = None    # New active status (None = no change)
    display_order: Optional[int] = None # New display order (None = no change)


class FAQResponse(BaseModel):
    """Response body returned after FAQ read/create/update operations."""

    id: int
    chatbot_id: int
    question: str
    answer: str
    parent_id: Optional[int] = None  # None if this is a top-level FAQ
    is_active: bool
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class FAQWithChildren(BaseModel):
    """FAQ response with its nested child FAQs included."""

    id: int
    chatbot_id: int
    question: str
    answer: str
    parent_id: Optional[int] = None
    is_active: bool
    display_order: int
    created_at: datetime
    children: List['FAQResponse'] = []  # Child FAQs shown as follow-up options

    class Config:
        from_attributes = True
