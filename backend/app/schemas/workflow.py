from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WorkflowCreate(BaseModel):
    name: str


class WorkflowResponse(BaseModel):
    id: int
    chatbot_id: int
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
