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
from app.services.faq_service import FAQService
from app.dependencies.cache import get_faq_service

router = APIRouter()


@router.post("/chatbots/{chatbot_id}/faqs", response_model=FAQResponse, status_code=201)
def create_faq(
    chatbot_id: int,
    faq: FAQCreate,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
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
    
    # Create the FAQ using service
    new_faq = faq_service.create_faq(chatbot_id, faq, db)
    return new_faq


@router.get("/chatbots/{chatbot_id}/faqs", response_model=List[FAQResponse])
def list_faqs(
    chatbot_id: int,
    active_only: bool = False,
    parent_only: bool = False,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
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
    # Use service to get FAQs (not cached for list operations)
    faqs = faq_service.get_all_faqs(chatbot_id, db, active_only, parent_only)
    return faqs


@router.get("/faqs/{faq_id}", response_model=FAQResponse)
def get_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
    """
    Get details of a specific FAQ by ID.
    
    Path parameters:
        faq_id: Unique identifier of the FAQ
    
    Returns:
        The FAQ with all details including question, answer, parent_id, etc.
        
    Raises:
        404: If FAQ with given ID doesn't exist
    """
    faq = faq_service.get_faq_by_id(faq_id, db)
    if not faq:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
    return faq


@router.patch("/faqs/{faq_id}", response_model=FAQResponse)
def update_faq(
    faq_id: int,
    faq_update: FAQUpdate,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
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
    - Cache is automatically invalidated
    """
    # If question is being updated, check for duplicates
    if faq_update.question is not None:
        faq = faq_service.get_faq_by_id(faq_id, db)
        if not faq:
            raise HTTPException(
                status_code=404,
                detail=entity_not_found_error("FAQ", faq_id)
            )
        
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
            
            # Trim the question in the update data
            faq_update.question = trimmed_new_question
    
    # Update using service (handles cache invalidation)
    updated_faq = faq_service.update_faq(faq_id, faq_update, db)
    
    if not updated_faq:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
    
    return updated_faq


@router.delete("/faqs/{faq_id}", status_code=204)
def delete_faq(
    faq_id: int,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
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
        Cache is automatically invalidated.
    """
    # Delete using service (handles cache invalidation)
    deleted = faq_service.delete_faq(faq_id, db)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("FAQ", faq_id)
        )
