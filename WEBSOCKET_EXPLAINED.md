# WebSocket — Complete Explanation

> **Focus**: What is a WebSocket, why your project uses it, how the endpoint works,
> and what every part of the code does — explained in plain language with supporting code snippets.

---

## File Reference Index

Every code block in this document is taken from one of these files:

| File | Path | Role |
|---|---|---|
| `websocket.py` | `backend/app/routers/websocket.py` | FastAPI WebSocket endpoint — accepts connection, waits, delivers result |
| `redis_pubsub_service.py` | `backend/app/services/redis_pubsub_service.py` | Provides `collect_job_response()` which the endpoint calls |
| `chat.py` | `backend/app/routers/chat.py` | Provides the `queue_message()` endpoint that creates the `job_id` |
| `chat_worker.py` | `backend/app/worker/chat_worker.py` | Background worker that publishes results to the channel the endpoint listens on |
| `config.py` | `backend/app/config.py` | `WEBSOCKET_RESPONSE_TIMEOUT` and Redis settings |
| `api.ts` | `frontend/services/api.ts` | Frontend: `queueMessage()` and native WebSocket code |
| `main.py` | `backend/app/main.py` | Application startup — registers WebSocket router |

---

## Table of Contents

1. [What is a WebSocket and Why Do You Need It?](#1-what-is-a-websocket-and-why)
2. [WebSocket vs Regular HTTP — The Core Difference](#2-websocket-vs-http)
3. [How WebSocket Fits Into Your Project](#3-how-websocket-fits)
4. [The Complete Chat Flow (WebSocket Path)](#4-the-complete-flow)
5. [The WebSocket Endpoint — websocket.py](#5-the-websocket-endpoint)
6. [The Frontend Side — api.ts and queueMessage](#6-the-frontend-side)
7. [Error Handling and Edge Cases](#7-error-handling)
8. [Configuration Settings](#8-configuration-settings)
9. [Key Concepts You Should Know](#9-key-concepts)

---

## 1. What is a WebSocket and Why Do You Need It?

### HTTP Has a Fundamental Limitation

In normal HTTP, the browser always initiates the conversation:
1. Browser sends request
2. Server sends response
3. Connection closes

The server can never proactively push data to the browser. If the browser wants to know if something changed, it has to ask again (and again, and again). This "polling" approach is wasteful and adds latency.

### Your Specific Problem

When a user asks a question that requires RAG (PDF search + AI), the processing takes several seconds. You cannot make the browser wait in a single HTTP request because:
- The HTTP request would time out
- The server thread is blocked, unable to handle other users
- The UX is bad (spinning, frozen)

The solution you implemented is:
1. The browser sends the question via `POST /chat/message/queue` → gets back a ticket (job_id) instantly
2. The browser opens a WebSocket connection and **waits** for the result to be pushed to it
3. When the worker finishes, Redis Pub/Sub delivers the result to the WebSocket handler
4. The WebSocket handler pushes the result to the browser in real time
5. The connection closes — the browser displays the answer

### What is a WebSocket?

A WebSocket is a **persistent, full-duplex connection** between browser and server established over HTTP and then upgraded. Unlike HTTP, the connection stays open. Either side can send a message at any time without the other side needing to ask.

In your project you only use the WebSocket one way: **server pushes, browser receives**. Once the result arrives, the connection closes. You are not using it for an ongoing chat (each message uses a fresh WebSocket).

---

## 2. WebSocket vs Regular HTTP

| Feature | HTTP (REST) | WebSocket |
|---|---|---|
| Who initiates | Browser always | Browser opens, then either side can send |
| Connection lifecycle | Open → Request → Response → **Closes** | Open → stays open until explicitly closed |
| Server can push? | No | Yes |
| Best for | CRUD operations, fast responses | Real-time delivery, streaming, notifications |
| Your use case | Workflow/FAQ matches (instant) | RAG results (slow, needs push) |

---

## 3. How WebSocket Fits Into Your Project

Your system has two chat paths:

**Path 1 — Synchronous (instant)**

When a message matches a workflow node or FAQ, the answer is returned directly from `POST /chat/message/queue`. The response has `cache_hit: true` and `bot_response` is already populated. No WebSocket needed.

**Path 2 — Asynchronous (RAG)**

When nothing matches, the request is queued to RabbitMQ and the response has `queued: true`. The browser opens a WebSocket and waits. The ChatWorker processes the RAG pipeline and publishes the result to Redis Pub/Sub. The WebSocket handler is subscribed to Redis and forwards the result to the browser the moment it arrives.

```
PATH 1 (cache_hit: true):
  POST /chat/message/queue ──► instant response ──► browser displays answer

PATH 2 (queued: true):
  POST /chat/message/queue ──► "queued" + job_id
       │
       ▼
  WS /ws/chat/{session_id}/{job_id}  ──► waiting...
       │
       ├── RabbitMQ ──► ChatWorker ──► RAG pipeline
       │                                    │
       ├── Redis Pub/Sub ◄─────────────────┘
       │
       ▼
  WebSocket delivers result ──► browser displays answer
```

---

## 4. Code Flow Trace — Every Function Call in Order

This trace shows the exact function name, the file it lives in, and what it does — in execution order for one WebSocket request.

```
[1] BROWSER — Step 1: Queue the RAG Request
    frontend/services/api.ts
    → queueMessage(sessionId, message)
      Sends POST /chat/message/queue
      Returns { job_id, queued: true, cache_hit: false }

[2] BROWSER — Step 2: Open WebSocket
    frontend/services/api.ts  (native browser WebSocket API)
    → new WebSocket(`ws://127.0.0.1:8000/ws/chat/${session_id}/${job_id}`)
      Browser sends HTTP Upgrade request to FastAPI

[3] FASTAPI — Step 3: Accept WebSocket Handshake
    backend/app/routers/websocket.py
    → websocket_chat(websocket: WebSocket, session_id: int, job_id: str)
      This is the @router.websocket("/ws/chat/{session_id}/{job_id}") handler
      await websocket.accept()   ← completes the HTTP→WS upgrade protocol

[4] FASTAPI — Step 4: Check Redis is Available
    backend/app/routers/websocket.py
    → get_redis_pubsub_service()  ← gets/creates singleton from redis_pubsub_service.py
    → pubsub_service.is_available()
      If False → send error JSON → return (WebSocket closes)

[5] FASTAPI — Step 5: Wait for Worker Result (blocking call in thread pool)
    backend/app/routers/websocket.py
    → await asyncio.to_thread(
          pubsub_service.collect_job_response,   ← blocking, runs in thread pool
          job_id,
          WEBSOCKET_RESPONSE_TIMEOUT,             ← from config.py (60 sec)
      )
    This suspends the async WebSocket handler on the event loop.
    The event loop is FREE to handle other requests while this blocks.

[6] THREAD POOL — collect_job_response() runs (inside thread)
    backend/app/services/redis_pubsub_service.py
    → RedisPubSubService.collect_job_response(job_id, timeout=60)
      1. Checks rag_buffer:{job_id} with _publish_client.lrange()  (race condition guard)
      2. If buffer has complete result → return it immediately
      3. If no buffer → calls subscribe("rag_stream:{job_id}")
         subscribe() creates a NEW dedicated Redis connection
      4. Polls pubsub.get_message(timeout=1.0) in a loop

[7] BACKGROUND WORKER — Processes RAG Job
    backend/app/worker/chat_worker.py
    → ChatWorker._process_job(message)   ← triggered by RabbitMQ delivery
      Calls process_rag_message()         ← vector search + LLM
      Builds result payload dict

[8] BACKGROUND WORKER — Publishes Result to Redis
    backend/app/worker/chat_worker.py
    → ChatWorker._publish_response(job_id, session_id, payload)
      Calls pubsub_service.publish("rag_stream:{job_id}", payload)
      → redis_pubsub_service.py: RedisPubSubService.publish()
        json.dumps(payload)  →  _publish_client.publish(channel, body)
        Redis delivers the message to the subscribed collect_job_response() thread

[9] THREAD POOL — collect_job_response() returns
    backend/app/services/redis_pubsub_service.py
    The waiting get_message() unblocks, receives the message
    Deserializes + returns result dict to websocket_chat()
    finally: unsubscribe(pubsub_conn, channel)  ← always runs (cleanup)

[10] FASTAPI — Send Result to Browser
    backend/app/routers/websocket.py
    → await websocket.send_json(result)   or   send timeout error
    finally: await websocket.close()      ← always runs

[11] BROWSER — Receive and Display
    ws.onmessage callback fires
    JSON.parse(event.data)  →  display data.response
    ws.close()  ← browser closes connection
```

---

## 5. The Complete Flow — From Browser to Worker

### Step 1 — Browser Calls Queue Endpoint

📄 **File**: `frontend/services/api.ts` — function `queueMessage()`

```typescript
// 📄 frontend/services/api.ts  — queueMessage() call
const result = await queueMessage(sessionId, "What does clause 7 say?");
// POST /chat/message/queue  { session_id, message }
```

This sends `POST /chat/message/queue` with `{ session_id, message }`. The server checks workflow nodes and FAQ cache. Neither matches. The server publishes a job to RabbitMQ and returns:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": 42,
  "queued": true,
  "cache_hit": false
}
```

### Step 2 — Browser Opens WebSocket

📄 **File**: `frontend/services/api.ts` — native browser WebSocket API

```typescript
// 📄 frontend/services/api.ts  — opening a WebSocket connection
// WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000"
const ws = new WebSocket(
    `${WS_BASE_URL}/ws/chat/${result.session_id}/${result.job_id}`
);
// Example URL: ws://127.0.0.1:8000/ws/chat/42/550e8400-e29b-41d4-a716-446655440000
```

### Step 3 — Server Accepts the Connection

The WebSocket endpoint in FastAPI accepts the handshake. Both sides now have an open connection.

### Step 4 — Server Subscribes to Redis

The WebSocket handler calls `collect_job_response(job_id, timeout=60)`. Internally, this subscribes to the Redis channel `rag_stream:550e8400-e29b-41d4-a716-446655440000` and blocks, waiting for a message to arrive.

This blocking call runs in a thread pool (via `asyncio.to_thread`) so it does not freeze FastAPI's event loop.

### Step 5 — Worker Processes the Job

Meanwhile, in a background thread, `ChatWorker` picks up the job from RabbitMQ, runs the RAG pipeline, and gets the answer from the LLM.

### Step 6 — Worker Publishes Result to Redis

📄 **File**: `backend/app/worker/chat_worker.py` — function `_publish_response()`

```python
# 📄 backend/app/worker/chat_worker.py  — _publish_response() call inside _process_job()
self._publish_response(job_id, session_id, {
    "job_id":       job_id,
    "session_id":   session_id,
    "response":     "Clause 7 states that disputes shall be resolved by arbitration...",
    "next_options": [],
    "status":       "success",
    "is_done":      True,
})
# Internally calls:
# backend/app/services/redis_pubsub_service.py  →  RedisPubSubService.publish()
# channel = f"rag_stream:{job_id}"
```

Redis immediately delivers this message to everyone subscribed to `rag_stream:550e8400-...`. In this case, that is exactly one subscriber: the WebSocket handler's thread.

### Step 7 — WebSocket Handler Receives the Result

`collect_job_response()` returns the result dict. The handler sends it as a JSON text frame over the WebSocket.

### Step 8 — Browser Receives and Displays

📄 **File**: `frontend/services/api.ts` (or any frontend component using the WebSocket)

```typescript
// 📄 frontend/services/api.ts  — browser receiving the WebSocket message
ws.onmessage = (event: MessageEvent) => {
    const data = JSON.parse(event.data);
    // data.response === "Clause 7 states that disputes shall be resolved..."
    // data.status    === "success"
    // data.is_done   === true
    displayResponse(data.response);
    ws.close();   // one message → done
};
```

### Step 9 — Server Closes and Cleans Up

The WebSocket handler enters its `finally` block, ensures the WebSocket is closed, and logs completion.

---

## 6. The WebSocket Endpoint — Full Function Reference

📄 **File**: `backend/app/routers/websocket.py`
**URL pattern**: `WS /ws/chat/{session_id}/{job_id}`

### All Imports Used in websocket.py

```python
# 📄 backend/app/routers/websocket.py  — imports section
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import WEBSOCKET_RESPONSE_TIMEOUT
from app.services.redis_pubsub_service import get_redis_pubsub_service
from app.logging_config import get_logger
```

### Function Reference Table for websocket.py

| Function | Parameters | Returns | Purpose |
|---|---|---|---|
| `websocket_chat()` | `websocket: WebSocket`, `session_id: int`, `job_id: str` | `None` (async coroutine) | Full WebSocket lifecycle: accept → wait → send → close |

There is only one function in `websocket.py`. It handles everything.

---

### `websocket_chat()` — The Complete Endpoint

📄 **File**: `backend/app/routers/websocket.py`
**Function signature**: `async def websocket_chat(websocket: WebSocket, session_id: int, job_id: str) -> None`
**Decorator**: `@router.websocket("/ws/chat/{session_id}/{job_id}")`
**What it does**: Full WebSocket lifecycle: accept the connection, check Redis, wait for the RAG result via Redis Pub/Sub (in a thread pool), send the result to the browser, always close.

```python
# 📄 backend/app/routers/websocket.py  — websocket_chat() complete endpoint
@router.websocket("/ws/chat/{session_id}/{job_id}")
async def websocket_chat(websocket: WebSocket, session_id: int, job_id: str):
```

The URL contains two path parameters:
- `session_id` — the chat session ID (used for logging and error messages)
- `job_id` — the UUID assigned to this specific RAG job (used to subscribe to the right Redis channel)

```python
# 📄 backend/app/routers/websocket.py  — inside websocket_chat()
try:
    await websocket.accept()   # complete the HTTP→WS upgrade
    logger.info(f"🔌 WebSocket connected: session_id={session_id}, job_id={job_id}")
except Exception as e:
    logger.error(f"Failed to accept WebSocket: {e}")
    return
```

```
# 📄 backend/app/routers/websocket.py  — complete execution flow diagram

websocket.accept()
        │
        ▼
pubsub_service = get_redis_pubsub_service()     ← redis_pubsub_service.py singleton
pubsub_service.is_available()?
  NO ──► send error JSON ──► return
  YES ──► continue
        │
        ▼
await asyncio.to_thread(
    pubsub_service.collect_job_response,        ← redis_pubsub_service.py
    job_id, WEBSOCKET_RESPONSE_TIMEOUT          ← config.py (60 sec)
)
  Inside the thread:
    ├── Check rag_buffer:{job_id}  →  found? return result
    ├── Subscribe to rag_stream:{job_id}
    │       ├── message arrives ──► return result dict
    │       └── 60 sec timeout ──► return None
    └── finally: unsubscribe(pubsub_conn, channel)
result = (dict | None)
        │
        ▼
result is None?
  YES ──► await websocket.send_json(timeout error)
  NO  ──► await websocket.send_json(result)
        │
        ▼
[finally] await websocket.close()
```

---

## 7. The Frontend Side — Full Code Reference

📄 **File**: `frontend/services/api.ts`

### All Relevant Exports from api.ts

| Export | Type | Purpose |
|---|---|---|
| `WS_BASE_URL` | `const string` | Base URL for WebSocket connections (`ws://127.0.0.1:8000`) |
| `queueMessage()` | `async function` | Send message to queue endpoint, returns `job_id` |
| `request()` | `async function` | Internal HTTP helper — attaches Bearer token, handles 401 |

---

### `WS_BASE_URL` — WebSocket Base URL

📄 **File**: `frontend/services/api.ts`

```typescript
// 📄 frontend/services/api.ts  — constant
export const WS_BASE_URL =
    process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";
// In development: ws://127.0.0.1:8000
// In production:  set NEXT_PUBLIC_WS_URL to ws://your-domain.com
```

`http://` becomes `ws://` for WebSocket connections (or `https://` → `wss://` for TLS).

---

### `queueMessage()` — Send the Chat Request

📄 **File**: `frontend/services/api.ts`
**Function signature**: `export async function queueMessage(sessionId: string | number, message: string)`
**Returns**: Promise with `{ job_id, session_id, queued, cache_hit, bot_response?, options? }`

```typescript
// 📄 frontend/services/api.ts  — queueMessage() function
export async function queueMessage(
    sessionId: string | number,
    message: string
): Promise<{
    job_id: string;
    session_id: number;
    queued: boolean;
    cache_hit: boolean;
    bot_response?: string;
    options?: { id?: number; text: string }[];
}> {
    return request(`/chat/message/queue`, {
        method: "POST",
        body: { session_id: sessionId, message },
    });
    // request() is the internal helper that adds Authorization: Bearer <token>
}
```

This sends the chat message and waits for the server to confirm receipt. The response tells the frontend what to do next:

- If `cache_hit: true` → the answer is in `bot_response`. Display it. Done.
- If `queued: true` → open a WebSocket with the returned `job_id`.

---

### Typical Frontend Usage Pattern

📄 **File**: `frontend/services/api.ts` / any component using the chat API

```typescript
// 📄 frontend component  — complete WebSocket usage pattern
const result = await queueMessage(sessionId, userMessage);
// queueMessage is defined in: frontend/services/api.ts

if (result.cache_hit) {
    // Workflow or FAQ answered instantly — no WebSocket needed
    displayMessage(result.bot_response);

} else if (result.queued) {
    // RAG job queued — open WebSocket to wait for result
    showTypingIndicator();   // "Bot is thinking..."

    // WS_BASE_URL is defined in: frontend/services/api.ts
    const ws = new WebSocket(
        `${WS_BASE_URL}/ws/chat/${result.session_id}/${result.job_id}`
    );

    ws.onopen = () => {
        // Connection established — waiting for server to push the result
        // No need to send any message; job_id in URL tells server what to deliver
    };

    ws.onmessage = (event: MessageEvent) => {
        hideTypingIndicator();
        const data = JSON.parse(event.data);
        // data.response     = the bot's answer string
        // data.status       = "success" or "error"
        // data.is_done      = true (signals final message)
        // data.next_options = [] (optional follow-up buttons)

        if (data.status === "error") {
            displayError(data.response);
        } else {
            displayMessage(data.response, data.next_options);
        }
        ws.close();   // one message per connection — close after receiving
    };

    ws.onerror = (event: Event) => {
        hideTypingIndicator();
        displayError("Connection failed. Please try again.");
    };

    ws.onclose = (event: CloseEvent) => {
        // Connection closed — clean up any loading state
        hideTypingIndicator();
    };
}
```

---

## 8. Error Handling and Edge Cases

📄 **File**: `backend/app/routers/websocket.py` (error handling), `backend/app/worker/chat_worker.py` (worker errors), `backend/app/services/redis_pubsub_service.py` (Redis errors)

Your WebSocket endpoint is designed to handle every possible failure. Here is the full table:

| Scenario | What Happens | What Browser Sees |
|---|---|---|
| Normal success | Worker finishes, publishes result, WebSocket delivers | Bot response displayed |
| Redis is down | Endpoint sends error immediately | "Streaming service unavailable" |
| Worker takes > 60 seconds | `collect_job_response` times out, returns None | "Request timed out. Please try again." |
| Worker crashes mid-job | Worker's `finally` block publishes an error payload | "An error occurred while processing your request." |
| Browser disconnects while waiting | `WebSocketDisconnect` caught, cleanup runs | Nothing (user already left) |
| Unexpected server exception | Exception caught, error JSON sent if connection still open | "An unexpected error occurred." |
| Job payload was invalid | ChatWorker validates and publishs error before processing RAG | "Invalid job payload received." |

The key design principle is: **the browser should never be left hanging**. Every code path eventually sends a message with `"is_done": true` to the browser, so the frontend always knows when to stop waiting.

---

## 9. Configuration Settings

📄 **File**: `backend/app/config.py` — WebSocket section

```python
# 📄 backend/app/config.py  — WebSocket configuration
WEBSOCKET_RESPONSE_TIMEOUT = float(os.getenv("WEBSOCKET_RESPONSE_TIMEOUT", "60"))
# How many seconds the WebSocket endpoint waits for the RAG result before timing out.
# Default: 60 seconds
# Lower: faster timeout error messages
# Higher: allows very slow RAG queries to complete
```

---

## 10. Key Concepts

### Why Not Just Use HTTP Long-Polling Instead?

You could implement this without WebSockets: the browser keeps making `GET /chat/result/{job_id}` requests every second until the answer is ready. This is called long-polling.

The problem: it creates many unnecessary HTTP requests, adds 0.5–1 second average latency (depending on poll interval), and uses more server resources. WebSocket is cleaner — the result arrives within milliseconds of being published.

### How the WebSocket Router is Registered

📄 **File**: `backend/app/main.py` — router registration on startup

```python
# 📄 backend/app/main.py  — WebSocket router registration
from app.routers import websocket as websocket_router

app.include_router(
    websocket_router.router,
    # No prefix — the full path /ws/chat/{session_id}/{job_id} is in websocket.py
)
```

The WebSocket endpoint is registered on the main FastAPI `app` at startup. FastAPI handles the HTTP→WS upgrade internally when a client connects to `/ws/chat/{...}/{...}`.

### Why Does the WebSocket Close After One Message?

Your design uses one WebSocket connection per RAG query (each question opens a fresh connection). This is deliberate:

- It is simple — no need to manage which message belongs to which question.
- It is stateless — the `job_id` in the URL scopes everything.
- There is no risk of messages from different queries appearing in the wrong chat bubble.

A more complex design would keep a single WebSocket open for the entire chat session and multiplex multiple queries over it. That is more efficient but much harder to implement correctly.

### `daemon=True` and the Worker Thread

The ChatWorker that publishes to Redis runs in a daemon thread (`daemon=True` in `main.py`). If FastAPI shuts down, this thread is killed immediately — even if it is mid-RAG-query. In that case, the WebSocket handler's 60-second timeout will eventually fire and send a timeout error to the browser. This is acceptable — the worker will restart when FastAPI restarts.

### The Role of `session_id` vs `job_id` in the URL

Both are in the WebSocket URL: `/ws/chat/{session_id}/{job_id}`.

| Identifier | Source | Purpose in WebSocket |
|---|---|---|
| `session_id` | Created when chat starts | Logging and error message context |
| `job_id` | UUID created by queue endpoint | Identifies the Redis Pub/Sub channel |

The actual work is done using `job_id`. The `session_id` is mainly for human-readable logs so you can trace "which session's WebSocket timed out" in your log files.

### No Authentication on WebSocket

The WebSocket endpoint has no JWT check. The comment in `websocket.py` explains why: `POST /chat/message/queue` (which creates the job) also has no auth. The `session_id`+`job_id` combination is unique enough to scope the response — a random user who guessed your job_id UUID would just receive your answer, which has little attack surface compared to the complexity of adding WebSocket auth.

If you wanted to add auth in production, you would validate a JWT token passed as a query parameter when opening the WebSocket:
```
ws://...8000/ws/chat/42/550e8400-...?token=<jwt>
```
Then in the endpoint, extract and validate the token before calling `websocket.accept()`.
