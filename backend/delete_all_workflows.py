"""
Script to delete all workflows from the database
This will cascade delete all associated nodes, edges, and chat sessions
"""
from sqlalchemy.orm import Session
from database import SessionLocal
from app.models.workflow import Workflow
from app.models.node import Node
from app.models.edge import Edge
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.logging_config import get_logger

logger = get_logger(__name__)


def delete_all_workflows():
    """Delete all workflows from the database"""
    db: Session = SessionLocal()
    try:
        # Get counts before deletion
        workflow_count = db.query(Workflow).count()
        node_count = db.query(Node).count()
        edge_count = db.query(Edge).count()
        session_count = db.query(ChatSession).count()
        
        logger.info(f"Found {workflow_count} workflows, {node_count} nodes, {edge_count} edges, {session_count} sessions")
        
        if workflow_count == 0:
            print("No workflows found in database")
            return
        
        # Delete in correct order to avoid foreign key constraints
        # 1. Delete chat messages
        message_count = db.query(ChatMessage).delete()
        logger.info(f"Deleted {message_count} chat messages")
        
        # 2. Delete chat sessions
        db.query(ChatSession).delete()
        logger.info(f"Deleted {session_count} chat sessions")
        
        # 3. Delete edges
        db.query(Edge).delete()
        logger.info(f"Deleted {edge_count} edges")
        
        # 4. Delete nodes
        db.query(Node).delete()
        logger.info(f"Deleted {node_count} nodes")
        
        # 5. Delete workflows
        db.query(Workflow).delete()
        logger.info(f"Deleted {workflow_count} workflows")
        
        db.commit()
        
        print(f"✓ Successfully deleted:")
        print(f"  - {workflow_count} workflows")
        print(f"  - {node_count} nodes")
        print(f"  - {edge_count} edges")
        print(f"  - {session_count} chat sessions")
        print(f"  - {message_count} chat messages")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting workflows: {e}", exc_info=True)
        print(f"✗ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Deleting all workflows...")
    delete_all_workflows()
