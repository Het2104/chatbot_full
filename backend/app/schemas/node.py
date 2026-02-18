from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Literal, Optional


class NodeCreate(BaseModel):
    node_type: Literal["trigger", "response"]
    text: str
    position_x: Optional[int] = None  # Optional X position for visual editor
    position_y: Optional[int] = None  # Optional Y position for visual editor

    @field_validator("text")
    @classmethod
    def trim_text(cls, v: str) -> str:
        return v.strip()


class NodeResponse(BaseModel):
    id: int
    workflow_id: int
    node_type: Literal["trigger", "response"]
    text: str
    position_x: Optional[int] = None  # X position in visual editor
    position_y: Optional[int] = None  # Y position in visual editor
    created_at: datetime

    class Config:
        from_attributes = True


class NodeUpdate(BaseModel):
    """Schema for updating node positions or text"""
    text: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None

    @field_validator("text")
    @classmethod
    def trim_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else None
