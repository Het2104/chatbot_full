"""
Redis Pub/Sub Service

Provides a class-based publish/subscribe layer using Redis.
Used to bridge the ChatWorker responses to WebSocket clients.

Publish side  (ChatWorker):
    worker finishes job → publish(channel, payload)

Subscribe side (WebSocket endpoint):
    client connects → subscribe(channel) → listen_once() → send to client

Channel naming convention:
    chat_response:{session_id}   e.g.  chat_response:42
"""

import json
import logging
from typing import Any, Dict, Optional

import redis
from redis.client import PubSub
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from app.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_SSL,
    REDIS_SOCKET_TIMEOUT,
    REDIS_SOCKET_CONNECT_TIMEOUT,
    REDIS_PUBSUB_CHANNEL_PREFIX,
)

logger = logging.getLogger(__name__)


class RedisPubSubService:
    """
    Redis Pub/Sub service for real-time message broadcasting.

    Features:
    - Separate publish client (connection-pooled, reused across requests)
    - Per-subscription PubSub objects (one per WebSocket connection)
    - JSON serialization / deserialization
    - Graceful degradation when Redis is unavailable
    - Health check capability
    - Timeout-aware blocking listen (compatible with asyncio.to_thread)
    """

    def __init__(self):
        """Initialize Redis publish client with connection pooling."""
        self._publish_client: Optional[redis.Redis] = None
        self._available = False

        try:
            pool_config = {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "socket_timeout": REDIS_SOCKET_TIMEOUT,
                "socket_connect_timeout": REDIS_SOCKET_CONNECT_TIMEOUT,
                "decode_responses": True,
                "max_connections": 50,
            }

            if REDIS_PASSWORD:
                pool_config["password"] = REDIS_PASSWORD

            if REDIS_SSL:
                pool_config["ssl"] = True
                pool_config["ssl_cert_reqs"] = None

            pool = redis.ConnectionPool(**pool_config)
            self._publish_client = redis.Redis(connection_pool=pool)

            # Verify connection
            self._publish_client.ping()
            self._available = True
            logger.info(
                f"✅ Redis Pub/Sub service connected: {REDIS_HOST}:{REDIS_PORT} "
                f"(DB: {REDIS_DB})"
            )

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Redis Pub/Sub failed to connect: {e}")
            logger.warning("Pub/Sub will operate in fallback mode (disabled)")
            self._publish_client = None
            self._available = False

        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Redis Pub/Sub: {e}")
            self._publish_client = None
            self._available = False

    # -------------------------------------------------------------------------
    # Health / Availability
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """
        Check if the Redis Pub/Sub service is connected.

        Returns:
            True if the publish client is ready, False otherwise.
        """
        return self._available and self._publish_client is not None

    def health_check(self) -> bool:
        """
        Lightweight health check via PING.

        Returns:
            True if Redis responds, False otherwise.
        """
        if not self.is_available():
            return False

        try:
            return bool(self._publish_client.ping())
        except RedisError as e:
            logger.error(f"Redis Pub/Sub health check failed: {e}")
            return False

    # -------------------------------------------------------------------------
    # Channel Naming
    # -------------------------------------------------------------------------

    def get_channel_name(self, session_id: int) -> str:
        """
        Build the Redis channel name for a chat session.

        Args:
            session_id: Chat session ID.

        Returns:
            Channel string e.g. 'chat_response:42'
        """
        return f"{REDIS_PUBSUB_CHANNEL_PREFIX}:{session_id}"

    # -------------------------------------------------------------------------
    # Publish
    # -------------------------------------------------------------------------

    def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publish a JSON-serializable message to a Redis channel.

        Args:
            channel: Redis channel name.
            message: Dictionary payload to publish.

        Returns:
            True if at least one subscriber received it (or message sent),
            False if Redis is unavailable or an error occurred.
        """
        if not self.is_available():
            logger.warning(
                f"Redis Pub/Sub unavailable. Cannot publish to channel '{channel}'."
            )
            return False

        try:
            body = json.dumps(message)
            receivers = self._publish_client.publish(channel, body)
            logger.debug(
                f"📢 Published to '{channel}' → {receivers} receiver(s): "
                f"status={message.get('status')}"
            )
            return True

        except RedisError as e:
            logger.error(f"❌ Redis publish error on channel '{channel}': {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected publish error on channel '{channel}': {e}")
            return False

    def publish_to_session(self, session_id: int, message: Dict[str, Any]) -> bool:
        """
        Convenience method: publish directly using session_id.

        Builds the channel name automatically and publishes via Pub/Sub only.
        No result is stored in Redis — Pub/Sub is the sole delivery path.

        Args:
            session_id: Chat session ID.
            message:    Dictionary payload.

        Returns:
            True if published successfully, False otherwise.
        """
        channel = self.get_channel_name(session_id)
        return self.publish(channel, message)

    def collect_job_response(
        self,
        job_id: str,
        timeout: float = 60.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Collect the full response for a RAG job from Redis.

        Handles two publisher formats:

        1. Internal ChatWorker (chat_worker.py):
           Publishes a single complete JSON dict to ``rag_stream:{job_id}``:
           {"response": str, "status": "success"|"error", "is_done": True, ...}

        2. Docker chatbot-worker (rag_worker.py):
           Streams individual tokens then sends a completion signal:
           - ``rag_buffer:{job_id}`` Redis List: all messages buffered.
           - ``rag_stream:{job_id}`` Pub/Sub: live token stream.
           Message format: {"type": "token"|"complete"|"error", "content": str}

        Strategy:
           a) Check ``rag_buffer:{job_id}`` Redis List (Docker worker buffer/replay).
           b) Subscribe to ``rag_stream:{job_id}`` and collect live messages.

        Args:
            job_id:  UUID string for the job.
            timeout: Max seconds to wait for a response.

        Returns:
            Normalized dict {"response": str, "status": str, "is_done": True, ...}
            or None on timeout / Redis unavailable.
        """
        import time

        channel = f"rag_stream:{job_id}"
        buffer_key = f"rag_buffer:{job_id}"

        if not self.is_available():
            return None

        # ── (b) Docker worker: replay from Redis List buffer ──────────────────
        try:
            buffered = self._publish_client.lrange(buffer_key, 0, -1)
            if buffered:
                tokens = []
                for raw in buffered:
                    try:
                        msg = json.loads(raw)
                        if msg.get("type") == "token":
                            tokens.append(msg.get("content", ""))
                        elif msg.get("type") == "complete":
                            # All tokens already in buffer — job finished
                            full_response = "".join(tokens)
                            logger.debug(
                                f"collect_job_response: assembled {len(tokens)} buffered "
                                f"tokens for job_id={job_id}"
                            )
                            return {
                                "response": full_response,
                                "next_options": [],
                                "status": "success",
                                "is_done": True,
                            }
                        elif msg.get("type") == "error":
                            return {
                                "response": msg.get("content", "An error occurred."),
                                "next_options": [],
                                "status": "error",
                                "is_done": True,
                            }
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"collect_job_response: buffer read error for job_id={job_id}: {e}")

        # ── (c) Subscribe to live Pub/Sub channel and collect ─────────────────
        pubsub_conn = self.subscribe(channel)
        if pubsub_conn is None:
            return None

        tokens = []
        deadline = time.monotonic() + timeout

        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.warning(f"collect_job_response: timeout for job_id={job_id}")
                    return None

                msg_raw = pubsub_conn.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(1.0, remaining),
                )
                if msg_raw is None:
                    continue
                if msg_raw.get("type") != "message":
                    continue

                data_str = msg_raw.get("data", "")
                if not data_str:
                    continue

                try:
                    msg = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                if msg_type == "token":
                    # Docker worker: accumulate streaming tokens
                    tokens.append(msg.get("content", ""))

                elif msg_type == "complete":
                    # Docker worker: all tokens received
                    full_response = "".join(tokens)
                    logger.debug(
                        f"collect_job_response: assembled {len(tokens)} live tokens "
                        f"for job_id={job_id}"
                    )
                    return {
                        "response": full_response,
                        "next_options": [],
                        "status": "success",
                        "is_done": True,
                    }

                elif msg_type == "error":
                    # Docker worker: error signal
                    return {
                        "response": msg.get("content", "An error occurred."),
                        "next_options": [],
                        "status": "error",
                        "is_done": True,
                    }

                elif msg.get("is_done") is True or msg.get("status") in ("success", "error"):
                    # Internal ChatWorker: single complete message
                    return {
                        "response": msg.get("response") or msg.get("content", ""),
                        "next_options": msg.get("next_options", []),
                        "status": msg.get("status", "success"),
                        "is_done": True,
                    }

        except Exception as e:
            logger.error(f"collect_job_response: listen error for job_id={job_id}: {e}")
            return None

        finally:
            self.unsubscribe(pubsub_conn, channel)

    # -------------------------------------------------------------------------
    # Subscribe
    # -------------------------------------------------------------------------

    def subscribe(self, channel: str) -> Optional[PubSub]:
        """
        Create a PubSub subscription to a Redis channel.

        Each WebSocket connection should call this to get its own PubSub object.
        Remember to call unsubscribe() when the connection closes.

        Args:
            channel: Redis channel name to subscribe to.

        Returns:
            PubSub object ready to listen, or None if Redis unavailable.
        """
        if not self.is_available():
            logger.warning(
                f"Redis Pub/Sub unavailable. Cannot subscribe to '{channel}'."
            )
            return None

        try:
            # Each subscriber gets its own connection (not pooled for pub/sub)
            sub_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD or None,
                decode_responses=True,
                socket_timeout=None,       # Blocking — needed for listen()
                socket_connect_timeout=5,
            )

            pubsub = sub_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel)

            logger.debug(f"📡 Subscribed to Redis channel: '{channel}'")
            return pubsub

        except RedisError as e:
            logger.error(f"❌ Redis subscribe error on channel '{channel}': {e}")
            return None

        except Exception as e:
            logger.error(
                f"❌ Unexpected error subscribing to channel '{channel}': {e}"
            )
            return None

    def unsubscribe(self, pubsub: PubSub, channel: str) -> None:
        """
        Unsubscribe and close a PubSub object.

        Should be called when a WebSocket connection closes.

        Args:
            pubsub:  PubSub object returned by subscribe().
            channel: Channel name to unsubscribe from.
        """
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
            logger.debug(f"🔕 Unsubscribed from Redis channel: '{channel}'")
        except Exception as e:
            logger.warning(f"Error unsubscribing from '{channel}': {e}")

    # -------------------------------------------------------------------------
    # Listen (blocking — run via asyncio.to_thread in WebSocket handler)
    # -------------------------------------------------------------------------

    def listen_once(
        self,
        pubsub: PubSub,
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Block and wait for exactly ONE real message on a subscribed PubSub object.

        Intended to be called via asyncio.to_thread() inside the WebSocket
        endpoint so it does not block the event loop.

        Uses a polling loop so that subscribe-confirmation messages (which
        arrive immediately on the socket before any real message) are drained
        and the function keeps waiting until the actual payload arrives or the
        timeout is reached.

        Args:
            pubsub:  PubSub object (from subscribe()).
            timeout: Max seconds to wait. Returns None on timeout.

        Returns:
            Deserialized message dict, or None on timeout / error.
        """
        import time

        deadline = time.monotonic() + timeout

        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    logger.debug("Pub/Sub listen_once: timed out — no message received.")
                    return None

                # Poll with a short window so we can re-check the deadline.
                # Using min(1.0, remaining) keeps the loop responsive without
                # spinning the CPU at 100%.
                message = pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(1.0, remaining),
                )

                if message is None:
                    # No message in this 1-second window — keep waiting
                    continue

                if message.get("type") != "message":
                    # Subscribe / unsubscribe confirmation — skip and keep waiting
                    continue

                data = message.get("data")
                if not data:
                    continue

                # ── Deserialize JSON payload ──────────────────────────────────
                try:
                    return json.loads(data)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to decode Pub/Sub message: {e}")
                    return None

        except RedisError as e:
            logger.error(f"❌ Redis listen error: {e}")
            return None

        except Exception as e:
            logger.error(f"❌ Unexpected listen error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the publish client connection pool."""
        if self._publish_client:
            try:
                self._publish_client.close()
                logger.info("Redis Pub/Sub publish client closed.")
            except Exception as e:
                logger.warning(f"Error closing Redis Pub/Sub client: {e}")


# ---------------------------------------------------------------------------
# Module-level singleton instance
# ---------------------------------------------------------------------------

_redis_pubsub_service: Optional[RedisPubSubService] = None


def get_redis_pubsub_service() -> RedisPubSubService:
    """
    Get or create singleton RedisPubSubService instance.

    Returns:
        Singleton RedisPubSubService instance.
    """
    global _redis_pubsub_service

    if _redis_pubsub_service is None:
        _redis_pubsub_service = RedisPubSubService()

    return _redis_pubsub_service
