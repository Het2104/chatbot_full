"""
Redis Cache Service

Provides a class-based, reusable caching layer using Redis.
Handles connection pooling, error handling, and graceful fallback.
"""

import json
import logging
from typing import Any, Optional
import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from app.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_SSL,
    REDIS_SOCKET_TIMEOUT,
    REDIS_SOCKET_CONNECT_TIMEOUT,
    CACHE_ENABLED,
)

logger = logging.getLogger(__name__)


class RedisCacheService:
    """
    Generic Redis caching service with connection pooling and error handling.
    
    Features:
    - Connection pooling for performance
    - Graceful degradation when Redis is unavailable
    - JSON serialization/deserialization
    - TTL (Time-To-Live) support
    - Health check capabilities
    """
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self._client: Optional[redis.Redis] = None
        self._enabled = CACHE_ENABLED
        
        if not self._enabled:
            logger.warning("Redis cache is disabled via CACHE_ENABLED config")
            return
        
        try:
            # Create connection pool configuration
            pool_config = {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "socket_timeout": REDIS_SOCKET_TIMEOUT,
                "socket_connect_timeout": REDIS_SOCKET_CONNECT_TIMEOUT,
                "decode_responses": True,  # Auto-decode bytes to str
                "max_connections": 50,
            }
            
            # Add password only if provided
            if REDIS_PASSWORD:
                pool_config["password"] = REDIS_PASSWORD
            
            # Add SSL configuration only if enabled
            if REDIS_SSL:
                pool_config["ssl"] = True
                pool_config["ssl_cert_reqs"] = None  # For self-signed certs
            
            pool = redis.ConnectionPool(**pool_config)
            self._client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self._client.ping()
            logger.info(
                f"✅ Redis cache connected: {REDIS_HOST}:{REDIS_PORT} (DB: {REDIS_DB})"
            )
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            logger.warning("Cache will operate in fallback mode (disabled)")
            self._client = None
            self._enabled = False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Redis: {e}")
            self._client = None
            self._enabled = False
    
    def is_available(self) -> bool:
        """
        Check if Redis cache is available.
        
        Returns:
            True if cache is enabled and connected, False otherwise
        """
        return self._enabled and self._client is not None
    
    def health_check(self) -> bool:
        """
        Perform health check on Redis connection.
        
        Returns:
            True if Redis responds to PING, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return self._client.ping()
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value (deserialized from JSON) or None if not found/error
        """
        if not self.is_available():
            return None
        
        try:
            value = self._client.get(key)
            
            if value is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            logger.debug(f"Cache HIT: {key}")
            
            # Deserialize JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Return as-is if not JSON
                return value
                
        except RedisError as e:
            logger.warning(f"Redis GET error for key '{key}': {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (None = no expiration)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Serialize to JSON
            if not isinstance(value, str):
                value = json.dumps(value)
            
            if ttl:
                self._client.setex(key, ttl, value)
            else:
                self._client.set(key, value)
            
            logger.debug(f"Cache SET: {key} (TTL: {ttl or 'none'})")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Redis SET error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist or error
        """
        if not self.is_available():
            return False
        
        try:
            result = self._client.delete(key)
            
            if result > 0:
                logger.debug(f"Cache DELETE: {key}")
                return True
            else:
                logger.debug(f"Cache DELETE (not found): {key}")
                return False
                
        except RedisError as e:
            logger.warning(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "faq:chatbot:1:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self._client.keys(pattern)
            
            if not keys:
                return 0
            
            deleted = self._client.delete(*keys)
            logger.debug(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
            return deleted
            
        except RedisError as e:
            logger.warning(f"Redis DELETE PATTERN error for '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return self._client.exists(key) > 0
        except RedisError as e:
            logger.warning(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, -1 if no expiration, -2 if key doesn't exist, None on error
        """
        if not self.is_available():
            return None
        
        try:
            return self._client.ttl(key)
        except RedisError as e:
            logger.warning(f"Redis TTL error for key '{key}': {e}")
            return None
    
    def close(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            try:
                self._client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Singleton instance (initialized in dependencies)
_redis_cache_service: Optional[RedisCacheService] = None


def get_redis_cache_service() -> RedisCacheService:
    """
    Get or create singleton RedisCacheService instance.
    
    Returns:
        Singleton RedisCacheService instance
    """
    global _redis_cache_service
    
    if _redis_cache_service is None:
        _redis_cache_service = RedisCacheService()
    
    return _redis_cache_service
