"""
WebSocket Router

Provides a WebSocket endpoint that streams chat responses to the frontend.

Endpoint:
    WS /ws/chat/{session_id}

Flow:
    1. Client opens WebSocket connection
    2. Server subscribes to Redis Pub/Sub channel: chat_response:{session_id}
    3. Server waits (non-blocking via asyncio.to_thread) for the ChatWorker
       to publish the response
    4. Server sends the response JSON to the client
    5. Connection closes after the response is delivered (is_done=True)
       or after a timeout

No token auth — consistent with /chat/message/queue which also has no auth.
The session_id scopes the subscription naturally.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.redis_pubsub_service import get_redis_pubsub_service
from app.config import WEBSOCKET_RESPONSE_TIMEOUT

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/chat/{session_id}/{job_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: int,
    job_id: str,
):
    """
    WebSocket endpoint for streaming chat responses.

    The frontend:
        1. POSTs to /chat/message/queue  (enqueues job, gets session_id back)
        2. Opens  WS  /ws/chat/{session_id}
        3. Waits for the JSON message payload
        4. Closes connection

    Server-side:
        1. Accepts the WebSocket connection
        2. Subscribes to Redis channel  chat_response:{session_id}
        3. Waits for the ChatWorker to publish a result (up to 120 s)
        4. Sends result as JSON text frame
        5. Closes connection

    Note: No token auth here — consistent with /chat/message/queue REST endpoint
    which also requires no auth. The session_id scopes the subscription.

    Args:
        websocket:  FastAPI WebSocket instance.
        session_id: Chat session ID (embedded in URL path).
    """
    # ── Step 1: Accept connection ─────────────────────────────────────────────
    await websocket.accept()
    logger.info(f"WebSocket connected: session_id={session_id}")

    pubsub_service = get_redis_pubsub_service()

    try:
        if not pubsub_service.is_available():
            logger.error("Redis Pub/Sub unavailable — cannot serve WebSocket.")
            await websocket.send_json({
                "session_id": session_id,
                "response": "Streaming service is temporarily unavailable.",
                "next_options": [],
                "status": "error",
                "is_done": True,
            })
            return

        # ── Step 2: Collect full response for this job ────────────────────────
        # collect_job_response handles both publisher formats transparently:
        #   - Internal chat_worker: single JSON on rag_stream:{job_id}
        #   - Docker chatbot-worker: token stream on rag_stream:{job_id}
        #     with full buffer replay from rag_buffer:{job_id}
        # Also handles the race condition (worker faster than WS subscribe).
        result = await asyncio.to_thread(
            pubsub_service.collect_job_response,
            job_id,
            WEBSOCKET_RESPONSE_TIMEOUT,
        )

        # ── Step 3: Send response to frontend ────────────────────────────────
        if result is None:
            logger.warning(
                f"WebSocket timeout for session_id={session_id} "
                f"after {WEBSOCKET_RESPONSE_TIMEOUT}s"
            )
            await websocket.send_json({
                "session_id": session_id,
                "response": "Request timed out. Please try again.",
                "next_options": [],
                "status": "error",
                "is_done": True,
            })
        else:
            logger.info(
                f"WebSocket delivering response: session_id={session_id} "
                f"status={result.get('status')}"
            )
            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client: session_id={session_id}")

    except Exception as e:
        logger.error(
            f"WebSocket error for session_id={session_id}: {e}", exc_info=True
        )
        try:
            await websocket.send_json({
                "session_id": session_id,
                "response": "An unexpected error occurred.",
                "next_options": [],
                "status": "error",
                "is_done": True,
            })
        except Exception:
            pass  # Connection may already be closed

    finally:
        # ── Cleanup ───────────────────────────────────────────────────────────
        # collect_job_response manages its own pub/sub subscription internally;
        # nothing to clean up here except the WebSocket connection itself.
        try:
            await websocket.close()
        except Exception:
            pass  # Already closed

        logger.info(f"WebSocket closed: session_id={session_id}")
