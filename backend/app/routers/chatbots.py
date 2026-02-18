"""
Chatbots Router Module

Provides CRUD endpoints for managing chatbot instances.
Each chatbot can have multiple workflows, FAQs, and chat sessions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.chatbot import Chatbot
from app.schemas.chatbot import ChatbotCreate, ChatbotResponse
from app.utils import entity_not_found_error

router = APIRouter()


@router.post("", response_model=ChatbotResponse, status_code=201)
def create_chatbot(chatbot: ChatbotCreate, db: Session = Depends(get_db)):
    """
    Create a new chatbot instance.
    
    A chatbot is the top-level container that holds:
    - Workflows (conversation flows)
    - FAQs (question-answer pairs)
    - Chat sessions (user conversations)
    
    Request body:
        name: Display name for the chatbot
        description: Optional description of the chatbot's purpose
    
    Returns:
        The created chatbot with assigned ID and timestamp
    """
    new_chatbot = Chatbot(
        name=chatbot.name,
        description=chatbot.description
    )
    db.add(new_chatbot)
    db.commit()
    db.refresh(new_chatbot)  # Get the assigned ID and created_at
    return new_chatbot


@router.get("", response_model=List[ChatbotResponse])
def list_chatbots(db: Session = Depends(get_db)):
    """
    List all chatbots in the system.
    
    Returns:
        List of all chatbot instances with their basic information
    """
    all_chatbots = db.query(Chatbot).all()
    return all_chatbots


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
def get_chatbot(chatbot_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific chatbot by ID.
    
    Path parameters:
        chatbot_id: Unique identifier of the chatbot
    
    Returns:
        The chatbot instance with all details
        
    Raises:
        404: If chatbot with given ID doesn't exist
    """
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    return chatbot


@router.delete("/{chatbot_id}", status_code=204)
def delete_chatbot(chatbot_id: int, db: Session = Depends(get_db)):
    """
    Delete a chatbot and all related data.
    
    This is a cascading delete that removes:
    - The chatbot itself
    - All workflows belonging to the chatbot
    - All nodes and edges in those workflows
    - All FAQs for the chatbot
    - All chat sessions and messages
    
    Path parameters:
        chatbot_id: Unique identifier of the chatbot to delete
    
    Returns:
        204 No Content on success
        
    Raises:
        404: If chatbot with given ID doesn't exist
    
    Warning:
        This operation is irreversible. All conversation history will be lost.
    """
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    # SQLAlchemy cascade delete handles all related records
    db.delete(chatbot)
    db.commit()
    return None
