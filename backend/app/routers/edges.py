"""
Edges Router Module

Provides CRUD endpoints for managing edges (connections between nodes).

Edges create the conversation flow by connecting nodes:
- From trigger node → to response node
- From response node → to another response node

Edges form a directed graph that defines how conversations progress.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.workflow import Workflow
from app.models.node import Node
from app.models.edge import Edge
from app.schemas.edge import EdgeCreate, EdgeResponse
from app.utils import entity_not_found_error

router = APIRouter()


@router.post("/workflows/{workflow_id}/edges", response_model=EdgeResponse, status_code=201)
def create_edge(workflow_id: int, edge: EdgeCreate, db: Session = Depends(get_db)):
    """
    Create a new edge to connect two nodes in a workflow.
    
    Edges define the conversation flow by connecting nodes:
    - Trigger node → Response node (initial bot reply)
    - Response node → Response node (follow-up conversation)
    
    Path parameters:
        workflow_id: ID of the parent workflow
    
    Request body:
        from_node_id: Source node ID (where conversation is coming from)
        to_node_id: Target node ID (where conversation is going to)
    
    Returns:
        The created edge with assigned ID
        
    Raises:
        404: If workflow or either node doesn't exist
        400: If validation rules are violated
        
    Validation Rules:
    1. Both nodes must exist
    2. Both nodes must belong to the same workflow (cross-workflow edges not allowed)
    3. No self-loops (node cannot connect to itself)
    4. No duplicate edges (same from_node → to_node pair)
    
    These rules ensure a valid directed acyclic graph (DAG) structure.
    """
    # Verify parent workflow exists
    parent_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not parent_workflow:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Workflow", workflow_id)
        )

    # Verify both nodes exist
    source_node = db.query(Node).filter(Node.id == edge.from_node_id).first()
    target_node = db.query(Node).filter(Node.id == edge.to_node_id).first()

    if not source_node or not target_node:
        raise HTTPException(
            status_code=404, 
            detail="Source or target node not found"
        )

    # Rule: Both nodes must belong to the same workflow
    # This prevents creating nonsensical cross-workflow connections
    if source_node.workflow_id != workflow_id or target_node.workflow_id != workflow_id:
        raise HTTPException(
            status_code=400, 
            detail="Nodes must belong to the same workflow"
        )

    # Rule: Prevent self-loops (node → node)
    # Self-loops would create infinite conversation loops
    if source_node.id == target_node.id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot create edge from a node to itself"
        )

    # Rule: Prevent duplicate edges
    # Multiple identical edges would be redundant and confusing
    existing_edge = db.query(Edge).filter(
        Edge.from_node_id == edge.from_node_id,
        Edge.to_node_id == edge.to_node_id
    ).first()
    
    if existing_edge:
        raise HTTPException(
            status_code=400, 
            detail="Edge already exists between these nodes"
        )

    # Create the edge
    new_edge = Edge(
        workflow_id=workflow_id,
        from_node_id=edge.from_node_id,
        to_node_id=edge.to_node_id
    )
    db.add(new_edge)
    db.commit()
    db.refresh(new_edge)
    return new_edge


@router.get("/workflows/{workflow_id}/edges", response_model=List[EdgeResponse])
def list_edges(workflow_id: int, db: Session = Depends(get_db)):
    """
    List all edges in a workflow.
    
    The frontend uses this to:
    - Build the visual workflow graph
    - Understand conversation flow (which node leads to which)
    - Navigate the conversation tree during chat
    
    Path parameters:
        workflow_id: ID of the workflow
    
    Returns:
        List of all edges with from_node_id and to_node_id
        
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

    # Get all edges for this workflow
    workflow_edges = db.query(Edge).filter(Edge.workflow_id == workflow_id).all()
    return workflow_edges


@router.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: int, db: Session = Depends(get_db)):
    """
    Delete an edge (disconnect two nodes).
    
    This breaks the conversation flow between two nodes.
    The nodes themselves remain intact, only the connection is removed.
    
    Path parameters:
        edge_id: ID of the edge to delete
    
    Returns:
        204 No Content on success
        
    Raises:
        404: If edge doesn't exist
        
    Note:
        After deleting an edge, users will no longer be able to navigate
        from the source node to the target node in conversations.
    """
    edge = db.query(Edge).filter(Edge.id == edge_id).first()
    if not edge:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Edge", edge_id)
        )

    db.delete(edge)
    db.commit()
    return None
