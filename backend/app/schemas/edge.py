"""
Edge Pydantic schemas.

Defines request/response shapes for edge CRUD endpoints.
Edges are directed connections between nodes that define the conversation flow.
"""

from pydantic import BaseModel
from datetime import datetime


class EdgeCreate(BaseModel):
    """Request body for creating a directed edge between two nodes."""

    from_node_id: int  # Source node (start of the connection)
    to_node_id: int    # Target node (end of the connection)


class EdgeResponse(BaseModel):
    """Response body returned after edge read/create operations."""

    id: int
    workflow_id: int    # Parent workflow that owns both nodes
    from_node_id: int
    to_node_id: int
    created_at: datetime

    class Config:
        from_attributes = True
