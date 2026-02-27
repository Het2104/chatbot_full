"""
Chat Pydantic schemas.

Defines request/response shapes for the chat REST endpoints:
  POST /chat/start   - begin a new session
  POST /chat/message - send a synchronous message
  POST /chat/message/queue - send a message that may be routed to the RAG worker
"""

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List


class TriggerNodeOption(BaseModel):
    """A workflow trigger node returned when a chat session starts."""

    id: int           # Node ID (used to identify the selected trigger)
    text: str         # Button label shown to the user
    workflow_id: int  # Workflow this trigger belongs to


class NodeOption(BaseModel):
    """A generic next-step option shown after a bot response."""

    id: Optional[int] = None  # Node ID; None for FAQ-derived options
    text: str                 # Option label shown to the user


class ChatStartRequest(BaseModel):
    """Request body to start a new chat session."""

    chatbot_id: int  # ID of the chatbot to converse with


class ChatStartResponse(BaseModel):
    """Response returned after a chat session is created."""

    session_id: int                       # Unique session identifier for subsequent messages
    chatbot_id: int
    trigger_nodes: List[TriggerNodeOption] # Initial clickable options to start a workflow
    started_at: datetime


class ChatMessageRequest(BaseModel):
    """Request body for sending a synchronous message."""

    session_id: int
    message: str

    @field_validator('message')
    @classmethod
    def trim_message(cls, v: str) -> str:
        """Strip leading/trailing whitespace from the user's message."""
        return v.strip()


class ChatMessageResponse(BaseModel):
    """Response returned after synchronous message processing."""

    session_id: int
    user_message: str
    bot_response: str
    options: List[NodeOption] = []  # Next-step options; empty for RAG / default responses
    timestamp: datetime


class ChatQueueRequest(BaseModel):
    """Request body for the async queue endpoint (workflow/FAQ checked first, then RAG)."""

    session_id: int
    message: str

    @field_validator('message')
    @classmethod
    def trim_message(cls, v: str) -> str:
        """Strip leading/trailing whitespace from the user's message."""
        return v.strip()


class ChatQueueResponse(BaseModel):
    """
    Response from the async queue endpoint.

    Two possible cases:
      cache_hit=True  → bot_response is populated, no WebSocket needed.
      cache_hit=False → job enqueued; frontend opens WS /ws/chat/{session_id}.
    """
    job_id: str
    session_id: int
    queued: bool                        # True  = job sent to RabbitMQ
    cache_hit: bool                     # True  = answered from Redis cache
    bot_response: Optional[str] = None  # Populated only on cache_hit
    options: List[NodeOption] = []      # Populated only on cache_hit
