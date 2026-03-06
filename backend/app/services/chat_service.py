"""
Chat Service Module

Handles all chat-related business logic including:
- Starting new chat sessions
- Processing user messages through a waterfall pattern:
  1. Try workflow nodes (trigger/response)
  2. Try FAQ exact match (with Redis caching)
  3. Try RAG (PDF documents)
  4. Fallback to default response
- Managing conversation state and message history

This is the core of the chatbot's intelligence.
"""

from sqlalchemy.orm import Session
from typing import Optional, Tuple, List, Dict
from app.models.chatbot import Chatbot
from app.models.workflow import Workflow
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.node import Node
from app.models.edge import Edge
from app.models.faq import FAQ
from app.logging_config import get_logger
from app.config import DEFAULT_BOT_RESPONSE
from app.utils import entity_not_found_error, no_active_workflow_error
from app.services.faq_service import FAQService

logger = get_logger(__name__)


def _get_all_trigger_nodes(chatbot_id: int, db: Session) -> List[Dict[str, any]]:
    """
    Get all trigger nodes from all workflows for a chatbot.
    
    Args:
        chatbot_id: ID of the chatbot
        db: Database session
        
    Returns:
        List of trigger node dictionaries with id, text, and workflow_id
    """
    logger.debug(f"Getting all trigger nodes for chatbot_id={chatbot_id}")
    
    trigger_nodes = db.query(Node).join(Workflow).filter(
        Workflow.chatbot_id == chatbot_id,
        Node.node_type == "trigger"
    ).all()
    
    result = [
        {
            "id": node.id,
            "text": node.text,
            "workflow_id": node.workflow_id
        }
        for node in trigger_nodes
    ]
    
    logger.info(f"Found {len(result)} trigger nodes")
    return result


def _get_node_children(node_id: int, db: Session) -> List[Dict[str, any]]:
    """
    Get all child nodes (response options) for a given node.
    
    Args:
        node_id: ID of the parent node
        db: Database session
        
    Returns:
        List of child node dictionaries with id and text
    """
    logger.debug(f"Getting children for node_id={node_id}")
    
    # Find all edges from this node
    edges = db.query(Edge).filter(Edge.from_node_id == node_id).all()
    
    if not edges:
        logger.debug("No edges found from this node")
        return []
    
    # Get all child nodes
    child_node_ids = [edge.to_node_id for edge in edges]
    child_nodes = db.query(Node).filter(Node.id.in_(child_node_ids)).all()
    
    result = [
        {
            "id": node.id,
            "text": node.text
        }
        for node in child_nodes
    ]
    
    logger.info(f"Found {len(result)} child nodes")
    return result


def _find_node_by_text(text: str, chatbot_id: int, db: Session) -> Optional[Node]:
    """
    Find a node by its exact text within a chatbot's workflows.
    
    Args:
        text: The node text to search for
        chatbot_id: ID of the chatbot
        db: Database session
        
    Returns:
        Node if found, None otherwise
    """
    logger.debug(f"Searching for node with text: '{text[:50]}...'")
    
    node = db.query(Node).join(Workflow).filter(
        Workflow.chatbot_id == chatbot_id,
        Node.text == text
    ).first()
    
    if node:
        logger.info(f"Found node_id={node.id}, type={node.node_type}")
    else:
        logger.debug("Node not found")
    
    return node


def _find_workflow_response(session: ChatSession, user_message: str, db: Session) -> Optional[str]:
    """
    Find a workflow response for an exact-match trigger node.

    Deprecated — no longer called by process_message.
    The trigger-node approach via _find_node_by_text / _get_node_children replaced this.
    Retained for reference and potential backward-compatibility use.

    Args:
        session: Current chat session
        user_message: User's message text
        db: Database session

    Returns:
        Response text if a matching trigger→response edge exists, None otherwise
    """
    logger.debug(f"Checking workflow for exact match: '{user_message[:50]}...'")
    matching_input = db.query(Node).filter(
        Node.workflow_id == session.workflow_id,
        Node.node_type == "trigger",
        Node.text == user_message
    ).first()

    if not matching_input:
        logger.debug("No workflow match found")
        return None

    edge = db.query(Edge).filter(Edge.from_node_id == matching_input.id).first()
    if not edge:
        logger.debug("Matching input found but no edge")
        return None

    output_node = db.query(Node).filter(
        Node.id == edge.to_node_id,
        Node.node_type == "response"
    ).first()

    if output_node:
        logger.info(f"Workflow match found: trigger_node={matching_input.id} -> response_node={output_node.id}")
    return output_node.text if output_node else None


