"""
MCP Tools — Chatbot Management
Tools: list_chatbots, ask_chatbot
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from typing import Any
from database import SessionLocal
from app.models.chatbot import Chatbot


def register_chatbot_tools(mcp):

    @mcp.tool()
    def list_chatbots() -> list[dict[str, Any]]:
        """
        List all chatbots available on the platform.
        Returns id, name, description, welcome message and creation date for each chatbot.
        """
        db = SessionLocal()
        try:
            chatbots = db.query(Chatbot).order_by(Chatbot.id).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description or "",
                    "welcome_message": c.widget_welcome_message,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in chatbots
            ]
        finally:
            db.close()

    @mcp.tool()
    def get_chatbot(chatbot_id: int) -> dict[str, Any]:
        """
        Get full details of a specific chatbot by its ID.
        Returns id, name, description, widget settings and creation date.
        """
        if chatbot_id <= 0:
            return {"error": "chatbot_id must be a positive integer"}

        db = SessionLocal()
        try:
            chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
            if not chatbot:
                return {"error": f"Chatbot with id={chatbot_id} not found"}
            return {
                "id": chatbot.id,
                "name": chatbot.name,
                "description": chatbot.description or "",
                "welcome_message": chatbot.widget_welcome_message,
                "widget_color": chatbot.widget_color,
                "widget_position": chatbot.widget_position,
                "embed_key": chatbot.embed_key,
                "created_at": chatbot.created_at.isoformat() if chatbot.created_at else None,
            }
        finally:
            db.close()
