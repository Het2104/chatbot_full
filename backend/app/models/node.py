from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    node_type = Column(String, nullable=False)  # "trigger" or "response"
    text = Column(String, nullable=False)        # Trigger label or button name
    bot_message = Column(String, nullable=True)  # Bot response shown to user
    position_x = Column(Integer, nullable=True)  # Visual editor X position (pixels)
    position_y = Column(Integer, nullable=True)  # Visual editor Y position (pixels)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")
    outgoing_edges = relationship(
        "Edge",
        foreign_keys="Edge.from_node_id",
        back_populates="from_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "Edge",
        foreign_keys="Edge.to_node_id",
        back_populates="to_node",
        cascade="all, delete-orphan",
    )
