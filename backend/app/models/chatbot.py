import uuid
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Chatbot(Base):
    __tablename__ = "chatbots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Widget embed settings
    embed_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    widget_color = Column(String, nullable=False, default="#2563EB")
    widget_welcome_message = Column(String, nullable=False, default="Hi! How can I help you?")
    widget_position = Column(String, nullable=False, default="bottom-right")

    # Relationships
    workflows = relationship("Workflow", back_populates="chatbot", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="chatbot", cascade="all, delete-orphan")
    faqs = relationship("FAQ", back_populates="chatbot", cascade="all, delete-orphan")
