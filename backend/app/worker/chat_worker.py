"""
Chat Worker Service

Class-based worker that consumes chat jobs from RabbitMQ,
processes them through the RAG pipeline only,
and publishes the result to a Redis Pub/Sub channel.

Flow:
    RabbitMQ queue (rag_processing_queue)
        → ChatWorker._process_job()
            → RAG pipeline → Default fallback
              (Workflow + FAQ already checked in POST /chat/message/queue)
        → Redis Pub/Sub channel (chat_response:{session_id})
            → WebSocket endpoint picks up and delivers to frontend

Job Message Schema (consumed from RabbitMQ):
    {
        "job_id":      str,   # Unique job identifier (UUID)
        "session_id":  int,   # Existing ChatSession ID
        "chatbot_id":  int,   # Chatbot ID (for context)
        "user_message": str   # User's message text
    }

Response Message Schema (published to Redis Pub/Sub):
    {
        "job_id":       str,
        "session_id":   int,
        "response":     str,
        "next_options": list,
        "status":       "success" | "error",
        "is_done":      bool
    }
"""

import logging
import threading
from typing import Any, Dict, Optional

from app.config import WORKER_PREFETCH_COUNT
from app.services.rabbitmq_service import RabbitMQService
from app.services.redis_pubsub_service import RedisPubSubService, get_redis_pubsub_service
from database import SessionLocal

logger = logging.getLogger(__name__)


