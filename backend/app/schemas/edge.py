from pydantic import BaseModel
from datetime import datetime


class EdgeCreate(BaseModel):
    from_node_id: int
    to_node_id: int


class EdgeResponse(BaseModel):
    id: int
    workflow_id: int
    from_node_id: int
    to_node_id: int
    created_at: datetime

    class Config:
        from_attributes = True
