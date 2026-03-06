"""
Node Pydantic schemas.

Defines request/response shapes for node CRUD endpoints.
Nodes are the building blocks of a workflow:
  - "trigger": User-selectable entry points (e.g. "Check my order")
  - "response": Bot replies shown after user input
"""

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Literal, Optional


class NodeCreate(BaseModel):
    """Request body for creating a new node inside a workflow."""

    node_type: Literal["trigger", "response"]  # Type determines role in conversation flow
    text: str                                  # Trigger label or button name
    bot_message: Optional[str] = None          # Bot response displayed to the user
    position_x: Optional[int] = None           # Horizontal position in the visual editor
    position_y: Optional[int] = None           # Vertical position in the visual editor

    @field_validator("text")
    @classmethod
    def trim_text(cls, v: str) -> str:
        """Strip leading/trailing whitespace from node text."""
        return v.strip()


class NodeResponse(BaseModel):
    """Response body returned after node read/create/update operations."""

    id: int
    workflow_id: int
    node_type: Literal["trigger", "response"]
    text: str
    bot_message: Optional[str] = None  # Bot response displayed to the user
    position_x: Optional[int] = None  # X position in visual editor (does not affect logic)
    position_y: Optional[int] = None  # Y position in visual editor (does not affect logic)
    created_at: datetime

    class Config:
        from_attributes = True


class NodeUpdate(BaseModel):
    """Request body for partial node updates (text, bot_message, and/or visual position)."""

    text: Optional[str] = None             # New trigger label / button name (None = no change)
    bot_message: Optional[str] = None      # New bot response text (None = no change)
    position_x: Optional[int] = None       # New horizontal position (None = no change)
    position_y: Optional[int] = None       # New vertical position (None = no change)

    @field_validator("text")
    @classmethod
    def trim_text(cls, v: Optional[str]) -> Optional[str]:
        """Strip leading/trailing whitespace if text is provided."""
        return v.strip() if v else None