def _find_faq_response(session: ChatSession, user_message: str, db: Session) -> Tuple[Optional[str], List[str]]:
    """
    Find an FAQ response and child options for an exact-match question.

    Deprecated — no longer called by process_message.
    FAQService.get_faq_response (with Redis caching) replaced this direct DB lookup.
    Retained for reference.

    Args:
        session: Current chat session
        user_message: User's message text
        db: Database session

    Returns:
        Tuple of (answer text or None, list of child question option strings)
    """
    logger.debug(f"Checking FAQ for exact match: '{user_message[:50]}...'")
    matching_faq = db.query(FAQ).filter(
        FAQ.chatbot_id == session.chatbot_id,
        FAQ.question == user_message,
        FAQ.is_active == True
    ).first()

    if not matching_faq:
        logger.debug("No FAQ match found")
        return None, []

    child_faqs = db.query(FAQ).filter(
        FAQ.parent_id == matching_faq.id,
        FAQ.is_active == True
    ).order_by(FAQ.display_order, FAQ.created_at).all()

    options = [child.question for child in child_faqs]
    logger.info(f"FAQ match found: faq_id={matching_faq.id}, child_options={len(options)}")
    return matching_faq.answer, options


def _find_rag_response(user_message: str, db: Session) -> Optional[str]:
    """
    Query RAG system for answer based on uploaded PDF documents.
    
    Args:
        user_message: User's question
        db: Database session (reserved for future use)
        
    Returns:
        - Answer string if relevant documents found
        - "I don't know..." if no relevant documents
        - None if RAG system unavailable (triggers fallback to default)
    """
    logger.debug(f"Attempting RAG query: '{user_message[:50]}...'")
    try:
        from app.services.rag_service import get_rag_service
        
        # Get RAG service (singleton)
        rag_service = get_rag_service()
        
        # Check if RAG is available
        if not rag_service.is_available():
            logger.debug("RAG service not available")
            return None
        
        # Get RAG answer
        logger.info("Querying RAG service...")
        answer = rag_service.get_rag_response(user_message)
        logger.info(f"RAG response received: {len(answer)} characters")
        
        return answer
        
    except Exception as e:
        # Log error but don't break chat
        logger.error(f"RAG error: {e}", exc_info=True)
        return None


