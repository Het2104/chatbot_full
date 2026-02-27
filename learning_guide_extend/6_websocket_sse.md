# 6. WebSocket and SSE — Deep Technical Learning

---

## 6.1 Concept Introduction

Traditional HTTP is **request-response**: the client sends a request, the server returns a response, and the connection closes. This model does not work for real-time communication where the server needs to push data to the client.

Two technologies solve this:

**WebSocket:**
- Full-duplex, persistent TCP connection
- Both client and server can send messages at any time
- Low overhead after initial handshake
- Standard: RFC 6455

**Server-Sent Events (SSE):**
- One-way: server pushes to client
- Uses normal HTTP connection (keep-alive)
- Auto-reconnect built into standard
- Simpler than WebSocket, text-only
- Standard: HTML5 EventSource API

---

## 6.2 WebSocket vs SSE — Deep Comparison

| Feature | WebSocket | SSE |
|---|---|---|
| **Direction** | Bidirectional | Server → Client only |
| **Protocol** | ws:// or wss:// | http:// or https:// |
| **Data format** | Text or binary | Text only (UTF-8) |
| **Reconnect** | Manual | Automatic (built-in) |
| **Load balancers** | Needs sticky sessions | Works with standard LBs |
| **Overhead** | Low (2-8 byte frames) | None extra (HTTP keep-alive) |
| **Browser support** | Universal | Universal except old IE |
| **Use case** | Chat, games, collaboration | Notifications, feeds, AI streaming |

**Your project uses WebSocket** for the `/ws/chat/{session_id}/{job_id}` endpoint.

**Why WebSocket over SSE for this chatbot?**
- Future bidirectional features (typing indicators, cancel request)
- Industry standard for chat applications
- Easy to implement with FastAPI's built-in WebSocket support

---

## 6.3 WebSocket Lifecycle — Complete

```
Phase 1: HTTP Upgrade Handshake
─────────────────────────────────
Client → Server:
  GET /ws/chat/42/job-uuid HTTP/1.1
  Host: localhost:8000
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
  Sec-WebSocket-Version: 13

Server → Client:
  HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=

Connection is now upgraded from HTTP to WebSocket protocol.
TCP socket stays open persistently.

Phase 2: Data Exchange
─────────────────────────────────
Server → Client:
  WebSocket frame: {"response": "You can return...", "is_done": true}

Client → Server:
  (no messages needed in your current implementation)

Phase 3: Closing
─────────────────────────────────
Server sends WebSocket Close frame (code 1000 - Normal Closure)
Client receives close frame, sends its own close frame back
TCP connection fully closed

Or:
Client navigates away → TCP connection drops
Server catches WebSocketDisconnect exception
Server cleans up Redis subscription
```

---

## 6.4 Your WebSocket Implementation — Deep Walk-Through

```python
@router.websocket("/ws/chat/{session_id}/{job_id}")
async def websocket_chat(websocket: WebSocket, session_id: int, job_id: str):

    # Step 1: Accept the WebSocket upgrade
    await websocket.accept()
    
    # Step 2: Check Redis availability
    pubsub_service = get_redis_pubsub_service()
    if not pubsub_service.is_available():
        await websocket.send_json({...error...})
        return  # Close gracefully

    try:
        # Step 3: Subscribe to Redis channel
        channel_name = f"chat_response:{session_id}"
        subscription = pubsub_service.subscribe(channel_name)

        # Step 4: Wait for worker result (non-blocking via thread)
        result = await asyncio.to_thread(
            pubsub_service.listen_once,
            subscription,
            WEBSOCKET_RESPONSE_TIMEOUT
        )

        # Step 5: Send result to client
        if result:
            await websocket.send_json(result)
        else:
            await websocket.send_json({
                "status": "timeout",
                "response": "Request timed out.",
                "is_done": True
            })

    except WebSocketDisconnect:
        # Client disconnected before getting response
        logger.info(f"WebSocket disconnected: session_id={session_id}")

    finally:
        # Step 6: Always clean up Redis subscription
        pubsub_service.unsubscribe(subscription)
        # WebSocket closes when function returns
```

**Key design decisions:**
1. **`await websocket.accept()`** — must be called before sending or receiving anything
2. **`asyncio.to_thread()`** — offloads blocking Redis `listen_once()` to thread pool
3. **`try/except WebSocketDisconnect`** — handles client closing browser/tab
4. **`finally` block** — always unsubscribes from Redis, even on error or disconnect
5. **Single response then close** — your system is request-response over WebSocket (not persistent chat stream)

---

## 6.5 Persistent Connection Logic

A WebSocket connection stays open as long as:
- Neither side sends a Close frame
- The underlying TCP connection remains alive
- No timeout is triggered by the OS or load balancer

In your system, the WebSocket is designed to:
1. Open when POST /chat/message/queue returns
2. Receive exactly one response message
3. Close immediately after

This is a **semi-persistent** pattern — not permanently open like in a traditional chat app. Future evolution would keep the WebSocket open for the entire user session.

---

## 6.6 Real-Time Streaming Mechanism

The complete data path from AI response to browser screen:

```
OpenAI returns text
      │
      ▼
ChatWorker: json.dumps(result)
      │
      ▼
Redis PUBLISH chat_response:42 "{...json...}"
      │
      ▼ (milliseconds)
Redis delivers to all subscribers of chat_response:42
      │
      ▼
WebSocket handler: listen_once() returns message
      │
      ▼
WebSocket handler: await websocket.send_json(result)
      │
      ▼ (network)
Browser: WebSocket.onmessage event fires
      │
      ▼
Frontend JavaScript: setResponse(message.response)
      │
      ▼
React re-renders with AI response text
```

