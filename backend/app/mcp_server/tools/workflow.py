"""
Workflow MCP Tools
Lets an AI inspect and build workflows (nodes + edges) stored in the local PostgreSQL DB.
"""

import sys
import os

_this_file = os.path.abspath(__file__)
_backend_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(_this_file)))
)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from typing import Optional
from database import SessionLocal
from app.models.workflow import Workflow
from app.models.node import Node
from app.models.edge import Edge


def register_workflow_tools(mcp):

    @mcp.tool()
    def list_workflows(chatbot_id: int) -> dict:
        """
        List all workflows for a chatbot.
        Returns id, name, is_active, created_at, and node/edge counts for each.
        """
        db = SessionLocal()
        try:
            workflows = db.query(Workflow).filter(Workflow.chatbot_id == chatbot_id).all()
            result = []
            for w in workflows:
                node_count = db.query(Node).filter(Node.workflow_id == w.id).count()
                edge_count = db.query(Edge).filter(Edge.workflow_id == w.id).count()
                result.append({
                    "id": w.id,
                    "name": w.name,
                    "is_active": w.is_active,
                    "created_at": str(w.created_at),
                    "node_count": node_count,
                    "edge_count": edge_count,
                })
            return {"chatbot_id": chatbot_id, "workflows": result, "total": len(result)}
        finally:
            db.close()

    @mcp.tool()
    def get_workflow(workflow_id: int) -> dict:
        """
        Get a full workflow including all nodes and edges.
        Shows the complete graph structure so the AI can understand or extend it.
        """
        db = SessionLocal()
        try:
            w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not w:
                return {"error": f"Workflow {workflow_id} not found"}

            nodes = db.query(Node).filter(Node.workflow_id == workflow_id).all()
            edges = db.query(Edge).filter(Edge.workflow_id == workflow_id).all()

            node_list = [
                {
                    "id": n.id,
                    "node_type": n.node_type,
                    "text": n.text,
                    "bot_message": n.bot_message,
                    "position_x": n.position_x,
                    "position_y": n.position_y,
                }
                for n in nodes
            ]
            edge_list = [
                {
                    "id": e.id,
                    "from_node_id": e.from_node_id,
                    "to_node_id": e.to_node_id,
                }
                for e in edges
            ]
            return {
                "id": w.id,
                "chatbot_id": w.chatbot_id,
                "name": w.name,
                "is_active": w.is_active,
                "created_at": str(w.created_at),
                "nodes": node_list,
                "edges": edge_list,
            }
        finally:
            db.close()

    @mcp.tool()
    def create_workflow(chatbot_id: int, name: str) -> dict:
        """
        Create a new workflow for a chatbot.
        The workflow starts empty (no nodes/edges) and inactive.
        Returns the new workflow id so nodes can be added next.
        """
        db = SessionLocal()
        try:
            w = Workflow(chatbot_id=chatbot_id, name=name.strip(), is_active=False)
            db.add(w)
            db.commit()
            db.refresh(w)
            return {
                "id": w.id,
                "chatbot_id": w.chatbot_id,
                "name": w.name,
                "is_active": w.is_active,
                "created_at": str(w.created_at),
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    @mcp.tool()
    def add_node(
        workflow_id: int,
        node_type: str,
        text: str,
        bot_message: Optional[str] = None,
        position_x: Optional[int] = None,
        position_y: Optional[int] = None,
    ) -> dict:
        """
        Add a node to a workflow.
        node_type must be 'trigger' or 'response'.
        - trigger: represents a user intent / button label (text = label shown to user).
        - response: represents a bot reply (text = button name, bot_message = reply text).
        Returns the new node id so edges can be created referencing it.
        """
        if node_type not in ("trigger", "response"):
            return {"error": "node_type must be 'trigger' or 'response'"}

        text = text.strip()
        if not text:
            return {"error": "text cannot be empty"}

        db = SessionLocal()
        try:
            w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not w:
                return {"error": f"Workflow {workflow_id} not found"}

            # Prevent duplicate trigger text within the same workflow
            if node_type == "trigger":
                existing = (
                    db.query(Node)
                    .filter(
                        Node.workflow_id == workflow_id,
                        Node.node_type == "trigger",
                        Node.text == text,
                    )
                    .first()
                )
                if existing:
                    return {"error": f"A trigger node with text '{text}' already exists in this workflow"}

            node = Node(
                workflow_id=workflow_id,
                node_type=node_type,
                text=text,
                bot_message=bot_message,
                position_x=position_x,
                position_y=position_y,
            )
            db.add(node)
            db.commit()
            db.refresh(node)
            return {
                "id": node.id,
                "workflow_id": node.workflow_id,
                "node_type": node.node_type,
                "text": node.text,
                "bot_message": node.bot_message,
                "position_x": node.position_x,
                "position_y": node.position_y,
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    @mcp.tool()
    def add_edge(workflow_id: int, from_node_id: int, to_node_id: int) -> dict:
        """
        Connect two nodes with a directed edge (from_node → to_node).
        Both nodes must belong to the same workflow.
        No self-loops or duplicate edges are allowed.
        """
        if from_node_id == to_node_id:
            return {"error": "Self-loops are not allowed (from_node_id == to_node_id)"}

        db = SessionLocal()
        try:
            # Validate both nodes belong to the workflow
            from_node = db.query(Node).filter(
                Node.id == from_node_id, Node.workflow_id == workflow_id
            ).first()
            to_node = db.query(Node).filter(
                Node.id == to_node_id, Node.workflow_id == workflow_id
            ).first()

            if not from_node:
                return {"error": f"Node {from_node_id} not found in workflow {workflow_id}"}
            if not to_node:
                return {"error": f"Node {to_node_id} not found in workflow {workflow_id}"}

            # Check for duplicate edge
            existing = db.query(Edge).filter(
                Edge.from_node_id == from_node_id,
                Edge.to_node_id == to_node_id,
            ).first()
            if existing:
                return {"error": "An edge between these two nodes already exists"}

            edge = Edge(
                workflow_id=workflow_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
            )
            db.add(edge)
            db.commit()
            db.refresh(edge)
            return {
                "id": edge.id,
                "workflow_id": edge.workflow_id,
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    @mcp.tool()
    def activate_workflow(workflow_id: int) -> dict:
        """
        Activate a workflow. Automatically deactivates all other workflows for the same chatbot.
        Only one workflow can be active per chatbot at a time.
        """
        db = SessionLocal()
        try:
            w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not w:
                return {"error": f"Workflow {workflow_id} not found"}

            # Deactivate all other workflows for this chatbot
            db.query(Workflow).filter(
                Workflow.chatbot_id == w.chatbot_id,
                Workflow.id != workflow_id,
            ).update({"is_active": False})

            w.is_active = True
            db.commit()
            db.refresh(w)
            return {
                "id": w.id,
                "name": w.name,
                "is_active": w.is_active,
                "message": f"Workflow '{w.name}' is now active for chatbot {w.chatbot_id}",
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e)}
        finally:
            db.close()

    @mcp.tool()
    def get_trigger_nodes(chatbot_id: int) -> dict:
        """
        Get all trigger nodes across all workflows for a chatbot.
        Useful for seeing what user intents / entry points already exist.
        Each result shows the workflow it belongs to and whether that workflow is active.
        """
        db = SessionLocal()
        try:
            workflows = db.query(Workflow).filter(Workflow.chatbot_id == chatbot_id).all()
            workflow_map = {w.id: w for w in workflows}

            trigger_nodes = (
                db.query(Node)
                .filter(
                    Node.workflow_id.in_(list(workflow_map.keys())),
                    Node.node_type == "trigger",
                )
                .all()
            )

            result = [
                {
                    "node_id": n.id,
                    "text": n.text,
                    "workflow_id": n.workflow_id,
                    "workflow_name": workflow_map[n.workflow_id].name,
                    "workflow_active": workflow_map[n.workflow_id].is_active,
                }
                for n in trigger_nodes
            ]
            return {"chatbot_id": chatbot_id, "trigger_nodes": result, "total": len(result)}
        finally:
            db.close()