def start_chat_session(chatbot_id: int, db: Session) -> Tuple[ChatSession, List[Dict[str, any]]]:
    """
    Start a new chat session and return all trigger nodes as initial options.
    
    Args:
        chatbot_id: ID of the chatbot
        db: Database session
        
    Returns:
        Tuple of (ChatSession object, list of trigger node options)
        
    Raises:
        ValueError: If chatbot not found
    """
    logger.info(f"Starting chat session for chatbot_id={chatbot_id}")
    
    # Find the chatbot
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not chatbot:
        logger.warning(f"Chatbot not found: {chatbot_id}")
        raise ValueError(entity_not_found_error("Chatbot", chatbot_id))
    
    # Create a new chat session (no specific workflow_id needed anymore)
    session = ChatSession(
        chatbot_id=chatbot_id,
        workflow_id=None  # No single active workflow
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Get all trigger nodes to show as initial options
    trigger_nodes = _get_all_trigger_nodes(chatbot_id, db)
    
    logger.info(f"Chat session created: session_id={session.id}, trigger_nodes={len(trigger_nodes)}")
    return session, trigger_nodes


def process_message(
    session_id: int,
    user_message: str,
    db: Session,
    faq_service: FAQService
) -> Tuple[str, List[Dict[str, any]], ChatSession]:
    """
    Process a user message and return bot response with optional child node options.
    Uses a waterfall pattern to find the best response type.
    Saves both user and bot messages to database.
    
    Message Processing Flow (in order of priority):
    1. Workflow Nodes - Check if message matches any trigger/response node text
    2. FAQs - Check if message matches any FAQ question (with Redis caching)
    3. RAG - Query PDF documents using AI
    4. Default - Fallback message if nothing matches
    
    Args:
        session_id: ID of the chat session
        user_message: User's message (already trimmed by schema validator)
        db: Database session
        faq_service: FAQ service with caching support
        
    Returns:
        Tuple of (bot_response_text, next_options_list, chat_session_object)
        - bot_response_text: The chatbot's reply
        - next_options_list: List of dicts with 'id' and 'text' for next conversation steps
        - chat_session_object: The ChatSession instance
        
    Raises:
        ValueError: If chat session not found in database
    """
    logger.info(f"Processing message for session_id={session_id}: '{user_message[:50]}...'")
    
    # Step 0: Validate that the chat session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        logger.warning(f"Chat session not found: {session_id}")
        raise ValueError(entity_not_found_error("Chat session", session_id))
    
    # Initialize default values
    bot_response = DEFAULT_BOT_RESPONSE
    next_options: List[Dict[str, any]] = []

    # ========================================================================
    # STEP 1: Try Workflow Nodes (Highest Priority)
    # ========================================================================
    # Check if user message matches any trigger or response node text
    matched_node = _find_node_by_text(user_message, session.chatbot_id, db)
    
    if matched_node:
        # Found a matching node in the workflow graph
        child_nodes = _get_node_children(matched_node.id, db)
        
        if child_nodes:
            # This node has children - use its bot_message as the reply,
            # then show the child nodes as the next conversation options.
            # Fall back to a generic prompt only when no bot_message is set.
            bot_response = matched_node.bot_message or "Please choose:"
            next_options = child_nodes
            logger.info(f"Workflow node matched: '{matched_node.text}' with {len(child_nodes)} child options")
        else:
            # This is a leaf node (no children) - use its bot_message as the
            # final response. Fall back to the node's label text only if
            # bot_message was never set.
            bot_response = matched_node.bot_message or matched_node.text
            logger.info(f"Workflow leaf node matched: '{matched_node.text}' - final response")
    
    # ========================================================================
    # STEP 2: Try FAQ System (Second Priority) - with Redis caching
    # ========================================================================
    else:
        faq_answer, faq_child_questions = faq_service.get_faq_response(
            session.chatbot_id, user_message, db
        )
        
        if faq_answer is not None:
            # Found an FAQ match
            bot_response = faq_answer
            # Convert FAQ child questions to the expected format (list of dicts)
            next_options = [{"text": question} for question in faq_child_questions]
            logger.info(f"FAQ matched with {len(faq_child_questions)} child questions")
        
        # ====================================================================
        # STEP 3: Try RAG System (Third Priority)
        # ====================================================================
        else:
            rag_answer = _find_rag_response(user_message, db)
            
            if rag_answer is not None:
                # RAG system found relevant information in PDF documents
                bot_response = rag_answer
                logger.info("Response generated from RAG (PDF documents)")
            
            # ================================================================
            # STEP 4: Default Fallback (Last Resort)
            # ================================================================
            else:
                # Nothing matched - use default "I don't know" response
                logger.warning(f"No match found for: '{user_message[:50]}...' - using default response")
    
    # ========================================================================
    # STEP 5: Save Conversation to Database
    # ========================================================================
    # Persist both user message and bot response for conversation history
    _save_chat_messages(session_id, user_message, bot_response, db)
    
    logger.info(f"Message processing complete. Response: {len(bot_response)} chars, Next options: {len(next_options)}")
    return bot_response, next_options, session


def _save_chat_messages(session_id: int, user_message: str, bot_response: str, db: Session) -> None:
    """
    Save user and bot messages to database.
    
    Args:
        session_id: ID of the chat session
        user_message: User's message text
        bot_response: Bot's response text
        db: Database session
    """
    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        sender="user",
        message_text=user_message
    )
    db.add(user_msg)
    
    # Save bot message
    bot_msg = ChatMessage(
        session_id=session_id,
        sender="bot",
        message_text=bot_response
    )
    db.add(bot_msg)
    
    db.commit()


