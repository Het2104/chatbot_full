from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        # Prevent duplicate edges between same two nodes
        UniqueConstraint("from_node_id", "to_node_id", name="uq_edge_from_to"),
    )

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    from_node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow", back_populates="edges")
    from_node = relationship("Node", foreign_keys=[from_node_id], back_populates="outgoing_edges")
    to_node = relationship("Node", foreign_keys=[to_node_id], back_populates="incoming_edges")
