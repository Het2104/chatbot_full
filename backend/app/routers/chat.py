"""
Chat Router Module

Provides REST API endpoints for chatbot conversations:
- Starting new chat sessions
- Sending messages and receiving responses

These are the main endpoints used by the frontend chat interface.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from app.schemas.chat import ChatStartRequest, ChatStartResponse, ChatMessageRequest, ChatMessageResponse, TriggerNodeOption, NodeOption
from app.services.chat_service import start_chat_session, process_message
from app.services.faq_service import FAQService
from app.dependencies.cache import get_faq_service
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/start", response_model=ChatStartResponse, status_code=201)
def start_chat(request: ChatStartRequest, db: Session = Depends(get_db)):
    """
    Start a new chat session for a specific chatbot.
    
    This endpoint:
    1. Creates a new ChatSession in the database
    2. Retrieves all trigger nodes from all workflows for this chatbot
    3. Returns session info + trigger nodes as initial conversation starters
    
    The frontend displays trigger nodes as clickable buttons to begin workflows.
    
    Request body:
        chatbot_id: ID of the chatbot to start a conversation with
    
    Returns:
        session_id: Unique identifier for this conversation session
        trigger_nodes: List of all available workflow triggers with their IDs and workflow IDs
        
    Raises:
        404: If chatbot with given ID doesn't exist
    """
    logger.info(f"Starting new chat session for chatbot_id={request.chatbot_id}")
    
    try:
        # Create session and fetch all available trigger nodes
        chat_session, available_triggers = start_chat_session(request.chatbot_id, db)
        
        # Convert internal dict format to API schema format
        trigger_options = [
            TriggerNodeOption(
                id=trigger_node["id"],
                text=trigger_node["text"],
                workflow_id=trigger_node["workflow_id"]
            )
            for trigger_node in available_triggers
        ]
        
        logger.info(f"Chat session created: session_id={chat_session.id}, available_triggers={len(trigger_options)}")
        
        return ChatStartResponse(
            session_id=chat_session.id,
            chatbot_id=chat_session.chatbot_id,
            trigger_nodes=trigger_options,
            started_at=chat_session.started_at
        )
        
    except ValueError as e:
        # Chatbot not found or validation error
        logger.warning(f"Failed to start chat session: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/message", response_model=ChatMessageResponse)
def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    faq_service: FAQService = Depends(get_faq_service)
):
    """
    Send a message to the chatbot and receive a response.
    
    This endpoint:
    1. Processes the user's message through the waterfall pattern:
       - Try workflow nodes
       - Try FAQ (with Redis caching)
       - Try RAG (PDF documents)
       - Fallback to default
    2. Saves both user and bot messages to database
    3. Returns bot response with optional next conversation options
    
    Request body:
        session_id: ID of the current chat session
        message: User's message text (will be trimmed automatically)
    
    Returns:
        bot_response: The chatbot's reply
        options: List of suggested next messages (clickable buttons in UI)
            - For workflow nodes: child nodes to continue the conversation
            - For FAQs: child FAQs for follow-up questions
            - For RAG: empty (no predefined options)
        
    Raises:
        404: If chat session with given ID doesn't exist
    """
    logger.info(f"Received message for session_id={request.session_id}: '{request.message[:50]}...'")
    
    try:
        # Process message through the waterfall pattern (with FAQ caching)
        bot_reply, next_conversation_options, chat_session = process_message(
            request.session_id, 
            request.message, 
            db,
            faq_service
        )
        
        # Convert internal dict format to API schema format
        formatted_options = [
            NodeOption(
                id=option.get("id"),  # May be None for FAQ options
                text=option["text"]
            )
            for option in next_conversation_options
        ]
        
        logger.info(
            f"Message processed successfully. "
            f"Response length: {len(bot_reply)} chars, "
            f"Next options: {len(formatted_options)}"
        )
        
        return ChatMessageResponse(
            session_id=chat_session.id,
            user_message=request.message,
            bot_response=bot_reply,
            options=formatted_options,
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        # Session not found or validation error
        logger.warning(f"Failed to process message: {e}")
        raise HTTPException(status_code=404, detail=str(e))