Total latency from Redis PUBLISH to browser screen: **< 10 milliseconds** (excluding network)

---

## 6.7 Handling Disconnects and Resource Cleanup

**What happens if the user closes the browser while waiting?**

```
T=0:  WebSocket opens
T=1:  AI processing begins
T=5:  User closes browser tab

Browser sends TCP RST (connection reset) or FIN (graceful close)
      │
      ▼
FastAPI detects TCP close
      │
      ▼
WebSocketDisconnect exception is raised in the async handler
      │
      ▼
except WebSocketDisconnect: block executes
  → Log the disconnection
      │
      ▼
finally: block executes
  → pubsub_service.unsubscribe(subscription)
  → Redis PubSub connection closed
  → No resource leak

T=10: Worker finishes, publishes to Redis
  → Publishing succeeds, but nobody is subscribed
  → Message is dropped (fire-and-forget)
  → No error
```

**Without the `finally` block:**
- Redis subscription stays open forever
- After ~10,000 disconnected users, Redis hits connection limit
- New subscriptions fail
- System unavailable

This is why `finally` blocks for resource cleanup are essential.

---

## 6.8 WebSocket Frame Types

| Frame Type | Opcode | Use |
|---|---|---|
| Text | 0x1 | JSON messages (your usage) |
| Binary | 0x2 | Images, audio, binary data |
| Close | 0x8 | Graceful connection termination |
| Ping | 0x9 | Keepalive check |
| Pong | 0xA | Response to ping |

FastAPI's `websocket.send_json()` sends a **text frame** with JSON serialized content. FastAPI's `websocket.send_bytes()` sends a **binary frame**.

---

## 6.9 SSE — How It Would Be Implemented

While your system uses WebSocket, SSE is worth understanding as an alternative:

```python
# SSE implementation example (not in your codebase)
from fastapi.responses import StreamingResponse

@router.get("/sse/chat/{session_id}")
async def sse_chat(session_id: int):
    async def event_generator():
        subscription = pubsub_service.subscribe(f"chat_response:{session_id}")
        try:
            while True:
                message = await asyncio.to_thread(
                    pubsub_service.listen_once, subscription, 60
                )
                if message:
                    yield f"data: {json.dumps(message)}\n\n"
                    if message.get("is_done"):
                        break
        finally:
            pubsub_service.unsubscribe(subscription)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )
```

**SSE wire format:**
```
data: {"response": "You can return...", "is_done": true}

data: {"response": "Additional info...", "is_done": false}

data: {"response": "Final response complete", "is_done": true}

```
(Each message ends with `\n\n`)

---

## 6.10 Interview Questions and Answers

**Q: What is the difference between WebSocket and HTTP long-polling?**

A: HTTP long-polling means the client sends a request that the server holds open until data is available, then responds. The client immediately opens a new request. This creates overhead from repeated HTTP handshakes. WebSocket establishes one persistent TCP connection at startup and keeps it open, with near-zero overhead for subsequent messages.

**Q: What is the WebSocket handshake and why is it needed?**

A: WebSocket starts as an HTTP request with `Upgrade: websocket` header. The server responds with `101 Switching Protocols`. This HTTP-based handshake allows WebSocket to work through existing HTTP infrastructure (proxies, firewalls). After the upgrade, the protocol switches to the WebSocket framing protocol over the same TCP socket.

**Q: Why does your WebSocket close after one response?**

A: The current design is one-request-one-response. The client opens the WebSocket to receive the AI response, gets it (indicated by `is_done: true`), and the connection closes. This is a design choice — not a limitation. Future implementations could keep a long-lived WebSocket for an entire conversation session.

**Q: What happens to the Redis subscription if a WebSocket client disconnects?**

A: FastAPI raises a `WebSocketDisconnect` exception. The `except` block catches it. The `finally` block always runs (even on disconnect) and calls `pubsub_service.unsubscribe(subscription)`, which closes the Redis connection and frees the subscription resource.

**Q: When would you choose SSE over WebSocket?**

A: SSE is simpler for one-way streaming (server → client). It works through standard HTTP load balancers without sticky sessions. It auto-reconnects. Choose SSE for: news feeds, notifications, AI text streaming (OpenAI streaming). Choose WebSocket for: chat apps (bidirectional), collaborative editing, gaming (low latency bidirectional).

---

## 6.11 Common Mistakes

1. **Not calling `websocket.accept()` first** — sending messages before accepting raises an error
2. **Calling blocking code directly in async WebSocket handler** — freezes event loop
3. **Not catching `WebSocketDisconnect`** — unhandled exception leaves resources open
4. **No `finally` cleanup** — Redis subscriptions leaked on every disconnect
5. **Missing timeout on `listen_once()`** — WebSocket can hang forever if worker never responds
6. **Not handling `None` return from `listen_once()`** — timeout case not handled, sends garbage to client

---

## 6.12 Production Considerations

- WebSocket connections stay open on a specific server instance; load balancers need sticky sessions
- Alternatively, use Redis Pub/Sub for cross-server WebSocket delivery (which you already do!)
- Set WebSocket idle timeout at the load balancer level to close orphaned connections
- Use `wss://` (WebSocket over TLS) in production — never `ws://`
- Monitor open WebSocket connections as a metric — alert on unusual spikes
- Implement WebSocket heartbeat (ping/pong) to detect zombie connections
- Use connection limits per user to prevent DoS attacks

---

## 6.13 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/routers/websocket.py` | WebSocket endpoint implementation |
| `backend/app/services/redis_pubsub_service.py` | `subscribe()`, `listen_once()`, `unsubscribe()` |
| `backend/app/config.py` | `WEBSOCKET_RESPONSE_TIMEOUT` |
| `frontend/app/chat/` | Frontend WebSocket client code |
