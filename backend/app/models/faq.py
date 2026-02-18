from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from .base import Base


class FAQ(Base):
    __tablename__ = "faqs"
    __table_args__ = (
        UniqueConstraint('chatbot_id', 'question', name='unique_chatbot_question'),
    )

    id = Column(Integer, primary_key=True, index=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    parent_id = Column(Integer, ForeignKey("faqs.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chatbot = relationship("Chatbot", back_populates="faqs")
    parent = relationship("FAQ", remote_side=[id], backref="children", foreign_keys=[parent_id])