class ChatWorker:
    """
    Class-based worker that bridges RabbitMQ → Chat Pipeline → Redis Pub/Sub.

    Features:
    - Consumes jobs from a RabbitMQ queue
    - Reuses the existing chat waterfall (Workflow → FAQ cache → RAG → Default)
    - Publishes complete responses to Redis Pub/Sub for WebSocket delivery
    - Graceful error handling: on failure publishes an error payload so the
      WebSocket client is always notified instead of hanging
    - Thread-safe: can be started in a background thread
    """

    def __init__(
        self,
        rabbitmq_service: Optional[RabbitMQService] = None,
        pubsub_service: Optional[RedisPubSubService] = None,
    ):
        """
        Initialize ChatWorker.

        Args:
            rabbitmq_service: Shared RabbitMQService instance.
                              If None, a new one is created internally.
            pubsub_service:   Shared RedisPubSubService instance.
                              If None, the singleton is used.
        """
        # RabbitMQ
        self._rabbitmq = rabbitmq_service or RabbitMQService()

        # Redis Pub/Sub — reuse service singleton so all components share one pool
        self._pubsub: RedisPubSubService = pubsub_service or get_redis_pubsub_service()

        # Worker state
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # -------------------------------------------------------------------------
    # Database Session Helper
    # -------------------------------------------------------------------------

    def _get_db_session(self):
        """
        Create and return a new SQLAlchemy database session.
        Caller is responsible for closing it.
        """
        return SessionLocal()

    # -------------------------------------------------------------------------
    # Redis Pub/Sub Publishing
    # -------------------------------------------------------------------------

    def _publish_response(self, job_id: str, session_id: int, payload: Dict[str, Any]) -> bool:
        """
        Publish a response payload to the Redis Pub/Sub channel via RedisPubSubService.

        Publishes to rag_stream:{job_id} — matches the channel that both the
        Docker chatbot-worker and this internal worker use, and that the
        WebSocket endpoint subscribes to.

        Args:
            job_id:     Job UUID (used as channel key)
            session_id: Chat session ID
            payload:    Dict to serialize and publish

        Returns:
            True if published, False if Redis unavailable
        """
        channel = f"rag_stream:{job_id}"
        published = self._pubsub.publish(channel, payload)
        return published

    # -------------------------------------------------------------------------
    # Job Processing
    # -------------------------------------------------------------------------

    def _process_job(self, message: Dict[str, Any]) -> None:
        """
        Process a single chat job consumed from RabbitMQ.

        Runs the full chat waterfall:
            Workflow → FAQ (with Redis cache) → RAG → Default fallback

        Always publishes a result (success or error) to Redis Pub/Sub so
        the WebSocket endpoint can relay it to the frontend.

        Args:
            message: Deserialized job dict from RabbitMQ queue.
        """
        # ── Validate required fields ──────────────────────────────────────────
        job_id = message.get("job_id", "unknown")
        session_id = message.get("session_id")
        user_message = message.get("user_message", "")

        logger.info(
            f"⚙️  Processing job_id={job_id} session_id={session_id} "
            f"message='{user_message[:60]}...'"
        )

        if not session_id or not user_message:
            logger.error(
                f"❌ Invalid job payload — missing session_id or user_message: {message}"
            )
            if session_id:
                self._publish_response(
                    job_id,
                    session_id,
                    {
                        "job_id": job_id,
                        "session_id": session_id,
                        "response": "Invalid job payload received.",
                        "next_options": [],
                        "status": "error",
                        "is_done": True,
                    },
                )
            return

        db = None
        try:
            # ── Open DB session ───────────────────────────────────────────────
            db = self._get_db_session()

            # ── Run RAG-only pipeline ───────────────────────────────────────────
            # Workflow and FAQ were already checked in the queue endpoint.
            # Worker only handles the RAG path + default fallback.
            # It also saves both messages to the database.
            from app.services.chat_service import process_rag_message

            bot_response, next_options, _session = process_rag_message(
                session_id=session_id,
                user_message=user_message,
                db=db,
            )

            # ── Publish success response to Redis Pub/Sub ─────────────────────
            self._publish_response(
                job_id,
                session_id,
                {
                    "job_id": job_id,
                    "session_id": session_id,
                    "response": bot_response,
                    "next_options": next_options,
                    "status": "success",
                    "is_done": True,
                },
            )

            logger.info(
                f"✅ Job {job_id} completed. "
                f"Response length={len(bot_response)} opts={len(next_options)}"
            )

        except ValueError as e:
            # Expected errors (e.g. session not found)
            logger.warning(f"⚠️  Job {job_id} — ValueError: {e}")
            self._publish_response(
                job_id,
                session_id,
                {
                    "job_id": job_id,
                    "session_id": session_id,
                    "response": str(e),
                    "next_options": [],
                    "status": "error",
                    "is_done": True,
                },
            )

        except Exception as e:
            # Unexpected errors
            logger.error(
                f"❌ Job {job_id} failed with unexpected error: {e}",
                exc_info=True,
            )
            self._publish_response(
                job_id,
                session_id,
                {
                    "job_id": job_id,
                    "session_id": session_id,
                    "response": "Something went wrong. Please try again.",
                    "next_options": [],
                    "status": "error",
                    "is_done": True,
                },
            )

        finally:
            if db:
                db.close()

    # -------------------------------------------------------------------------
    # Worker Lifecycle
    # -------------------------------------------------------------------------

    def start(self, run_in_thread: bool = False) -> None:
        """
        Start the worker consumer loop.

        Args:
            run_in_thread: If True, runs in a background daemon thread.
                           If False, blocks the calling thread (for standalone worker process).
        """
        if self._running:
            logger.warning("ChatWorker is already running.")
            return

        # NOTE: Do NOT connect here.
        # pika's BlockingConnection is NOT thread-safe and must be created
        # and used entirely within the same thread.
        # _run_consumer() handles the initial connection inside the worker thread.
        self._running = True
        logger.info(
            f"🚀 ChatWorker starting "
            f"(thread={run_in_thread}, prefetch={WORKER_PREFETCH_COUNT})"
        )

        if run_in_thread:
            self._thread = threading.Thread(
                target=self._run_consumer,
                name="ChatWorkerThread",
                daemon=True,  # Dies with the main process
            )
            self._thread.start()
            logger.info("ChatWorker background thread started.")
        else:
            # Blocking — meant for a standalone worker entry-point
            self._run_consumer()

    def _run_consumer(self) -> None:
        """Internal: start the blocking consumer loop with reconnect on failure."""
        import time

        RECONNECT_DELAY = 5  # seconds between reconnect attempts

        while self._running:
            try:
                # Ensure connected before starting consumer
                if not self._rabbitmq.is_available():
                    logger.info("RabbitMQ not connected — attempting reconnect...")
                    if not self._rabbitmq.connect():
                        logger.error(
                            f"❌ RabbitMQ reconnect failed. Retrying in {RECONNECT_DELAY}s..."
                        )
                        time.sleep(RECONNECT_DELAY)
                        continue

                self._rabbitmq.consume_messages(
                    callback=self._process_job,
                    prefetch_count=WORKER_PREFETCH_COUNT,
                )

                # consume_messages() returned — connection was lost or user stopped it
                if not self._running:
                    break  # Normal shutdown — exit cleanly

                logger.warning(
                    f"RabbitMQ consumer exited unexpectedly. "
                    f"Reconnecting in {RECONNECT_DELAY}s..."
                )
                time.sleep(RECONNECT_DELAY)

            except Exception as e:
                logger.error(
                    f"❌ ChatWorker consumer loop error: {e}", exc_info=True
                )
                if self._running:
                    logger.info(f"Retrying in {RECONNECT_DELAY}s...")
                    time.sleep(RECONNECT_DELAY)

        self._running = False
        logger.info("ChatWorker consumer loop exited.")

    def stop(self) -> None:
        """
        Stop the worker consumer loop gracefully.
        """
        if not self._running:
            return

        logger.info("🛑 Stopping ChatWorker...")
        self._rabbitmq.stop_consuming()
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            logger.info("ChatWorker thread joined.")

    def is_running(self) -> bool:
        """Return True if the worker consumer loop is active."""
        return self._running


# ---------------------------------------------------------------------------
# Module-level singleton (used when imported by main.py or other modules)
# ---------------------------------------------------------------------------

chat_worker = ChatWorker()


# ---------------------------------------------------------------------------
# Standalone entry point — used when running as a Docker container process
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import signal
    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        force=True,
    )

    logger.info("🐳 ChatWorker starting as standalone Docker process...")

    def _shutdown(signum, frame):
        logger.info("Shutdown signal received — stopping worker...")
        chat_worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Blocking — runs until the process is stopped
    chat_worker.start(run_in_thread=False)
