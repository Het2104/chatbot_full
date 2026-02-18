"""
Nodes Router Module

Provides CRUD endpoints for managing nodes within workflows.

Nodes are the building blocks of conversation workflows:
- Trigger nodes: Start conversations (e.g., "Check Order Status")
- Response nodes: Bot replies (e.g., "Please provide your order number")

Nodes are connected by edges to form conversation flows.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.workflow import Workflow
from app.models.node import Node
from app.schemas.node import NodeCreate, NodeResponse, NodeUpdate
from app.utils import entity_not_found_error

router = APIRouter()


@router.post("/workflows/{workflow_id}/nodes", response_model=NodeResponse, status_code=201)
def create_node(workflow_id: int, node: NodeCreate, db: Session = Depends(get_db)):
    """
    Create a new node within a workflow.
    
    Nodes come in two types:
    1. Trigger nodes: Entry points for conversations (user-selectable options)
    2. Response nodes: Bot responses (displayed after user input)
    
    Path parameters:
        workflow_id: ID of the parent workflow
    
    Request body:
        node_type: Must be either "trigger" or "response"
        text: The actual text displayed to user or sent as bot response
    
    Returns:
        The created node with assigned ID
        
    Raises:
        404: If workflow doesn't exist
        400: If node_type is invalid or duplicate trigger text detected
        
    Validation Rules:
    - node_type must be exactly "trigger" or "response"
    - Trigger nodes with identical text cannot exist in the same workflow
      (prevents user confusion - they wouldn't know which one was selected)
    """
    # Verify parent workflow exists
    parent_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not parent_workflow:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Workflow", workflow_id)
        )
    
    # Validate node type (strict validation)
    if node.node_type not in {"trigger", "response"}:
        raise HTTPException(
            status_code=400, 
            detail="Invalid node_type. Must be 'trigger' or 'response'"
        )

    # Prevent duplicate trigger nodes (business rule)
    # This prevents user confusion when clicking trigger buttons
    if node.node_type == "trigger":
        existing_trigger = db.query(Node).filter(
            Node.workflow_id == workflow_id,
            Node.node_type == "trigger",
            Node.text == node.text
        ).first()
        
        if existing_trigger:
            raise HTTPException(
                status_code=400,
                detail=f"A trigger node with text '{node.text}' already exists in this workflow"
            )

    # Create the node
    new_node = Node(
        workflow_id=workflow_id,
        node_type=node.node_type,
        text=node.text,
        position_x=node.position_x,
        position_y=node.position_y
    )
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node


@router.get("/workflows/{workflow_id}/nodes", response_model=List[NodeResponse])
def list_nodes(workflow_id: int, db: Session = Depends(get_db)):
    """
    List all nodes in a workflow.
    
    Returns both trigger and response nodes. The frontend typically:
    - Displays trigger nodes as clickable buttons to start conversations  
    - Uses edges to determine which response nodes follow which triggers
    
    Path parameters:
        workflow_id: ID of the workflow
    
    Returns:
        List of all nodes in the workflow
        
    Raises:
        404: If workflow doesn't exist
    """
    # Verify workflow exists
    parent_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not parent_workflow:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Workflow", workflow_id)
        )
    
    # Get all nodes for this workflow
    workflow_nodes = db.query(Node).filter(Node.workflow_id == workflow_id).all()
    return workflow_nodes


@router.delete("/nodes/{node_id}", status_code=204)
def delete_node(node_id: int, db: Session = Depends(get_db)):
    """
    Delete a node.
    
    This also removes any edges connected to this node (cascade delete).
    
    Path parameters:
        node_id: ID of the node to delete
    
    Returns:
        204 No Content on success
        
    Raises:
        404: If node doesn't exist
        
    Warning:
        Deleting a node will break conversation flows that depend on it.
        Any edges pointing to or from this node will also be deleted.
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Node", node_id)
        )
    
    # SQLAlchemy cascade delete handles connected edges
    db.delete(node)
    db.commit()
    return None


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
def update_node(node_id: int, node_update: NodeUpdate, db: Session = Depends(get_db)):
    """
    Update a node's text or position.
    
    This endpoint is used to:
    - Update node text (chatbot message content)
    - Save node position when dragged in visual workflow editor
    
    Path parameters:
        node_id: ID of the node to update
    
    Request body (all fields optional):
        text: New text content for the node
        position_x: Horizontal position in pixels (for visual editor)
        position_y: Vertical position in pixels (for visual editor)
    
    Returns:
        The updated node with all current values
        
    Raises:
        404: If node doesn't exist
        400: If trying to create duplicate trigger text in same workflow
    
    Note:
        This does NOT change chatbot functionality, only visual layout.
        Node positions are purely for the visual workflow editor.
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Node", node_id)
        )
    
    # Update text if provided
    if node_update.text is not None:
        # Check for duplicate trigger text (business rule)
        if node.node_type == "trigger" and node_update.text != node.text:
            existing_trigger = db.query(Node).filter(
                Node.workflow_id == node.workflow_id,
                Node.node_type == "trigger",
                Node.text == node_update.text,
                Node.id != node_id
            ).first()
            
            if existing_trigger:
                raise HTTPException(
                    status_code=400,
                    detail=f"A trigger node with text '{node_update.text}' already exists in this workflow"
                )
        
        node.text = node_update.text
    
    # Update position if provided (visual editor only, doesn't affect chatbot logic)
    if node_update.position_x is not None:
        node.position_x = node_update.position_x
    
    if node_update.position_y is not None:
        node.position_y = node_update.position_y
    
    db.commit()
    db.refresh(node)
    return node
