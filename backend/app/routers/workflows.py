"""
Workflows Router Module

Provides CRUD endpoints for managing conversation workflows.
Workflows are directed graphs of nodes (triggers and responses) connected by edges.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.chatbot import Chatbot
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowResponse
from app.utils import entity_not_found_error

router = APIRouter()


@router.post("/chatbots/{chatbot_id}/workflows", response_model=WorkflowResponse, status_code=201)
def create_workflow(chatbot_id: int, workflow: WorkflowCreate, db: Session = Depends(get_db)):
    """
    Create a new workflow for a chatbot.
    
    A workflow is a conversation flow consisting of:
    - Trigger nodes (conversation starters)
    - Response nodes (bot replies)
    - Edges connecting nodes (conversation paths)
    
    Path parameters:
        chatbot_id: ID of the chatbot to create the workflow for
    
    Request body:
        name: Display name for the workflow
    
    Returns:
        The created workflow (initially inactive)
        
    Raises:
        404: If chatbot with given ID doesn't exist
        
    Note:
        New workflows are created as inactive. Use the activate endpoint to activate them.
    """
    # Verify that parent chatbot exists
    parent_chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not parent_chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    # Create workflow (inactive by default)
    new_workflow = Workflow(
        chatbot_id=chatbot_id,
        name=workflow.name,
        is_active=False
    )
    db.add(new_workflow)
    db.commit()
    db.refresh(new_workflow)
    return new_workflow


@router.get("/chatbots/{chatbot_id}/workflows", response_model=List[WorkflowResponse])
def list_workflows(chatbot_id: int, db: Session = Depends(get_db)):
    """
    List all workflows for a specific chatbot.
    
    Path parameters:
        chatbot_id: ID of the chatbot
    
    Returns:
        List of all workflows for the chatbot
        
    Raises:
        404: If chatbot with given ID doesn't exist
    """
    # Verify that chatbot exists
    parent_chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not parent_chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    # Get all workflows for this chatbot
    chatbot_workflows = db.query(Workflow).filter(Workflow.chatbot_id == chatbot_id).all()
    return chatbot_workflows


@router.put("/workflows/{workflow_id}/activate", response_model=WorkflowResponse)
def activate_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """
    Activate a workflow (and deactivate all other workflows for the same chatbot).
    
    Business Rule: Only one workflow can be active per chatbot at a time.
    When a workflow is activated, all other workflows for the same chatbot are
    automatically deactivated.
    
    Path parameters:
        workflow_id: ID of the workflow to activate
    
    Returns:
        The activated workflow
        
    Raises:
        404: If workflow with given ID doesn't exist
        
    Note:
        This is a PUT request (not POST) because it's an idempotent state change.
        Calling it multiple times has the same effect as calling it once.
    """
    # Find the workflow to activate
    target_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not target_workflow:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Workflow", workflow_id)
        )
    
    # Deactivate all other workflows for this chatbot
    db.query(Workflow).filter(
        Workflow.chatbot_id == target_workflow.chatbot_id
    ).update({"is_active": False})
    
    # Activate the target workflow
    target_workflow.is_active = True
    db.commit()
    db.refresh(target_workflow)
    return target_workflow


@router.delete("/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """
    Delete a workflow and all its nodes and edges.
    
    This is a cascading delete that removes:
    - The workflow itself
    - All nodes in the workflow
    - All edges connecting those nodes
    
    Path parameters:
        workflow_id: ID of the workflow to delete
    
    Returns:
        204 No Content on success
        
    Raises:
        404: If workflow with given ID doesn't exist
        
    Warning:
        This operation is irreversible. The conversation flow will be permanently lost.
    """
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Workflow", workflow_id)
        )
    
    # SQLAlchemy cascade delete handles all related nodes and edges
    db.delete(workflow)
    db.commit()
    return None
