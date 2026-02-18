from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FAQCreate(BaseModel):
    question: str
    answer: str
    parent_id: Optional[int] = None
    is_active: bool = True
    display_order: int = 0


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class FAQResponse(BaseModel):
    id: int
    chatbot_id: int
    question: str
    answer: str
    parent_id: Optional[int] = None
    is_active: bool
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class FAQWithChildren(BaseModel):
    """FAQ with optional child FAQs"""
    id: int
    chatbot_id: int
    question: str
    answer: str
    parent_id: Optional[int] = None
    is_active: bool
    display_order: int
    created_at: datetime
    children: List['FAQResponse'] = []

    class Config:
        from_attributes = True
