"""
RabbitMQ Service

Provides a class-based, reusable message queue layer using RabbitMQ via pika.
Handles connection management, publishing, and consuming messages.
"""

import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

import pika
import pika.exceptions

from app.config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASS,
    RABBITMQ_QUEUE_NAME,
    RABBITMQ_EXCHANGE,
    RABBITMQ_HEARTBEAT,
    RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,
)

logger = logging.getLogger(__name__)


class RabbitMQService:
    """
    Class-based RabbitMQ service for publishing and consuming messages.

    Features:
    - Connection and channel management
    - Graceful degradation when RabbitMQ is unavailable
    - JSON serialization/deserialization
    - Durable queue declaration (survives broker restart)
    - Thread-safe publish via lock
    - Health check capability
    """

    def __init__(self):
        """Initialize RabbitMQ service (does not connect immediately)."""
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._lock = threading.Lock()
        self._connected = False

    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Establish connection to RabbitMQ broker and declare the default queue.

        Returns:
            True if connection succeeded, False otherwise.
        """
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=RABBITMQ_HEARTBEAT,
                blocked_connection_timeout=RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,
            )

            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            # Process any pending events so the connection is fully ready
            self._connection.process_data_events()

            # Use passive=True to connect to the existing queue without
            # modifying its parameters (avoids PRECONDITION_FAILED if the
            # queue was created with extra arguments like x-message-ttl).
            # Falls back to creating it fresh if it doesn't exist yet.
            try:
                self._channel.queue_declare(
                    queue=RABBITMQ_QUEUE_NAME,
                    passive=True,
                )
                logger.debug(f"RabbitMQ queue '{RABBITMQ_QUEUE_NAME}' found (passive check).")
            except pika.exceptions.ChannelClosedByBroker:
                # Queue doesn't exist — create a fresh channel and declare it
                self._channel = self._connection.channel()
                self._channel.queue_declare(
                    queue=RABBITMQ_QUEUE_NAME,
                    durable=True,
                )
                logger.debug(f"RabbitMQ queue '{RABBITMQ_QUEUE_NAME}' created.")

            self._connected = True
            logger.info(
                f"✅ RabbitMQ connected: {RABBITMQ_HOST}:{RABBITMQ_PORT} "
                f"(queue: {RABBITMQ_QUEUE_NAME})"
            )
            return True

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self._connected = False
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to RabbitMQ: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """
        Gracefully close the RabbitMQ channel and connection.
        """
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
                logger.debug("RabbitMQ channel closed.")

            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.info("🔌 RabbitMQ connection closed.")

        except Exception as e:
            logger.warning(f"Error during RabbitMQ disconnect: {e}")

        finally:
            self._channel = None
            self._connection = None
            self._connected = False

    def is_available(self) -> bool:
        """
        Check if the RabbitMQ connection is alive.

        Returns:
            True if connected and channel is open, False otherwise.
        """
        return (
            self._connected
            and self._connection is not None
            and self._connection.is_open
            and self._channel is not None
            and self._channel.is_open
        )

    def health_check(self) -> bool:
        """
        Perform a lightweight health check on the RabbitMQ connection.

        Returns:
            True if connection is alive, False otherwise.
        """
        if not self.is_available():
            return False

        try:
            # Process any pending I/O events (keeps heartbeat alive)
            self._connection.process_data_events()
            return True
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False

    # -------------------------------------------------------------------------
    # Publishing
    # -------------------------------------------------------------------------

    def publish_message(
        self,
        message: Dict[str, Any],
        queue_name: Optional[str] = None,
        priority: int = 0,
    ) -> bool:
        """
        Publish a JSON-serializable message to a RabbitMQ queue.

        Args:
            message:    Dictionary payload to publish.
            queue_name: Target queue name. Defaults to RABBITMQ_QUEUE_NAME.
            priority:   Message priority (0-9). Default is 0.

        Returns:
            True if published successfully, False otherwise.
        """
        target_queue = queue_name or RABBITMQ_QUEUE_NAME

        if not self.is_available():
            logger.warning(
                "RabbitMQ not available. Attempting to reconnect before publish..."
            )
            if not self.connect():
                logger.error("❌ Reconnect failed. Message not published.")
                return False

        try:
            with self._lock:
                body = json.dumps(message)
                self._channel.basic_publish(
                    exchange=RABBITMQ_EXCHANGE,
                    routing_key=target_queue,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent message (survives broker restart)
                        content_type="application/json",
                        priority=priority,
                    ),
                )

            logger.debug(f"📤 Published message to '{target_queue}': {message}")
            return True

        except pika.exceptions.AMQPError as e:
            logger.warning(
                f"⚠️  Publish failed (stale connection): {e}. Reconnecting and retrying once..."
            )
            self._connected = False
            # Reconnect and retry once — handles the case where is_available()
            # returned True but the underlying socket was already dead.
            if not self.connect():
                logger.error(f"❌ Reconnect failed. Message not published to '{target_queue}'.")
                return False
            try:
                with self._lock:
                    body = json.dumps(message)
                    self._channel.basic_publish(
                        exchange=RABBITMQ_EXCHANGE,
                        routing_key=target_queue,
                        body=body,
                        properties=pika.BasicProperties(
                            delivery_mode=2,
                            content_type="application/json",
                            priority=priority,
                        ),
                    )
                logger.info(f"📤 Retry publish succeeded to '{target_queue}'.")
                return True
            except Exception as retry_err:
                logger.error(f"❌ Retry publish also failed: {retry_err}")
                self._connected = False
                return False

        except Exception as e:
            logger.error(f"❌ Unexpected error publishing message: {e}")
            return False

    # -------------------------------------------------------------------------
    # Consuming
    # -------------------------------------------------------------------------

    def consume_messages(
        self,
        callback: Callable[[Dict[str, Any]], None],
        queue_name: Optional[str] = None,
        prefetch_count: int = 1,
    ) -> None:
        """
        Start consuming messages from a queue (blocking call).

        The callback receives the deserialized message dictionary.
        After the callback returns successfully, the message is acknowledged.
        On any exception in callback, the message is rejected (nacked) and requeued.

        Args:
            callback:       Function to call with each deserialized message.
            queue_name:     Queue to consume from. Defaults to RABBITMQ_QUEUE_NAME.
            prefetch_count: Max unacknowledged messages per consumer (rate limiting).
        """
        target_queue = queue_name or RABBITMQ_QUEUE_NAME

        if not self.is_available():
            if not self.connect():
                logger.error(
                    "❌ Cannot start consumer: RabbitMQ connection unavailable."
                )
                return

        try:
            # Limit worker to process one message at a time (rate limiting)
            self._channel.basic_qos(prefetch_count=prefetch_count)

            def _on_message(ch, method, properties, body):
                """Internal wrapper: deserialize and call user callback."""
                try:
                    message = json.loads(body)
                    logger.debug(
                        f"📥 Received message from '{target_queue}': {message}"
                    )
                    callback(message)
                    # Acknowledge after successful processing
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to decode message body: {e}")
                    # Reject malformed messages (do not requeue)
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag, requeue=False
                    )

                except Exception as e:
                    logger.error(f"❌ Error in message callback: {e}")
                    # Requeue on processing error for retry
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag, requeue=True
                    )

            self._channel.basic_consume(
                queue=target_queue,
                on_message_callback=_on_message,
            )

            logger.info(
                f"🐇 RabbitMQ consumer started on queue '{target_queue}'. "
                "Waiting for messages..."
            )
            self._channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Consumer stopped by KeyboardInterrupt.")
            self._channel.stop_consuming()

        except pika.exceptions.AMQPError as e:
            logger.error(f"❌ AMQP error during consume: {e}")
            self._connected = False

        except Exception as e:
            logger.error(f"❌ Unexpected error during consume: {e}")
            self._connected = False

    def stop_consuming(self) -> None:
        """
        Stop an active consumer loop gracefully.
        """
        if self._channel and self._channel.is_open:
            try:
                self._channel.stop_consuming()
                logger.info("🛑 RabbitMQ consumer stopped.")
            except Exception as e:
                logger.warning(f"Error stopping consumer: {e}")


# ---------------------------------------------------------------------------
# Module-level singleton instance
# ---------------------------------------------------------------------------

rabbitmq_service = RabbitMQService()
