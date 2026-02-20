"""
Cache Dependencies

Provides dependency injection for cache-related services.
"""

from typing import Generator
from app.services.redis_cache_service import RedisCacheService, get_redis_cache_service
from app.services.faq_service import FAQService


def get_cache_service() -> RedisCacheService:
    """
    Dependency for Redis cache service (singleton).
    
    Returns:
        RedisCacheService instance
    """
    return get_redis_cache_service()


def get_faq_service() -> Generator[FAQService, None, None]:
    """
    Dependency for FAQ service with cache support.
    
    Yields:
        FAQService instance
    """
    cache_service = get_redis_cache_service()
    yield FAQService(cache_service)
