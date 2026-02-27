"""
FAQ Service

Class-based service for FAQ operations with Redis caching support.
Provides cache-first strategy for retrieving FAQs and automatic cache invalidation.
"""

import hashlib
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQUpdate, FAQResponse, FAQWithChildren
from app.services.redis_cache_service import RedisCacheService
from app.config import FAQ_CACHE_TTL, FAQ_CACHE_PREFIX
from app.logging_config import get_logger

logger = get_logger(__name__)


class FAQService:
    """
    Service layer for FAQ operations with caching support.
    
    Features:
    - Cache-first retrieval strategy
    - Automatic cache invalidation on updates/deletes
    - Hierarchical FAQ support (parent/child)
    - Deterministic cache key generation
    """
    
    def __init__(self, cache_service: RedisCacheService):
        """
        Initialize FAQ service.
        
        Args:
            cache_service: Redis cache service instance
        """
        self.cache = cache_service
    
    def _generate_cache_key(self, chatbot_id: int, question: str) -> str:
        """
        Generate deterministic cache key for FAQ.
        
        Args:
            chatbot_id: Chatbot ID
            question: FAQ question text
            
        Returns:
            Cache key string (e.g., "faq:chatbot:1:a3f5c8d9e2b1")
        """
        # Normalize question (lowercase, strip whitespace)
        normalized = question.lower().strip()
        
        # Hash for consistent key length and handling special characters
        question_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        
        # Namespace: faq:chatbot:{id}:{hash}
        return f"{FAQ_CACHE_PREFIX}:chatbot:{chatbot_id}:{question_hash}"
    
    def _generate_children_cache_key(self, chatbot_id: int, parent_id: int) -> str:
        """
        Generate cache key for FAQ children list.
        
        Args:
            chatbot_id: Chatbot ID
            parent_id: Parent FAQ ID
            
        Returns:
            Cache key string
        """
        return f"{FAQ_CACHE_PREFIX}:children:chatbot:{chatbot_id}:parent:{parent_id}"
    
    def _faq_to_dict(self, faq: FAQ) -> dict:
        """
        Convert FAQ SQLAlchemy model to dictionary for caching.
        
        Args:
            faq: FAQ model instance
            
        Returns:
            Dictionary representation
        """
        return {
            "id": faq.id,
            "chatbot_id": faq.chatbot_id,
            "question": faq.question,
            "answer": faq.answer,
            "parent_id": faq.parent_id,
            "is_active": faq.is_active,
            "display_order": faq.display_order,
            "created_at": faq.created_at.isoformat() if faq.created_at else None,
        }
    
    def get_faq_by_question(
        self,
        chatbot_id: int,
        question: str,
        db: Session,
        use_cache: bool = True
    ) -> Optional[FAQ]:
        """
        Get FAQ by exact question match with cache-first strategy.
        
        Args:
            chatbot_id: Chatbot ID
            question: FAQ question text (exact match)
            db: Database session
            use_cache: Whether to use cache (default: True)
            
        Returns:
            FAQ object if found, None otherwise
        """
        cache_key = self._generate_cache_key(chatbot_id, question)
        
        # Try cache first
        if use_cache and self.cache.is_available():
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                logger.debug(f"FAQ cache HIT: {cache_key}")
                # Reconstruct FAQ object from cached data
                faq = FAQ(**cached_data)
                return faq
        
        # Cache miss - query database
        logger.debug(f"FAQ cache MISS: {cache_key}")
        
        faq = db.query(FAQ).filter(
            FAQ.chatbot_id == chatbot_id,
            FAQ.question == question,
            FAQ.is_active == True
        ).first()
        
        if faq and use_cache:
            # Cache the result
            faq_data = self._faq_to_dict(faq)
            self.cache.set(cache_key, faq_data, ttl=FAQ_CACHE_TTL)
            logger.debug(f"FAQ cached: {cache_key} (TTL: {FAQ_CACHE_TTL}s)")
        
        return faq
    
    def get_child_faqs(
        self,
        chatbot_id: int,
        parent_id: int,
        db: Session,
        use_cache: bool = True
    ) -> List[FAQ]:
        """
        Get child FAQs for a parent FAQ with caching.
        
        Args:
            chatbot_id: Chatbot ID
            parent_id: Parent FAQ ID
            db: Database session
            use_cache: Whether to use cache
            
        Returns:
            List of child FAQ objects
        """
        cache_key = self._generate_children_cache_key(chatbot_id, parent_id)
        
        # Try cache first
        if use_cache and self.cache.is_available():
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                logger.debug(f"FAQ children cache HIT: {cache_key}")
                # Reconstruct FAQ objects from cached data
                return [FAQ(**faq_data) for faq_data in cached_data]
        
        # Cache miss - query database
        logger.debug(f"FAQ children cache MISS: {cache_key}")
        
        child_faqs = db.query(FAQ).filter(
            FAQ.parent_id == parent_id,
            FAQ.is_active == True
        ).order_by(FAQ.display_order, FAQ.created_at).all()
        
        if child_faqs and use_cache:
            # Cache the results
            children_data = [self._faq_to_dict(faq) for faq in child_faqs]
            self.cache.set(cache_key, children_data, ttl=FAQ_CACHE_TTL)
            logger.debug(f"FAQ children cached: {cache_key} ({len(children_data)} children)")
        
        return child_faqs
    
    def get_faq_response(
        self,
        chatbot_id: int,
        question: str,
        db: Session
    ) -> Tuple[Optional[str], List[str]]:
        """
        Get FAQ response and child options for chat service.
        Replaces _find_faq_response from chat_service.py
        
        Args:
            chatbot_id: Chatbot ID
            question: User's question text
            db: Database session
            
        Returns:
            Tuple of (answer text or None, list of child question options)
        """
        logger.debug(f"Checking FAQ for exact match: '{question[:50]}...'")
        
        # Get FAQ with caching
        matching_faq = self.get_faq_by_question(chatbot_id, question, db, use_cache=True)
        
        if not matching_faq:
            logger.debug("No FAQ match found")
            return None, []
        
        # Get child FAQs with caching
        child_faqs = self.get_child_faqs(chatbot_id, matching_faq.id, db, use_cache=True)
        
        options = [child.question for child in child_faqs]
        logger.info(f"FAQ match found: faq_id={matching_faq.id}, child_options={len(options)}")
        
        return matching_faq.answer, options
    
    def create_faq(
        self,
        chatbot_id: int,
        faq_data: FAQCreate,
        db: Session
    ) -> FAQ:
        """
        Create a new FAQ.
        
        Args:
            chatbot_id: Chatbot ID
            faq_data: FAQ creation data
            db: Database session
            
        Returns:
            Created FAQ object
        """
        faq = FAQ(
            chatbot_id=chatbot_id,
            question=faq_data.question,
            answer=faq_data.answer,
            parent_id=faq_data.parent_id,
            is_active=faq_data.is_active,
            display_order=faq_data.display_order,
        )
        
        db.add(faq)
        db.commit()
        db.refresh(faq)
        
        logger.info(f"Created FAQ: id={faq.id}, chatbot_id={chatbot_id}")
        
        # Note: We don't cache on create, cache will be populated on first read
        # This avoids caching data that might never be accessed
        
        return faq
    
    def update_faq(
        self,
        faq_id: int,
        faq_data: FAQUpdate,
        db: Session
    ) -> Optional[FAQ]:
        """
        Update an existing FAQ and invalidate cache.
        
        Args:
            faq_id: FAQ ID to update
            faq_data: Update data
            db: Database session
            
        Returns:
            Updated FAQ object or None if not found
        """
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        
        if not faq:
            return None
        
        # Store old question for cache invalidation
        old_question = faq.question
        old_chatbot_id = faq.chatbot_id
        
        # Update fields
        update_data = faq_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(faq, field, value)
        
        db.commit()
        db.refresh(faq)
        
        # Invalidate cache (both old and new question if changed)
        if old_question:
            old_cache_key = self._generate_cache_key(old_chatbot_id, old_question)
            self.cache.delete(old_cache_key)
            logger.debug(f"Invalidated cache (old): {old_cache_key}")
        
        if faq_data.question and faq_data.question != old_question:
            new_cache_key = self._generate_cache_key(faq.chatbot_id, faq.question)
            self.cache.delete(new_cache_key)
            logger.debug(f"Invalidated cache (new): {new_cache_key}")
        
        # Invalidate children cache if this FAQ is a parent
        children_cache_key = self._generate_children_cache_key(faq.chatbot_id, faq.id)
        self.cache.delete(children_cache_key)
        
        logger.info(f"Updated FAQ: id={faq_id}")
        
        return faq
    
    def delete_faq(
        self,
        faq_id: int,
        db: Session
    ) -> bool:
        """
        Delete FAQ and invalidate cache.
        
        Args:
            faq_id: FAQ ID to delete
            db: Database session
            
        Returns:
            True if deleted, False if not found
        """
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        
        if not faq:
            return False
        
        # Store data for cache invalidation before deletion
        question = faq.question
        chatbot_id = faq.chatbot_id
        parent_id = faq.parent_id
        
        # Delete from database (CASCADE will delete children)
        db.delete(faq)
        db.commit()
        
        # Invalidate cache
        cache_key = self._generate_cache_key(chatbot_id, question)
        self.cache.delete(cache_key)
        logger.debug(f"Invalidated cache: {cache_key}")
        
        # Invalidate children cache
        children_cache_key = self._generate_children_cache_key(chatbot_id, faq_id)
        self.cache.delete(children_cache_key)
        
        # If this FAQ had a parent, invalidate parent's children cache
        if parent_id:
            parent_children_key = self._generate_children_cache_key(chatbot_id, parent_id)
            self.cache.delete(parent_children_key)
            logger.debug(f"Invalidated parent's children cache: {parent_children_key}")
        
        logger.info(f"Deleted FAQ: id={faq_id}")
        
        return True
    
    def get_all_faqs(
        self,
        chatbot_id: int,
        db: Session,
        active_only: bool = True,
        parent_only: bool = False
    ) -> List[FAQ]:
        """
        Get all FAQs for a chatbot.
        
        Args:
            chatbot_id: Chatbot ID
            db: Database session
            active_only: Only return active FAQs
            parent_only: Only return parent FAQs (no parent_id)
            
        Returns:
            List of FAQ objects
        """
        query = db.query(FAQ).filter(FAQ.chatbot_id == chatbot_id)
        
        if active_only:
            query = query.filter(FAQ.is_active == True)
        
        if parent_only:
            query = query.filter(FAQ.parent_id == None)
        
        faqs = query.order_by(FAQ.display_order, FAQ.created_at).all()
        
        logger.debug(f"Retrieved {len(faqs)} FAQs for chatbot_id={chatbot_id}")
        
        return faqs
    
    def get_faq_by_id(self, faq_id: int, db: Session) -> Optional[FAQ]:
        """
        Get FAQ by ID (no caching for admin operations).
        
        Args:
            faq_id: FAQ ID
            db: Database session
            
        Returns:
            FAQ object or None
        """
        return db.query(FAQ).filter(FAQ.id == faq_id).first()
