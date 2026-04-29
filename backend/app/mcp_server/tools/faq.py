"""
MCP Tools — FAQ Management
Tools: get_faqs, lookup_faq, add_faq, delete_faq
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import hashlib
from typing import Any
from database import SessionLocal
from app.models.faq import FAQ
from app.models.chatbot import Chatbot
from app.config import FAQ_CACHE_PREFIX, FAQ_CACHE_TTL
from app.services.redis_cache_service import get_redis_cache_service


def _cache_key(chatbot_id: int, question: str) -> str:
    """Same key format used by FAQService so MCP hits the same cache."""
    normalized = question.lower().strip()
    question_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
    return f"{FAQ_CACHE_PREFIX}:chatbot:{chatbot_id}:{question_hash}"


def register_faq_tools(mcp):

    @mcp.tool()
    def get_faqs(chatbot_id: int, active_only: bool = True) -> list[dict[str, Any]]:
        """
        Get all FAQs for a chatbot.
        Use active_only=true (default) to return only active FAQs.
        Use active_only=false to return all FAQs including inactive ones.
        """
        if chatbot_id <= 0:
            return [{"error": "chatbot_id must be a positive integer"}]

        db = SessionLocal()
        try:
            chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
            if not chatbot:
                return [{"error": f"Chatbot with id={chatbot_id} not found"}]

            query = db.query(FAQ).filter(FAQ.chatbot_id == chatbot_id)
            if active_only:
                query = query.filter(FAQ.is_active == True)
            faqs = query.order_by(FAQ.display_order, FAQ.id).all()

            return [
                {
                    "id": f.id,
                    "question": f.question,
                    "answer": f.answer,
                    "is_active": f.is_active,
                    "display_order": f.display_order,
                    "parent_id": f.parent_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in faqs
            ]
        finally:
            db.close()

    @mcp.tool()
    def lookup_faq(chatbot_id: int, question: str) -> dict[str, Any]:
        """
        Look up an answer to a specific question from the FAQ database.
        Checks Redis cache first, then falls back to a direct database search.
        Returns the matching question and answer, or a not_found message.
        """
        if chatbot_id <= 0:
            return {"error": "chatbot_id must be a positive integer"}
        if not question or not question.strip():
            return {"error": "question cannot be empty"}

        # 1. Try Redis cache first (same key format as FAQService)
        cache = get_redis_cache_service()
        if cache.is_available():
            cached = cache.get(_cache_key(chatbot_id, question))
            if cached:
                return {"source": "cache", "question": cached.get("question"), "answer": cached.get("answer")}

        # 2. Fallback: direct DB lookup (case-insensitive contains)
        db = SessionLocal()
        try:
            faq = (
                db.query(FAQ)
                .filter(
                    FAQ.chatbot_id == chatbot_id,
                    FAQ.is_active == True,
                    FAQ.question.ilike(f"%{question.strip()}%"),
                )
                .first()
            )
            if faq:
                return {"source": "database", "question": faq.question, "answer": faq.answer}
            return {"source": "none", "message": f"No FAQ found matching '{question}' for chatbot {chatbot_id}"}
        finally:
            db.close()

    @mcp.tool()
    def add_faq(chatbot_id: int, question: str, answer: str) -> dict[str, Any]:
        """
        Add a new FAQ entry to a chatbot's knowledge base.
        Automatically invalidates the Redis cache for this chatbot's FAQs.
        Returns the created FAQ with its new ID.
        """
        if chatbot_id <= 0:
            return {"error": "chatbot_id must be a positive integer"}
        if not question or not question.strip():
            return {"error": "question cannot be empty"}
        if not answer or not answer.strip():
            return {"error": "answer cannot be empty"}

        db = SessionLocal()
        try:
            # Check chatbot exists
            chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
            if not chatbot:
                return {"error": f"Chatbot with id={chatbot_id} not found"}

            # Check for duplicate question
            existing = db.query(FAQ).filter(
                FAQ.chatbot_id == chatbot_id,
                FAQ.question == question.strip(),
            ).first()
            if existing:
                return {"error": f"FAQ with this question already exists (id={existing.id})"}

            new_faq = FAQ(
                chatbot_id=chatbot_id,
                question=question.strip(),
                answer=answer.strip(),
                is_active=True,
            )
            db.add(new_faq)
            db.commit()
            db.refresh(new_faq)

            # Invalidate Redis cache for this chatbot's FAQs
            cache = get_redis_cache_service()
            if cache.is_available():
                deleted = cache.delete_pattern(f"{FAQ_CACHE_PREFIX}:chatbot:{chatbot_id}:*")

            return {
                "success": True,
                "id": new_faq.id,
                "chatbot_id": chatbot_id,
                "question": new_faq.question,
                "answer": new_faq.answer,
                "created_at": new_faq.created_at.isoformat() if new_faq.created_at else None,
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    @mcp.tool()
    def delete_faq(faq_id: int) -> dict[str, Any]:
        """
        Delete an FAQ entry by its ID.
        Automatically invalidates the Redis cache for the affected chatbot.
        """
        if faq_id <= 0:
            return {"error": "faq_id must be a positive integer"}

        db = SessionLocal()
        try:
            faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
            if not faq:
                return {"error": f"FAQ with id={faq_id} not found"}

            chatbot_id = faq.chatbot_id
            question = faq.question
            db.delete(faq)
            db.commit()

            # Invalidate Redis cache
            cache = get_redis_cache_service()
            if cache.is_available():
                cache.delete_pattern(f"{FAQ_CACHE_PREFIX}:chatbot:{chatbot_id}:*")

            return {
                "success": True,
                "deleted_id": faq_id,
                "question": question,
                "chatbot_id": chatbot_id,
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()
