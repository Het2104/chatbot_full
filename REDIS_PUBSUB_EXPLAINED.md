# Redis Pub/Sub — Complete Explanation

> **Focus**: What is Redis Pub/Sub, why your project uses it, how the code is structured,
> and what every function does — explained in plain language with supporting code snippets.

---

## File Reference Index

Every code block in this document is taken from one of these files:

| File | Path | Role |
|---|---|---|
| `redis_pubsub_service.py` | `backend/app/services/redis_pubsub_service.py` | Entire Pub/Sub logic — publish + subscribe |
| `chat_worker.py` | `backend/app/worker/chat_worker.py` | Consumer that publishes results to Redis |
| `websocket.py` | `backend/app/routers/websocket.py` | WebSocket endpoint that reads from Redis |
| `config.py` | `backend/app/config.py` | All Redis configuration constants |
| `api.ts` | `frontend/services/api.ts` | Frontend that opens the WebSocket |
| `main.py` | `backend/app/main.py` | Application startup — starts the worker |

---

## Table of Contents

1. [What is Redis Pub/Sub and Why Do You Need It?](#1-what-is-redis-pubsub-and-why)
2. [Pub/Sub vs Regular Redis Cache — The Difference](#2-pubsub-vs-cache)
3. [How Pub/Sub Works in Your Project](#3-how-pubsub-works)
4. [Where Pub/Sub Lives in Your Project](#4-where-pubsub-lives)
5. [The Channel Naming Strategy](#5-channel-naming)
6. [RedisPubSubService — Every Function Explained](#6-redispubsubservice)
7. [The Two Worker Formats — Internal vs Docker](#7-two-worker-formats)
8. [Configuration Settings](#8-configuration-settings)
9. [Key Concepts You Should Know](#9-key-concepts)

---

## 1. What is Redis Pub/Sub and Why Do You Need It?

### The Bridge Problem

After RabbitMQ delivers a job to the `ChatWorker` and the worker finishes processing, you have the answer sitting in a background thread. The browser is waiting on a WebSocket connection. These two things need to communicate, but they live in completely different places:

- The **ChatWorker** is a background thread with no access to WebSocket connections.
- The **WebSocket endpoint** is an async function handling a specific client's connection, with no knowledge of what the worker is doing.

You need a bridge. That bridge is Redis Pub/Sub.

```
ChatWorker (background thread)
    │
    │  "I finished job 550e8400, here is the answer"
    │
    ▼
Redis Pub/Sub channel: "rag_stream:550e8400"
    │
    │  "A message arrived on your channel"
    │
    ▼
WebSocket handler (waiting for this exact channel)
    │
    ▼
Browser receives the answer
```

### Why Redis Pub/Sub Specifically?

You could have stored the result in the database and had the WebSocket poll every second. But that would mean:
- Unnecessary database queries
- Latency added by polling interval
- The WebSocket would still need to know when to stop polling

Redis Pub/Sub delivers the message **immediately** the moment the publisher calls `publish()`. The subscriber does not poll — it just waits, and Redis pushes the message to it. This is faster, simpler, and uses no CPU when nothing is happening.

---

## 2. Pub/Sub vs Regular Redis Cache — The Difference

Your project uses Redis for two completely different purposes. It is important to understand both.

| Feature | Redis Cache (FAQ) | Redis Pub/Sub |
|---|---|---|
| **Purpose** | Store FAQ answers to avoid DB queries | Deliver one-time job results between components |
| **Persistence** | Stored in Redis until TTL expires or deleted | Message is gone the moment it is delivered |
| **Reading** | Any code can read at any time with `GET key` | Only active subscribers receive the message |
| **Writing** | Any code can write with `SET key value` | Publisher uses `PUBLISH channel message` |
| **Commands used** | GET, SET, SETEX, DELETE | PUBLISH, SUBSCRIBE, UNSUBSCRIBE |
| **Your files** | `redis_cache_service.py`, `faq_service.py` | `redis_pubsub_service.py`, `chat_worker.py`, `websocket.py` |

The most critical difference: **if nobody is subscribed when a message is published, the message is lost**. Redis Pub/Sub has no built-in message storage. This is why your `collect_job_response()` function has a buffer fallback mechanism — more on that in section 7.

---

## 3. How Pub/Sub Works in Your Project

### The Full Journey

```
Step 1: Browser opens WebSocket at /ws/chat/{session_id}/{job_id}

Step 2: WebSocket handler calls:
        pubsub_service.collect_job_response(job_id, timeout=60)
        This internally calls subscribe("rag_stream:{job_id}")
        The handler is now WAITING for a message on this channel.

Step 3: RabbitMQ delivers the job to ChatWorker.
        ChatWorker processes RAG (takes seconds).

Step 4: ChatWorker calls:
        pubsub_service.publish("rag_stream:{job_id}", result_dict)
        Redis delivers the message to all subscribers of that channel.

Step 5: The WebSocket handler's subscribe loop receives the message.
        collect_job_response() returns the result dict.

Step 6: WebSocket handler sends the JSON to the browser.
        Browser displays the answer.
```

The key insight is **timing**: the WebSocket subscribes BEFORE the worker finishes so it is already listening when the message arrives. There is also a race condition handler for when the worker finishes before the WebSocket subscribes — explained in Section 7.

---

## 4. Code Flow Trace — Every Function Call in Order

This trace shows the exact function name, the file it lives in, and what it does — in execution order.

```
[1] BROWSER
    frontend/services/api.ts
    → queueMessage(sessionId, message)
      result.queued === true  →  open WebSocket

[2] BROWSER OPENS WEBSOCKET
    frontend/services/api.ts
    → new WebSocket(`ws://127.0.0.1:8000/ws/chat/${session_id}/${job_id}`)

[3] FASTAPI ACCEPTS WEBSOCKET
    backend/app/routers/websocket.py
    → websocket_chat(websocket, session_id, job_id)
      await websocket.accept()

[4] WEBSOCKET CALLS collect_job_response (in thread pool)
    backend/app/routers/websocket.py
    → await asyncio.to_thread(
          pubsub_service.collect_job_response,
          job_id, WEBSOCKET_RESPONSE_TIMEOUT
      )

[5] collect_job_response CHECKS BUFFER FIRST
    backend/app/services/redis_pubsub_service.py
    → RedisPubSubService.collect_job_response(job_id, timeout)
      Reads rag_buffer:{job_id} with _publish_client.lrange()
      If tokens found and complete → return assembled result immediately

[6] IF NO BUFFER → SUBSCRIBE TO LIVE CHANNEL
    backend/app/services/redis_pubsub_service.py
    → RedisPubSubService.subscribe(channel="rag_stream:{job_id}")
      Creates a NEW dedicated Redis connection (not the shared pool)
      Returns a PubSub object listening on that channel

[7] WORKER PICKS UP JOB FROM RABBITMQ
    backend/app/worker/chat_worker.py
    → ChatWorker._process_job(message)
      Calls process_rag_message() → gets the LLM answer

[8] WORKER PUBLISHES RESULT TO REDIS
    backend/app/worker/chat_worker.py
    → ChatWorker._publish_response(job_id, session_id, payload)
      Calls pubsub_service.publish("rag_stream:{job_id}", payload)

[9] pubsub.publish() SENDS THE MESSAGE
    backend/app/services/redis_pubsub_service.py
    → RedisPubSubService.publish(channel, message)
      json.dumps(message)  →  _publish_client.publish(channel, body)
      Redis delivers to subscribed connections immediately

[10] collect_job_response RECEIVES THE MESSAGE
    backend/app/services/redis_pubsub_service.py
    → still inside collect_job_response() — the waiting loop unblocks
      Deserializes message, checks format (internal or Docker)
      Returns the result dict

[11] WEBSOCKET HANDLER SENDS RESULT TO BROWSER
    backend/app/routers/websocket.py
    → await websocket.send_json(result)

[12] CLEANUP
    backend/app/services/redis_pubsub_service.py
    → RedisPubSubService.unsubscribe(pubsub_conn, channel)
      Closes the dedicated subscribe connection
    backend/app/routers/websocket.py
    → await websocket.close()
```

---

## 5. Where Pub/Sub Lives in Your Project

```
backend/
  app/
    services/
      redis_pubsub_service.py      ← The entire Pub/Sub logic
    worker/
      chat_worker.py               ← Calls publish() after RAG finishes
    routers/
      websocket.py                 ← Calls collect_job_response() while waiting
    config.py                      ← Redis connection settings
```

There is also a single shared instance (singleton) of `RedisPubSubService` used by both the worker and the WebSocket handler. This ensures all parts of the application share the same connection pool for publishing.

---

## 5. The Channel Naming Strategy

Each job gets its own dedicated Redis channel. The channel name includes the unique `job_id` (a UUID), so there is zero chance of one user's response reaching another user's WebSocket.

```python
# Example channel names:
"rag_stream:550e8400-e29b-41d4-a716-446655440000"
"rag_stream:7f8d2e1a-3b4c-5d6e-7f8a-9b0c1d2e3f4a"
```

There are also buffer keys for the Docker worker (explained in Section 7):
```python
"rag_buffer:550e8400-e29b-41d4-a716-446655440000"
```

**Why the `chat_response:` prefix in config.py?** You will see `REDIS_PUBSUB_CHANNEL_PREFIX = "chat_response"` in config. This is a legacy prefix referenced in older helpers. In practice, the code that actually runs uses `rag_stream:{job_id}` for channels — matching both the internal ChatWorker and the Docker-based worker format.

---

## 6. RedisPubSubService Class — Every Function Explained

📄 **File**: `backend/app/services/redis_pubsub_service.py`

### All Imports Used in redis_pubsub_service.py

```python
# 📄 backend/app/services/redis_pubsub_service.py  — imports section
import json
import logging
import time
from typing import Any, Dict, Optional

import redis
from redis.client import PubSub

from app.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_SSL,
    REDIS_SOCKET_TIMEOUT,
    REDIS_SOCKET_CONNECT_TIMEOUT,
    WEBSOCKET_RESPONSE_TIMEOUT,
)
```

### Function Reference Table

| Function | Parameters | Returns | Purpose |
|---|---|---|---|
| `__init__()` | none | — | Create connection pool + publish client |
| `is_available()` | none | `bool` | Check if Redis is reachable |
| `health_check()` | none | `bool` | Ping Redis to confirm it's alive |
| `get_channel_name()` | `session_id: int` | `str` | Build `chat_response:{session_id}` channel string |
| `publish()` | `channel: str`, `message: Dict` | `bool` | JSON-serialize and publish message to channel |
| `publish_to_session()` | `session_id: int`, `message: Dict` | `bool` | Convenience: build channel name then publish |
| `subscribe()` | `channel: str` | `Optional[PubSub]` | Create NEW dedicated connection and subscribe |
| `unsubscribe()` | `pubsub: PubSub`, `channel: str` | `None` | Close subscription + dedicated connection |
| `listen_once()` | `pubsub: PubSub`, `timeout: float` | `Optional[dict]` | Poll for one message (older method) |
| `collect_job_response()` | `job_id: str`, `timeout: float` | `Optional[dict]` | Full lifecycle: buffer check + subscribe + wait |
| `close()` | none | `None` | Shut down publish connection pool |
| `get_redis_pubsub_service()` | none | `RedisPubSubService` | Module-level singleton factory |

---

### `__init__(selfself)` — Constructor

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def __init__(self) -> None`
**What it does**: Builds a Redis connection pool and creates a single shared publish client. Subscribe connections are created separately per request.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — __init__() method
def __init__(self):
    """Initialize Redis Pub/Sub service with a pooled publish client."""
    self._available = False
    self._publish_client: Optional[redis.Redis] = None

    try:
        pool_config = {
            "host":             REDIS_HOST,
            "port":             REDIS_PORT,
            "db":               REDIS_DB,
            "decode_responses": True,   # bytes → str automatically
            "max_connections":  50,
        }
        if REDIS_PASSWORD:
            pool_config["password"] = REDIS_PASSWORD
        if REDIS_SSL:
            pool_config["ssl"] = True

        pool = redis.ConnectionPool(**pool_config)
        self._publish_client = redis.Redis(connection_pool=pool)
        self._publish_client.ping()   # verify the connection works at startup
        self._available = True
        logger.info("✅ Redis Pub/Sub service initialized.")

    except redis.ConnectionError as e:
        logger.error(f"❌ Redis Pub/Sub unavailable: {e}")
        self._available = False
```

---

### `is_available(self) -> bool` — Check If Redis Is Reachable

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def is_available(self) -> bool`
**Returns**: `True` if the publish client exists and `_available` flag is set
**What it does**: Checked at the top of every public method. If Redis is down, methods return `None` or `False` instead of crashing.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — is_available() method
def is_available(self) -> bool:
    return self._available and self._publish_client is not None
```

---

### `health_check(self) -> bool` — Ping Redis

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def health_check(self) -> bool`
**Returns**: `True` if Redis responds to PING, `False` otherwise
**What it does**: Sends a `PING` command to Redis. Redis responds with `PONG`. Used by health check endpoints.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — health_check() method
def health_check(self) -> bool:
    if not self.is_available():
        return False
    try:
        return bool(self._publish_client.ping())  # PING → PONG
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
```

---

### `get_channel_name(self, session_id) -> str` — Build Channel String

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def get_channel_name(self, session_id: int) -> str`
**Returns**: A string like `"chat_response:42"`
**What it does**: Builds a channel name using the configured prefix and a session ID. Used by `publish_to_session()`.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — get_channel_name() method
def get_channel_name(self, session_id: int) -> str:
    # REDIS_PUBSUB_CHANNEL_PREFIX = "chat_response"  (from config.py)
    return f"{REDIS_PUBSUB_CHANNEL_PREFIX}:{session_id}"
    # Example: "chat_response:42"
```

---

### `publish(self, channel, message) -> bool` — Send a Message

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def publish(self, channel: str, message: Dict[str, Any]) -> bool`
**Parameters**:
- `channel` — the Redis channel to publish to (e.g. `"rag_stream:{job_id}"`)
- `message` — Python dict to JSON-serialize and publish

**Returns**: `True` if Redis accepted the command, `False` if Redis unavailable
**What it does**: JSON-serializes the message dict and calls Redis `PUBLISH channel body`. Redis immediately delivers the message string to all active subscribers on that channel.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — publish() method
def publish(self, channel: str, message: Dict[str, Any]) -> bool:
    if not self.is_available():
        logger.warning("Redis Pub/Sub not available, cannot publish.")
        return False
    try:
        body = json.dumps(message)             # dict → JSON string
        receivers = self._publish_client.publish(channel, body)
        # receivers = count of subscribers that received this message
        # It will be 0 if no WebSocket is currently subscribed (race condition edge case)
        logger.debug(f"📤 Published to '{channel}' ({receivers} receivers): {message}")
        return True
    except Exception as e:
        logger.error(f"❌ Redis publish error on channel '{channel}': {e}")
        return False
```

**Why does `receivers` matter?** If `receivers == 0`, no WebSocket was subscribed when the message was published. This can happen if the worker was extremely fast and the WebSocket hadn't subscribed yet. That is the race condition handled by the buffer replay in `collect_job_response()`.

---

### `publish_to_session(self, session_id, message) -> bool` — Convenience Wrapper

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def publish_to_session(self, session_id: int, message: Dict[str, Any]) -> bool`
**Returns**: Same as `publish()` — `True` if Redis accepted the command
**What it does**: Builds the channel name from a session ID, then calls `publish()`.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — publish_to_session() method
def publish_to_session(self, session_id: int, message: Dict[str, Any]) -> bool:
    channel = self.get_channel_name(session_id)   # "chat_response:{session_id}"
    return self.publish(channel, message)
```

---

### `subscribe(self, channel) -> Optional[PubSub]` — Create a Subscription

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def subscribe(self, channel: str) -> Optional[PubSub]`
**Parameters**: `channel` — the Redis channel to listen on (e.g. `"rag_stream:{job_id}"`)
**Returns**: A `PubSub` object (from the `redis-py` library) or `None` if Redis is unavailable
**What it does**: Creates a **new dedicated Redis connection** (not from the shared pool) and tells Redis to start delivering messages on that channel to this connection.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — subscribe() method
def subscribe(self, channel: str) -> Optional[PubSub]:
    if not self.is_available():
        return None
    try:
        # ⚠️ IMPORTANT: Each subscribe() creates a BRAND-NEW connection
        # (not from the shared publish pool — subscribed connections can't do GET/SET)
        sub_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_timeout=None,              # blocking — no read timeout
            socket_connect_timeout=5,         # 5 sec to establish connection
        )
        pubsub = sub_client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)             # tell Redis: deliver messages here
        logger.debug(f"📡 Subscribed to Redis channel: '{channel}'")
        return pubsub
    except Exception as e:
        logger.error(f"❌ Redis subscribe failed on channel '{channel}': {e}")
        return None
```

**Why a separate connection?** Once a Redis connection calls `SUBSCRIBE`, it enters a restricted mode. In that mode, only `SUBSCRIBE`, `UNSUBSCRIBE`, `PSUBSCRIBE`, `PUNSUBSCRIBE`, and `PING` are allowed — no `GET`, `SET`, `LRANGE`, or any other command. The shared `_publish_client` pool would break if you called `SUBSCRIBE` on it. Each WebSocket handler gets its own isolated subscribe connection.

**`socket_timeout=None`** means this connection never times out waiting for a Redis response. The caller controls the timeout explicitly (via elapsed time checks in `collect_job_response`).

---

### `unsubscribe(self, pubsub, channel) -> None` — Clean Up a Subscription

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def unsubscribe(self, pubsub: PubSub, channel: str) -> None`
**Returns**: Nothing
**What it does**: Sends an `UNSUBSCRIBE` command to Redis, then closes the dedicated connection that was created by `subscribe()`.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — unsubscribe() method
def unsubscribe(self, pubsub: PubSub, channel: str) -> None:
    try:
        pubsub.unsubscribe(channel)   # tell Redis: stop delivering to this connection
        pubsub.close()                # close the dedicated socket
        logger.debug(f"📴 Unsubscribed from Redis channel: '{channel}'")
    except Exception as e:
        logger.warning(f"Redis unsubscribe error on '{channel}': {e}")
```

This is **always called in a `finally` block** inside `collect_job_response()`. Without this, the dedicated Redis connection created by `subscribe()` would stay open forever — leaking memory on both the Redis server and your application.

---

### `listen_once(self, pubsub, timeout) -> Optional[dict]` — Wait for One Message (Older Method)

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def listen_once(self, pubsub: PubSub, timeout: float = 30.0) -> Optional[dict]`
**Parameters**: `pubsub` — subscription object from `subscribe()`; `timeout` — max seconds to wait
**Returns**: Deserialized message dict, or `None` if timed out
**What it does**: Polls `pubsub.get_message()` in a loop with a 1-second window. Returns the first real message received, or `None` after timeout.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — listen_once() method
def listen_once(self, pubsub: PubSub, timeout: float = 30.0) -> Optional[dict]:
    deadline = time.monotonic() + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None                    # timeout reached

        message = pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=min(1.0, remaining),   # poll max 1 second at a time
        )

        if message is None:
            continue                        # no message yet — keep waiting

        if message.get("type") != "message":
            continue                        # system message — skip

        data = message.get("data")
        return json.loads(data)            # deserialize and return
```

**Why `timeout=min(1.0, remaining)`?** If you used `timeout=remaining` directly, `get_message()` would block for up to the full remaining time even if a message arrives sooner. Using `min(1.0, remaining)` means the function checks for a message every 1 second at most, while still respecting the overall deadline.

---

### `collect_job_response(self, job_id, timeout) -> Optional[dict]` — The Main Response Collector

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def collect_job_response(self, job_id: str, timeout: float = 60.0) -> Optional[dict]`
**Parameters**:
- `job_id` — UUID of the job to collect the result for
- `timeout` — max seconds to wait before giving up (default 60, from `WEBSOCKET_RESPONSE_TIMEOUT`)

**Returns**: Result dict with `{response, status, is_done, next_options}` or `None` if timed out
**What it does**: The full lifecycle of waiting for a job result. First checks the Redis buffer (handles race conditions). If not buffered, subscribes to the live Pub/Sub channel and waits up to `timeout` seconds.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — collect_job_response() method
def collect_job_response(self, job_id: str, timeout: float = 60.0) -> Optional[dict]:
    channel    = f"rag_stream:{job_id}"
    buffer_key = f"rag_buffer:{job_id}"

    if not self.is_available():
        return None

    # ── Path A: Check buffer first (handles race condition) ─────────────────
    buffered = self._publish_client.lrange(buffer_key, 0, -1)
    if buffered:
        tokens = []
        for raw in buffered:
            msg = json.loads(raw)
            if msg["type"] == "token":
                tokens.append(msg["content"])
            elif msg["type"] == "complete":
                return {"response": "".join(tokens), "status": "success", "is_done": True}
            elif msg["type"] == "error":
                return {"response": msg["content"], "status": "error", "is_done": True}

    # ── Path B: Subscribe and wait for live message ──────────────────────────
    pubsub_conn = self.subscribe(channel)
    if pubsub_conn is None:
        return None

    deadline = time.monotonic() + timeout
    tokens = []

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None     # 60-second timeout reached

            msg_raw = pubsub_conn.get_message(
                ignore_subscribe_messages=True,
                timeout=min(1.0, remaining),
            )
            if msg_raw is None:
                continue        # no message yet

            msg = json.loads(msg_raw["data"])

            # Handle Docker worker token streaming
            if msg.get("type") == "token":
                tokens.append(msg["content"])
            elif msg.get("type") == "complete":
                return {"response": "".join(tokens), "status": "success", "is_done": True}
            elif msg.get("type") == "error":
                return {"response": msg["content"], "status": "error", "is_done": True}

            # Handle internal ChatWorker single-message format
            elif msg.get("is_done") or msg.get("status") in ("success", "error"):
                return {
                    "response":     msg.get("response", ""),
                    "next_options": msg.get("next_options", []),
                    "status":       msg.get("status", "success"),
                    "is_done":      True,
                }
    finally:
        self.unsubscribe(pubsub_conn, channel)   # always clean up
```

This function handles two message formats transparently. The next section explains why two formats exist.

---

### `close(self) -> None` — Shutdown the Service

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def close(self) -> None`
**What it does**: Closes the connection pool used by the shared publish client. Called at application shutdown.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — close() method
def close(self) -> None:
    try:
        if self._publish_client:
            self._publish_client.close()   # close the connection pool
            logger.info("Redis Pub/Sub publish client closed.")
    except Exception as e:
        logger.warning(f"Error closing Redis Pub/Sub client: {e}")
```

---

### The Singleton — `get_redis_pubsub_service()`

📄 **File**: `backend/app/services/redis_pubsub_service.py`
**Function signature**: `def get_redis_pubsub_service() -> RedisPubSubService`
**Returns**: The single shared `RedisPubSubService` instance
**What it does**: Creates the `RedisPubSubService` on first call, then returns the same instance every subsequent call. This ensures all parts of the app share one connection pool.

```python
# 📄 backend/app/services/redis_pubsub_service.py  — singleton pattern
_redis_pubsub_service: Optional[RedisPubSubService] = None

def get_redis_pubsub_service() -> RedisPubSubService:
    global _redis_pubsub_service
    if _redis_pubsub_service is None:
        _redis_pubsub_service = RedisPubSubService()  # create once
    return _redis_pubsub_service                       # reuse every time
```

Used in:
- `backend/app/worker/chat_worker.py` → `get_redis_pubsub_service()` in `ChatWorker.__init__()`
- `backend/app/routers/websocket.py` → `get_redis_pubsub_service()` in the WebSocket handler

---

## 7. The Two Worker Formats

Your `collect_job_response()` handles two different message formats. This is because your system supports two worker implementations:

### Format 1 — Internal ChatWorker

📄 **Publisher**: `backend/app/worker/chat_worker.py` → `_publish_response()`

Your `ChatWorker` publishes a **single complete message** containing the full answer:

```json
// 📄 Message published to Redis channel "rag_stream:{job_id}"
// by: backend/app/worker/chat_worker.py → ChatWorker._publish_response()
{
    "job_id":       "550e8400-...",
    "session_id":   42,
    "response":     "Section 4.2 states that late penalties are 1.5% per month...",
    "next_options": [],
    "status":       "success",
    "is_done":      true
}
```

`collect_job_response()` detects this format by checking for `"is_done": true` or `"status" in ("success", "error")`.

### Format 2 — Docker Worker (Token Streaming)

📄 **Publisher**: Docker-based worker → publishes tokens one by one

A Docker-based worker streams the LLM response token by token:

```json
// 📄 Messages published to Redis channel "rag_stream:{job_id}"
// by: Docker-based worker (external)
{ "type": "token",    "content": "Section" }
{ "type": "token",    "content": " 4.2" }
{ "type": "token",    "content": " states" }
...
{ "type": "complete" }
```

The Docker worker also writes every token to a Redis List (`rag_buffer:{job_id}`) before publishing. This solves the race condition — `collect_job_response()` checks the buffer FIRST:

```python
# 📄 backend/app/services/redis_pubsub_service.py  — buffer check inside collect_job_response()
buffer_key = f"rag_buffer:{job_id}"
buffered   = self._publish_client.lrange(buffer_key, 0, -1)  # get all items from Redis List
if buffered:
    tokens = []
    for raw in buffered:
        msg = json.loads(raw)
        if msg["type"] == "token":
            tokens.append(msg["content"])          # accumulate tokens
        elif msg["type"] == "complete":
            return {"response": "".join(tokens), "status": "success", "is_done": True}
        elif msg["type"] == "error":
            return {"response": msg["content"],   "status": "error",   "is_done": True}
```

---

## 8. Configuration Settings

📄 **File**: `backend/app/config.py` — Redis section

```python
# 📄 backend/app/config.py  — Redis configuration block

# ============================================================================
# Redis Core Connection
# ============================================================================
REDIS_HOST     = os.getenv("REDIS_HOST",     "localhost")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB       = int(os.getenv("REDIS_DB",   "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_SSL      = os.getenv("REDIS_SSL",      "false").lower() == "true"

REDIS_SOCKET_TIMEOUT         = int(os.getenv("REDIS_SOCKET_TIMEOUT",         "5"))
REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

# ============================================================================
# Pub/Sub Specific
# ============================================================================
REDIS_PUBSUB_CHANNEL_PREFIX = "chat_response"   # legacy prefix for get_channel_name()
WEBSOCKET_RESPONSE_TIMEOUT  = float(os.getenv("WEBSOCKET_RESPONSE_TIMEOUT", "60"))
# Controls how long collect_job_response() waits before timing out
```

| Setting | Default | What it controls |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis server address |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |
| `REDIS_PASSWORD` | `""` | Authentication password (empty = no auth) |
| `REDIS_SSL` | `false` | Enable TLS encryption |
| `REDIS_SOCKET_TIMEOUT` | `5` | Seconds before read operations time out |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5` | Seconds to establish a connection |
| `REDIS_PUBSUB_CHANNEL_PREFIX` | `chat_response` | Prefix for `get_channel_name()` |
| `WEBSOCKET_RESPONSE_TIMEOUT` | `60` | Max seconds to wait for a job result |

---

## 9. Key Concepts

### Pub/Sub Has No Memory

Unlike a queue (RabbitMQ), Redis Pub/Sub does not store messages. If you publish a message and there are no subscribers, the message is permanently lost. This is fine for your use case because the WebSocket handler subscribes before the worker can possibly publish (the worker has to wait for the RabbitMQ delivery and then run the RAG pipeline — that's several seconds minimum). The buffer handles the edge cases.

### One Channel Per Job

Using `rag_stream:{job_id}` with a UUID per request means:
- Two users asking questions simultaneously get completely separate channels.
- There is no risk of User A receiving User B's answer.
- Old channels from past requests are simply ignored (no subscribers, so publishing is a no-op).

### Publish Connection Pool vs Subscribe Connections

The `_publish_client` uses a connection pool (shared, reused). Each subscription creates its own dedicated connection. This asymmetry is intentional:

- **Publish** can share connections — it is one-shot, stateless, and safe to pool.
- **Subscribe** cannot share connections — a subscribed connection is in a special mode and cannot do anything else. Each WebSocket handler needs its own private connection.

### `asyncio.to_thread()` in the WebSocket Handler

The `collect_job_response()` function uses a blocking poll (`get_message`) inside a while loop. If you called this directly in an `async` function, it would freeze FastAPI's entire event loop. The WebSocket endpoint uses `asyncio.to_thread()` to run this blocking function in a separate thread, keeping the event loop free to handle other requests.

```python
# websocket.py
result = await asyncio.to_thread(
    pubsub_service.collect_job_response,
    job_id,
    WEBSOCKET_RESPONSE_TIMEOUT,
)
```

### What if the WebSocket disconnects before the result arrives?

The `finally` block in `collect_job_response` always calls `unsubscribe()`. If the WebSocket handler catches a `WebSocketDisconnect` exception, execution falls through to the `finally` block and the Redis subscription is cleanly closed. No leaked connections.
