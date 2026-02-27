"""
Workflow Pydantic schemas.

Defines request/response shapes for workflow CRUD endpoints.
A workflow is a directed graph (nodes + edges) representing a conversation flow.
"""

from pydantic import BaseModel
from datetime import datetime


class WorkflowCreate(BaseModel):
    """Request body for creating a new workflow inside a chatbot."""

    name: str  # Display name for the workflow (e.g. "Order Support Flow")


class WorkflowResponse(BaseModel):
    """Response body returned after workflow read/create/activate operations."""

    id: int
    chatbot_id: int  # Parent chatbot that owns this workflow
    name: str
    is_active: bool  # True if this is the currently active workflow for the chatbot
    created_at: datetime

    class Config:
        from_attributes = True
