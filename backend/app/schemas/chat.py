from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any


class TriggerNodeOption(BaseModel):
    """Represents a trigger node option"""
    id: int
    text: str
    workflow_id: int


class NodeOption(BaseModel):
    """Represents a node option (could be trigger or response)"""
    id: Optional[int] = None
    text: str


class ChatStartRequest(BaseModel):
    chatbot_id: int


class ChatStartResponse(BaseModel):
    session_id: int
    chatbot_id: int
    trigger_nodes: List[TriggerNodeOption]
    started_at: datetime


class ChatMessageRequest(BaseModel):
    session_id: int
    message: str
    
    @field_validator('message')
    @classmethod
    def trim_message(cls, v: str) -> str:
        return v.strip()


class ChatMessageResponse(BaseModel):
    session_id: int
    user_message: str
    bot_response: str
    options: List[NodeOption] = []
    timestamp: datetime
