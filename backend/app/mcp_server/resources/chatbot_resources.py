"""
MCP Resources — Chatbot Platform
Resources are passive context the AI can read, like documents.
URI templates:
  chatbot://{chatbot_id}/config         → chatbot settings + widget config
  chatbot://{chatbot_id}/workflow       → active workflow full graph
  chatbot://{chatbot_id}/faqs           → all active FAQs
"""

import sys
import os

_this_file = os.path.abspath(__file__)
_backend_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(_this_file)))
)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import json
from database import SessionLocal
from app.models.chatbot import Chatbot
from app.models.workflow import Workflow
from app.models.node import Node
from app.models.edge import Edge
from app.models.faq import FAQ


def register_chatbot_resources(mcp):

    @mcp.resource("chatbot://{chatbot_id}/config")
    def chatbot_config(chatbot_id: str) -> str:
        """
        Full configuration for a chatbot.
        Includes name, description, widget settings, and embed key.
        Use this before editing a chatbot or when an AI needs chatbot context.
        """
        db = SessionLocal()
        try:
            c = db.query(Chatbot).filter(Chatbot.id == int(chatbot_id)).first()
            if not c:
                return json.dumps({"error": f"Chatbot {chatbot_id} not found"})
            return json.dumps({
                "id": c.id,
                "name": c.name,
                "description": c.description or "",
                "widget_color": c.widget_color,
                "widget_welcome_message": c.widget_welcome_message,
                "widget_position": c.widget_position,
                "embed_key": c.embed_key,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }, indent=2)
        finally:
            db.close()

    @mcp.resource("chatbot://{chatbot_id}/workflow")
    def chatbot_active_workflow(chatbot_id: str) -> str:
        """
        The currently active workflow for a chatbot as a full graph (nodes + edges).
        Shows every trigger node (user intents) and response node (bot replies)
        with their connections. Use this to understand or extend conversation flow.
        """
        db = SessionLocal()
        try:
            w = (
                db.query(Workflow)
                .filter(
                    Workflow.chatbot_id == int(chatbot_id),
                    Workflow.is_active == True,
                )
                .first()
            )
            if not w:
                return json.dumps({
                    "chatbot_id": chatbot_id,
                    "active_workflow": None,
                    "message": "No active workflow for this chatbot.",
                })

            nodes = db.query(Node).filter(Node.workflow_id == w.id).all()
            edges = db.query(Edge).filter(Edge.workflow_id == w.id).all()

            return json.dumps({
                "workflow_id": w.id,
                "workflow_name": w.name,
                "chatbot_id": int(chatbot_id),
                "nodes": [
                    {
                        "id": n.id,
                        "node_type": n.node_type,
                        "text": n.text,
                        "bot_message": n.bot_message,
                        "position_x": n.position_x,
                        "position_y": n.position_y,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "from_node_id": e.from_node_id,
                        "to_node_id": e.to_node_id,
                    }
                    for e in edges
                ],
            }, indent=2)
        finally:
            db.close()

    @mcp.resource("chatbot://{chatbot_id}/faqs")
    def chatbot_faqs(chatbot_id: str) -> str:
        """
        All active FAQs for a chatbot as a structured list.
        Each entry shows the question, answer, and display order.
        Use this as context when the AI needs to understand what the chatbot already knows.
        """
        db = SessionLocal()
        try:
            faqs = (
                db.query(FAQ)
                .filter(
                    FAQ.chatbot_id == int(chatbot_id),
                    FAQ.is_active == True,
                )
                .order_by(FAQ.display_order)
                .all()
            )
            return json.dumps({
                "chatbot_id": int(chatbot_id),
                "faq_count": len(faqs),
                "faqs": [
                    {
                        "id": f.id,
                        "question": f.question,
                        "answer": f.answer,
                        "display_order": f.display_order,
                    }
                    for f in faqs
                ],
            }, indent=2)
        finally:
            db.close()
