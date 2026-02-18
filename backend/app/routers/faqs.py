"""
FAQs Router Module

Provides CRUD endpoints for managing Frequently Asked Questions.

FAQs support a parent-child hierarchy:
- Parent FAQs: Top-level questions (displayed as initial options)
- Child FAQs: Follow-up questions (displayed after parent is selected)

This allows creating nested Q&A structures like:
  Pricing → Basic Plan Details → Monthly vs Annual
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.faq import FAQ
from app.models.chatbot import Chatbot
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from app.utils import entity_not_found_error

router = APIRouter()


@router.post("/chatbots/{chatbot_id}/faqs", response_model=FAQResponse, status_code=201)
def create_faq(chatbot_id: int, faq: FAQCreate, db: Session = Depends(get_db)):
    """
    Create a new FAQ for a chatbot.
    
    FAQs can be either:
    1. Parent FAQs (parent_id = None): Top-level questions shown as options
    2. Child FAQs (parent_id = X): Follow-up questions shown after parent is selected
    
    Path parameters:
        chatbot_id: ID of the chatbot to add the FAQ to
    
    Request body:
        question: The question text (must be unique per chatbot)
        answer: The answer text
        parent_id: Optional - ID of parent FAQ for nested questions
        is_active: Whether the FAQ is currently active (default True)
        display_order: Numeric order for sorting (lower numbers first)
    
    Returns:
        The created FAQ with assigned ID
        
    Raises:
        404: If chatbot doesn't exist
        400: If question already exists for this chatbot
        
    Validation Rules:
    - Questions must be unique per chatbot (case-sensitive exact match)
    - Question text is automatically trimmed
    """
    # Verify parent chatbot exists
    parent_chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not parent_chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    # Prevent duplicate questions (business rule)
    # This ensures users don't see confusing identical questions
    trimmed_question = faq.question.strip()
    existing_faq = db.query(FAQ).filter(
        FAQ.chatbot_id == chatbot_id,
        FAQ.question == trimmed_question
    ).first()
    
    if existing_faq:
        raise HTTPException(
            status_code=400, 
            detail="This question already exists for this chatbot"
        )
    
    # Create the FAQ
    new_faq = FAQ(
        chatbot_id=chatbot_id,
        question=trimmed_question,
        answer=faq.answer,
        parent_id=faq.parent_id,
        is_active=faq.is_active,
        display_order=faq.display_order
    )
    db.add(new_faq)
    db.commit()
    db.refresh(new_faq)
    return new_faq


@router.get("/chatbots/{chatbot_id}/faqs", response_model=List[FAQResponse])
def list_faqs(chatbot_id: int, active_only: bool = False, parent_only: bool = False, db: Session = Depends(get_db)):
    """
    List FAQs for a chatbot with optional filtering.
    
    This endpoint supports multiple query strategies:
    - All FAQs: No filters (for admin/management UI)
    - Active only: active_only=true (what users see)
    - Parent-level only: parent_only=true (initial options to display)
    
    Path parameters:
        chatbot_id: ID of the chatbot
    
    Query parameters:
        active_only: If true, only return FAQs where is_active=True
        parent_only: If true, only return parent FAQs (parent_id IS NULL)
    
    Returns:
        List of FAQs sorted by display_order, then created_at
        
    Common usage patterns:
    - Frontend chat: active_only=true&parent_only=true (initial FAQ buttons)
    - Admin panel: no filters (show all for editing)
    - FAQ tree: active_only=true (build full hierarchy)
    """
    # Build query with filters
    query = db.query(FAQ).filter(FAQ.chatbot_id == chatbot_id)
    
    if active_only:
        query = query.filter(FAQ.is_active == True)
    
    if parent_only:
        query = query.filter(FAQ.parent_id == None)
    
    # Sort by display_order first, then creation date
    faqs = query.order_by(FAQ.display_order, FAQ.created_at).all()
    return faqs


@router.get("/faqs/{faq_id}", response_model=FAQResponse)
def get_faq(faq_id: int, db: Session = Depends(get_db)):
    """
    Get details of a specific FAQ by ID.
    
    Path parameters:
        faq_id: Unique identifier of the FAQ
    
    Returns:
        The FAQ with all details including question, answer, parent_id, etc.
        
    Raises:
        404: If FAQ with given ID doesn't exist
    """
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
    return faq


@router.patch("/faqs/{faq_id}", response_model=FAQResponse)
def update_faq(faq_id: int, faq_update: FAQUpdate, db: Session = Depends(get_db)):
    """
    Update an existing FAQ (partial update).
    
    Uses PATCH method for partial updates - only send fields you want to change.
    Unset fields are ignored (won't be changed).
    
    Path parameters:
        faq_id: ID of the FAQ to update
    
    Request body (all fields optional):
        question: New question text
        answer: New answer text
        parent_id: New parent FAQ ID (or None to make it a parent FAQ)
        is_active: New active status
        display_order: New display order
    
    Returns:
        The updated FAQ
        
    Raises:
        404: If FAQ doesn't exist
        400: If new question conflicts with existing FAQ
        
    Validation:
    - If question is updated, checks for duplicates (excluding current FAQ)
    - Question text is automatically trimmed
    """
    # Find the FAQ to update
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
    
    # If question is being updated, check for duplicates
    if faq_update.question is not None:
        trimmed_new_question = faq_update.question.strip()
        
        # Only check if the question is actually changing
        if trimmed_new_question != faq.question:
            existing_faq = db.query(FAQ).filter(
                FAQ.chatbot_id == faq.chatbot_id,
                FAQ.question == trimmed_new_question,
                FAQ.id != faq_id  # Exclude the current FAQ
            ).first()
            
            if existing_faq:
                raise HTTPException(
                    status_code=400, 
                    detail="This question already exists for this chatbot"
                )
    
    # Apply updates (only fields that were provided)
    update_data = faq_update.model_dump(exclude_unset=True)
    for field_name, new_value in update_data.items():
        # Special handling: trim question text
        if field_name == 'question' and new_value is not None:
            new_value = new_value.strip()
        setattr(faq, field_name, new_value)
    
    db.commit()
    db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}", status_code=204)
def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    """
    Delete an FAQ permanently.
    
    Path parameters:
        faq_id: ID of the FAQ to delete
    
    Returns:
        204 No Content on success
        
    Raises:
        404: If FAQ doesn't exist
        
    Warning:
        If this FAQ has child FAQs, they will also be deleted (cascade delete).
        Consider deactivating (is_active=False) instead of deleting if you want
        to preserve the FAQ hierarchy.
    """
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
    
    # SQLAlchemy cascade delete handles child FAQs
    db.delete(faq)
    db.commit()