def check_sync_response(
    session_id: int,
    user_message: str,
    db: Session,
    faq_service: FAQService,
) -> Tuple[Optional[str], List[Dict[str, any]]]:
    """
    Check Workflow and FAQ for an instant (synchronous) answer.

    Used by the async queue endpoint BEFORE deciding to enqueue to RabbitMQ.
    If a static answer is found here, there is no need to go to the RAG worker.

    Priority:
        1. Workflow node exact match
        2. FAQ exact match (with Redis cache)

    Args:
        session_id:  Existing chat session ID.
        user_message: User's message text.
        db:           Database session.
        faq_service:  FAQ service with caching.

    Returns:
        Tuple (bot_response, next_options) if a static match was found,
        or (None, []) if nothing matched (RAG path needed).

    Raises:
        ValueError: If chat session not found.
    """
    logger.debug(
        f"check_sync_response: session_id={session_id} "
        f"message='{user_message[:50]}...'"
    )

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError(entity_not_found_error("Chat session", session_id))

    # ── Step 1: Workflow node ──────────────────────────────────────────────
    matched_node = _find_node_by_text(user_message, session.chatbot_id, db)
    if matched_node:
        child_nodes = _get_node_children(matched_node.id, db)
        if child_nodes:
            bot_response = matched_node.bot_message or "Please choose:"
            next_options = child_nodes
        else:
            bot_response = matched_node.bot_message or matched_node.text
            next_options = []
        logger.info(f"Sync match (workflow) for session_id={session_id}")
        _save_chat_messages(session_id, user_message, bot_response, db)
        return bot_response, next_options

    # ── Step 2: FAQ (with Redis cache) ────────────────────────────────────
    faq_answer, faq_child_questions = faq_service.get_faq_response(
        session.chatbot_id, user_message, db
    )
    if faq_answer is not None:
        next_options = [{"text": q} for q in faq_child_questions]
        logger.info(f"Sync match (FAQ) for session_id={session_id}")
        _save_chat_messages(session_id, user_message, faq_answer, db)
        return faq_answer, next_options

    # No static match found — caller should route to RAG worker
    logger.debug(f"No sync match for session_id={session_id} — RAG path needed")
    return None, []


def process_rag_message(
    session_id: int,
    user_message: str,
    db: Session,
) -> Tuple[str, List[Dict[str, any]], ChatSession]:
    """
    Process a message using ONLY the RAG pipeline + default fallback.

    Called by ChatWorker — Workflow and FAQ were already checked in the
    queue endpoint before the job was enqueued, so we skip straight to RAG.

    Saves both user and bot messages to the database.

    Args:
        session_id:   Existing chat session ID.
        user_message: User's message text.
        db:           Database session.

    Returns:
        Tuple (bot_response, next_options, session)

    Raises:
        ValueError: If chat session not found.
    """
    logger.info(
        f"process_rag_message: session_id={session_id} "
        f"message='{user_message[:50]}...'"
    )

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError(entity_not_found_error("Chat session", session_id))

    # ── RAG ───────────────────────────────────────────────────────────────
    rag_answer = _find_rag_response(user_message, db)

    if rag_answer is not None:
        bot_response = rag_answer
        logger.info(f"RAG answer generated for session_id={session_id}")
    else:
        # Default fallback
        bot_response = DEFAULT_BOT_RESPONSE
        logger.warning(
            f"RAG returned nothing for session_id={session_id} — using default"
        )

    _save_chat_messages(session_id, user_message, bot_response, db)

    return bot_response, [], session
