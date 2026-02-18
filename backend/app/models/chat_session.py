from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)  # Nullable - no single active workflow
    started_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chatbot = relationship("Chatbot", back_populates="chat_sessions")
    workflow = relationship("Workflow", back_populates="chat_sessions")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
