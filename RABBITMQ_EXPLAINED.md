# RabbitMQ — Complete Explanation

> **Focus**: What is RabbitMQ, why your project uses it, how the code is structured,
> and what every function does — explained in plain language with supporting code snippets.

---

## File Reference Index

Every piece of code in this document comes from one of these files in your project.
Whenever you see a code block, the file path is shown above it.

| File | Role |
|---|---|
| `backend/app/config.py` | All RabbitMQ connection settings (host, port, queue name, credentials) |
| `backend/app/services/rabbitmq_service.py` | `RabbitMQService` class — the full wrapper around pika |
| `backend/app/routers/chat.py` | `queue_message()` endpoint — the producer that puts jobs into the queue |
| `backend/app/worker/chat_worker.py` | `ChatWorker` class — the consumer that processes jobs |
| `backend/app/main.py` | Application startup — where the worker thread is launched |
| `frontend/services/api.ts` | `queueMessage()` — the frontend function that calls the queue endpoint |

---

## Table of Contents

1. [What is RabbitMQ and Why Do You Need It?](#1-what-is-rabbitmq-and-why-do-you-need-it)
2. [How RabbitMQ Works — The Core Idea](#2-how-rabbitmq-works)
3. [Where RabbitMQ Lives in Your Project](#3-where-rabbitmq-lives-in-your-project)
4. [The Complete Flow — From Browser to Worker](#4-the-complete-flow)
5. [RabbitMQService Class — File by File](#5-rabbitmqservice-class)
6. [The Queue Endpoint — chat.py](#6-the-queue-endpoint)
7. [The ChatWorker — chat_worker.py](#7-the-chatworker)
8. [Configuration Settings](#8-configuration-settings)
9. [Key Concepts You Should Know](#9-key-concepts)

---

## 1. What is RabbitMQ and Why Do You Need It?

### The Problem Without a Queue

Imagine two kinds of user questions your chatbot can receive:

- **"What are your opening hours?"** — This matches an FAQ. Your code looks it up in Redis or the database and replies in under 100 milliseconds. Fast.
- **"Can you explain what section 4.2 of the contract says about penalties?"** — This needs RAG (searching your PDF documents with AI). The AI model needs to embed the question, search thousands of vector chunks, and generate a response. This takes **3 to 10 seconds**.

If your HTTP endpoint just waited those 10 seconds before responding, the user would stare at a loading spinner, the browser might time out, and you could only handle one RAG request at a time because the entire server thread is blocked waiting.

### The Solution: A Queue

A queue lets you say: *"I've received your request, I've written it down, here is a ticket number, goodbye — you'll hear back soon."* The actual work happens separately, in the background. The user gets an instant response and then waits for the real answer via WebSocket.

RabbitMQ is a **message broker** — a program that stores these "tasks" (called messages) in an ordered list (called a queue) and delivers them to workers one at a time.

```
Without queue:
  Browser waits 10 seconds ──────────────────────────────► GET response

With queue:
  Browser gets ticket (0.05s) ──► Worker processes (10s) ──► WebSocket delivers answer
```

---

## 2. How RabbitMQ Works

### The Three Actors

| Actor | Role in Your Project |
|---|---|
| **Producer** | The FastAPI endpoint (`POST /chat/message/queue`) that puts jobs into the queue |
| **Broker** | The RabbitMQ server itself — holds the queue and delivers messages |
| **Consumer** | The `ChatWorker` thread that picks up jobs and processes them |

### Key Terms Used in Your Code

**Queue**: A named list of messages. Your queue is called `rag_processing_queue`. Messages arrive in order and each message is delivered to exactly one consumer.

**Exchange**: The routing layer in front of queues. Your code uses the default exchange (`""`), which means messages go directly to the queue named in the routing key — the simplest setup.

**Durable Queue**: A queue that survives a RabbitMQ restart. Your queue is declared durable so jobs are never lost if the server reboots.

**Persistent Message**: A message stored to disk by RabbitMQ. Your messages use `delivery_mode=2` which means they survive a broker restart even while sitting in the queue waiting to be consumed.

**Prefetch Count**: How many unacknowledged messages a consumer can hold at once. Your value is `1`, meaning the ChatWorker processes one job completely before it asks for the next — this prevents a slow job from creating a backlog.

**Acknowledge (ACK)**: After successfully processing a message, the consumer sends an ACK. RabbitMQ then removes the message from the queue permanently.

**Negative Acknowledge (NACK)**: If processing fails, the consumer sends a NACK. RabbitMQ can then re-deliver the message to another consumer or put it back in the queue.

---

## 3. Where RabbitMQ Lives in Your Project

```
backend/
  app/
    services/
      rabbitmq_service.py      ← The RabbitMQ connection and messaging logic
    worker/
      chat_worker.py           ← The consumer that processes jobs
    routers/
      chat.py                  ← The producer (publishes jobs)
    config.py                  ← All RabbitMQ settings (host, port, queue name)
```

The flow of responsibility is:

1. `config.py` holds all connection settings read from the `.env` file.
2. `rabbitmq_service.py` provides a reusable class that wraps the pika library (the Python RabbitMQ client). Any part of the app that needs to send or receive messages uses this class.
3. `chat.py` is the producer — it calls `rabbitmq_service.publish_message()` when a RAG job needs to be queued.
4. `chat_worker.py` is the consumer — it calls `rabbitmq_service.consume_messages()` in a background thread, processing each job as it arrives.

---

## 4. Code Flow Trace — Every Function Call in Order

This trace shows the exact function name, the file it lives in, and what it does — in the order they execute for one RAG request.

```
[1] BROWSER
    frontend/services/api.ts
    → queueMessage(sessionId, message)
      Sends POST /chat/message/queue with { session_id, message }
      Returns a promise that resolves with job_id + queued flag

[2] FASTAPI ENDPOINT
    backend/app/routers/chat.py
    → queue_message(request, db, faq_service)
      Generates a UUID job_id
      Calls check_sync_response() first

[3] SYNC CHECK — WORKFLOW
    backend/app/services/chat_service.py
    → check_sync_response(session_id, user_message, db, faq_service)
      Internally calls _find_node_by_text()       ← workflow node lookup
      Internally calls faq_service.get_faq_response() ← Redis cache + DB
      Returns (response, options) or (None, None) if no match

[4] IF NO SYNC MATCH → ENQUEUE
    backend/app/routers/chat.py  (still inside queue_message)
    → rabbitmq_service.publish_message(job_payload)
      Publishes { job_id, session_id, user_message } to RabbitMQ
      Returns True/False
      Endpoint responds HTTP 202 { job_id, queued: true }

[5] RABBITMQ BROKER
    Holds the message in rag_processing_queue until worker picks it up

[6] CHATWORKER PICKS UP JOB
    backend/app/worker/chat_worker.py
    → ChatWorker._process_job(message)
      Extracts job_id, session_id, user_message from the dict
      Calls _get_db_session() to open a fresh DB session

[7] RAG PIPELINE
    backend/app/services/chat_service.py
    → process_rag_message(session_id, user_message, db)
      Internally calls _find_rag_response()  ← vector search + LLM
      Saves messages to DB
      Returns (bot_response, next_options, session)

[8] PUBLISH RESULT
    backend/app/worker/chat_worker.py
    → ChatWorker._publish_response(job_id, session_id, payload)
      Calls pubsub_service.publish("rag_stream:{job_id}", payload)
      Redis delivers to subscribed WebSocket handler

[9] WEBSOCKET DELIVERS TO BROWSER
    backend/app/routers/websocket.py
    → websocket_chat() sends the JSON to the browser
```

---

## 5. The Complete Flow — From Browser to Worker

Here is the step-by-step journey of one RAG request:

### Step 1 — Browser Sends Chat Message

The user types a question that doesn't match any workflow node or FAQ. The browser calls `POST /chat/message/queue`.

📄 **File**: `frontend/services/api.ts` — function `queueMessage()`

```typescript
// 📄 frontend/services/api.ts
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
}
```

This function:
- Sends `POST /chat/message/queue` with `session_id` and `message` in the body
- Returns the full response including `job_id`, `queued`, `cache_hit`, and optionally `bot_response`
- If `cache_hit` is `true`, the answer is already in the response — no WebSocket needed
- If `queued` is `true`, the browser must open a WebSocket with the returned `job_id`

### Step 2 — FastAPI Checks Fast Paths First

📄 **File**: `backend/app/routers/chat.py` — function `queue_message()`

The endpoint first checks if the message can be answered without queueing. It calls `check_sync_response()` which runs the workflow node check and FAQ cache check synchronously. These are instant (milliseconds).

If neither matches, it proceeds to queue the job.

### Step 3 — Job is Published to RabbitMQ

📄 **File**: `backend/app/routers/chat.py` → calls `backend/app/services/rabbitmq_service.py`

The endpoint creates a job dictionary with a unique UUID, the session ID, and the user's message, then calls `rabbitmq_service.publish_message()`. This writes the job to the `rag_processing_queue` and returns in milliseconds.

The endpoint immediately responds with HTTP 202 (Accepted) and the `job_id`.

### Step 4 — Browser Opens WebSocket

📄 **File**: `frontend/services/api.ts` → connects to `backend/app/routers/websocket.py`

The browser, having received `queued: true` and a `job_id`, opens a WebSocket connection to `/ws/chat/{session_id}/{job_id}` and waits.

### Step 5 — ChatWorker Picks Up the Job

📄 **File**: `backend/app/worker/chat_worker.py` — function `_process_job()`

The `ChatWorker` is running in a background thread started when FastAPI launched. It is blocked on `basic_consume`, waiting for messages. RabbitMQ delivers the job to it.

### Step 6 — RAG Pipeline Runs

📄 **File**: `backend/app/worker/chat_worker.py` → calls `backend/app/services/chat_service.py`

The ChatWorker calls `process_rag_message()` with the user's message. This searches your PDF vectors in Milvus, retrieves relevant chunks, and asks the LLM (Groq/LLaMA) to synthesize an answer. This is the slow part (seconds).

### Step 7 — Result Published to Redis

📄 **File**: `backend/app/worker/chat_worker.py` → calls `backend/app/services/redis_pubsub_service.py`

Once the ChatWorker has the answer, it calls `_publish_response()` which calls `pubsub_service.publish()`. The WebSocket endpoint picks it up and sends it to the browser.

---

## 6. RabbitMQService Class — Full Function Reference

📄 **File**: `backend/app/services/rabbitmq_service.py`

### Function Reference Table

| Function | Parameters | Returns | Purpose |
|---|---|---|---|
| `__init__()` | none | — | Initialize internal state, no connection yet |
| `connect()` | none | `bool` | Open TCP connection + channel to broker |
| `disconnect()` | none | `None` | Gracefully close channel and connection |
| `is_available()` | none | `bool` | Check if connection and channel are both open |
| `health_check()` | none | `bool` | Send a lightweight ping to verify broker is alive |
| `publish_message()` | `message: Dict`, `queue_name: str` (optional), `priority: int` (default 0) | `bool` | JSON-serialize and publish one message to the queue |
| `consume_messages()` | `callback: Callable`, `queue_name: str` (optional), `prefetch_count: int` (default 1) | `None` (blocks forever) | Start the consumer loop — calls `callback` for every message |

---

### Imports at the Top of the File

These are the actual imports used in `rabbitmq_service.py`:

```python
# 📄 backend/app/services/rabbitmq_service.py  — imports section
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
```

Key libraries:
- `pika` — the official Python AMQP client for RabbitMQ
- `threading.Lock` — used inside `publish_message()` to prevent race conditions
- All the `RABBITMQ_*` constants come from `config.py` which reads your `.env` file

This class is a wrapper around `pika` (the Python RabbitMQ client library). It handles all the low-level details — connection management, JSON serialization, error recovery — and exposes a clean interface to the rest of the app.

---

### `__init__(self)` — Constructor

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Line in file**: Class constructor inside `class RabbitMQService`

**Function signature**: `def __init__(self) -> None`
**What it does**: Initializes all internal instance variables to safe empty/False values. Does NOT connect to RabbitMQ — connection is deferred to an explicit `connect()` call.

```python
# 📄 backend/app/services/rabbitmq_service.py
class RabbitMQService:
    def __init__(self):
        """Initialize RabbitMQ service (does not connect immediately)."""
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._lock = threading.Lock()   # thread-safety for publish calls
        self._connected = False         # tracks whether connect() succeeded
```

**Variables explained**:
- `_connection` — the pika TCP connection object (None until `connect()` is called)
- `_channel` — the AMQP channel used to publish and consume (created from `_connection`)
- `_lock` — a threading mutex; prevents two threads publishing at the same time
- `_connected` — a boolean flag; `True` only after a successful `connect()`

**Why not connect in `__init__`?** Because connection failure at startup would crash the service. Instead, `connect()` is called explicitly, so failures can be caught and handled gracefully.

---

### `connect(self) -> bool` — Establish Connection to Broker

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def connect(self) -> bool`
**Returns**: `True` if connection succeeded, `False` if it failed (never raises an exception)
**What it does**: Opens a TCP connection to the RabbitMQ broker, creates an AMQP channel, then verifies the queue exists (or creates it if not).

```python
# 📄 backend/app/services/rabbitmq_service.py  — connect() method
def connect(self) -> bool:
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=RABBITMQ_HEARTBEAT,                     # 60 seconds
            blocked_connection_timeout=RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,  # 300 seconds
        )

        self._connection = pika.BlockingConnection(parameters)
        self._channel   = self._connection.channel()
        # Flush any pending events so the channel is fully ready before use
        self._connection.process_data_events()

        # Check if queue already exists without modifying its parameters
        try:
            self._channel.queue_declare(
                queue=RABBITMQ_QUEUE_NAME,
                passive=True,          # only check existence, don't create
            )
        except pika.exceptions.ChannelClosedByBroker:
            # Queue doesn't exist yet — re-open channel and declare it fresh
            self._channel = self._connection.channel()
            self._channel.queue_declare(
                queue=RABBITMQ_QUEUE_NAME,
                durable=True,          # queue survives broker restart
            )

        self._connected = True
        return True

    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
        self._connected = False
        return False

    except Exception as e:
        logger.error(f"❌ Unexpected error connecting to RabbitMQ: {e}")
        self._connected = False
        return False
```

**What `heartbeat=60` does**: RabbitMQ and pika exchange a tiny "I'm still here" packet every 60 seconds. Without this, a broken TCP connection might not be detected for minutes, and messages would silently fail.

**What `blocked_connection_timeout=300` does**: If RabbitMQ is overloaded and blocks the Publisher, this setting makes the connection throw an exception after 5 minutes instead of hanging forever.

After opening the connection, `connect()` tries to verify the queue exists using `passive=True`:

```python
try:
    self._channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, passive=True)
    # passive=True: "I just want to check it exists, don't create or modify it"
except pika.exceptions.ChannelClosedByBroker:
    # Queue doesn't exist yet — create it fresh
    self._channel = self._connection.channel()
    self._channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True)
```

**Why `passive=True` first?** If the queue was previously created with extra parameters (like a message TTL), trying to redeclare it with different parameters would cause a `PRECONDITION_FAILED` error and crash the channel. Using passive avoids any conflict.

**Return value**: `True` if connection succeeded, `False` if it failed (logs the error but does not raise an exception).

---

### `disconnect(self) -> None` — Close Connection Gracefully

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def disconnect(self) -> None`
**Returns**: Nothing
**What it does**: Closes the AMQP channel first, then the TCP connection. Resets all internal state variables so `is_available()` returns `False` afterwards.

```python
# 📄 backend/app/services/rabbitmq_service.py  — disconnect() method
def disconnect(self) -> None:
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
        # Always reset — even if close() threw an error
        self._channel    = None
        self._connection = None
        self._connected  = False
```

The channel must be closed before the connection — closing the connection while the channel is still open can cause errors. The `finally` block guarantees the internal state is always cleaned up.

---

### `is_available(self) -> bool` — Check If Connection Is Alive

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def is_available(self) -> bool`
**Returns**: `True` if connection and channel are both alive and open, `False` otherwise
**What it does**: Checks all four conditions required for safe publishing/consuming. Called at the top of `publish_message()` and `consume_messages()` before doing any work.

```python
# 📄 backend/app/services/rabbitmq_service.py  — is_available() method
def is_available(self) -> bool:
    return (
        self._connected                        # connect() was called and succeeded
        and self._connection is not None       # connection object exists
        and self._connection.is_open           # TCP socket is still alive
        and self._channel is not None          # channel object exists
        and self._channel.is_open              # channel is alive (not closed by broker)
    )
```

All four must be true. If any one fails, the method returns `False` and the caller knows it needs to reconnect. This is checked:
- At the start of `publish_message()` — if False, tries to reconnect before publishing
- At the start of `consume_messages()` — if False, tries to reconnect before subscribing

---

### `health_check(self) -> bool` — Lightweight Liveness Probe

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def health_check(self) -> bool`
**Returns**: `True` if RabbitMQ is alive and responding, `False` otherwise
**What it does**: Calls `process_data_events()` on the open connection. If that call returns without error, the connection is healthy.

```python
# 📄 backend/app/services/rabbitmq_service.py  — health_check() method
def health_check(self) -> bool:
    if not self.is_available():
        return False
    try:
        # process_data_events() flushes any pending I/O and also ticks the heartbeat
        self._connection.process_data_events()
        return True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
        return False
```

`process_data_events()` processes any pending I/O on the connection without blocking. It also serves as a heartbeat tick, keeping the connection alive. If this call throws an exception, the connection is dead.

This is useful for `/health` endpoints that report whether all services are up.

---

### `publish_message(self, message, queue_name, priority) -> bool` — Put a Job Into the Queue

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def publish_message(self, message: Dict[str, Any], queue_name: Optional[str] = None, priority: int = 0) -> bool`
**Parameters**:
- `message` — Python dict to serialize as JSON and send
- `queue_name` — target queue (defaults to `RABBITMQ_QUEUE_NAME` from config)
- `priority` — message priority 0–9 (default 0, only used if queue has priority enabled)

**Returns**: `True` if published successfully, `False` if failed after retry
**What it does**: JSON-serializes the message dict and publishes it to RabbitMQ. Uses a thread lock for safety. Auto-reconnects and retries once if the connection was stale.

```python
# 📄 backend/app/services/rabbitmq_service.py  — publish_message() method
def publish_message(
    self,
    message: Dict[str, Any],
    queue_name: Optional[str] = None,
    priority: int = 0,
) -> bool:
    target_queue = queue_name or RABBITMQ_QUEUE_NAME

    # ── Check connection, auto-reconnect if needed ───────────────────────────
    if not self.is_available():
        logger.warning("RabbitMQ not available. Attempting reconnect before publish...")
        if not self.connect():
            logger.error("❌ Reconnect failed. Message not published.")
            return False

    try:
        with self._lock:        # ← thread lock: only one thread publishes at a time
            body = json.dumps(message)
            self._channel.basic_publish(
                exchange=RABBITMQ_EXCHANGE,      # "" = default exchange (direct routing)
                routing_key=target_queue,        # queue name acts as routing key
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,             # 2 = persistent (survives broker restart)
                    content_type="application/json",
                    priority=priority,
                ),
            )
        logger.debug(f"📤 Published message to '{target_queue}': {message}")
        return True

    except pika.exceptions.AMQPError as e:
        # ── Stale connection detected — reconnect and retry ONCE ─────────────
        logger.warning(f"⚠️ Publish failed (stale connection): {e}. Reconnecting...")
        self._connected = False
        if not self.connect():
            logger.error(f"❌ Reconnect failed. Message not published.")
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
```

**Why `with self._lock`?** Multiple FastAPI request threads could all call `publish_message` at the same time. The `pika` library is not thread-safe, so the lock ensures only one thread writes to the channel at a time.

**Why the retry logic?** There is a race condition: `is_available()` returns `True` but by the time `basic_publish` runs, the TCP connection has dropped (e.g., network hiccup). The catch + reconnect + retry pattern handles this gracefully without requiring the caller to retry manually.

**`delivery_mode=2`** makes the message persistent — RabbitMQ writes it to disk. If the broker restarts while the message is waiting in the queue, the message survives and will still be delivered to the worker eventually.

---

### `consume_messages(self, callback, queue_name, prefetch_count) -> None` — Start the Worker Loop

📄 **File**: `backend/app/services/rabbitmq_service.py`
**Function signature**: `def consume_messages(self, callback: Callable[[Dict[str, Any]], None], queue_name: Optional[str] = None, prefetch_count: int = 1) -> None`
**Parameters**:
- `callback` — function to call with each deserialized message dict; called once per message
- `queue_name` — queue to consume from (defaults to `RABBITMQ_QUEUE_NAME`)
- `prefetch_count` — max unacknowledged messages at once (default 1 = process one at a time)

**Returns**: Nothing — this function **blocks forever**
**What it does**: Starts the consumer loop. For every message RabbitMQ delivers, it JSON-deserializes the body and calls `callback(message)`. Handles ACK/NACK automatically.

```python
# 📄 backend/app/services/rabbitmq_service.py  — consume_messages() method
def consume_messages(
    self,
    callback: Callable[[Dict[str, Any]], None],
    queue_name: Optional[str] = None,
    prefetch_count: int = 1,
) -> None:
    target_queue = queue_name or RABBITMQ_QUEUE_NAME

    if not self.is_available():
        if not self.connect():
            logger.error("❌ Cannot start consumer: RabbitMQ connection unavailable.")
            return

    # ── Rate limiting: only accept one unacknowledged message at a time ───────
    self._channel.basic_qos(prefetch_count=prefetch_count)

    def _on_message(ch, method, properties, body):
        """Internal callback: deserialize body and call user callback."""
        try:
            message = json.loads(body)        # bytes → Python dict
            logger.debug(f"📥 Received message from '{target_queue}': {message}")

            callback(message)                 # ← call ChatWorker._process_job()

            # ── Tell RabbitMQ: job done, remove from queue ──────────────────
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode message body: {e}")
            # Malformed JSON — discard forever (do NOT requeue)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"❌ Callback error: {e}", exc_info=True)
            # Worker error — requeue so another worker can retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    self._channel.basic_consume(
        queue=target_queue,
        on_message_callback=_on_message,
    )

    logger.info(f"🎧 Starting consumer on '{target_queue}' (prefetch={prefetch_count})")
    self._channel.start_consuming()   # ← BLOCKS HERE — runs until connection drops
```

**How `prefetch_count=1` helps**: Without prefetch limiting, RabbitMQ would push all pending messages to the worker at once. With `prefetch_count=1`, RabbitMQ only sends the next message after the previous one has been acknowledged. This prevents one slow job from starving everything else and keeps memory usage stable.

**The three outcomes of `_on_message`**:

| What happened | Action | RabbitMQ effect |
|---|---|---|
| Success | `basic_ack` | Message deleted from queue |
| Message is malformed JSON | `basic_nack(requeue=False)` | Message discarded (dead lettered) |
| Worker code threw an exception | `basic_nack(requeue=True)` | Message goes back to queue, will retry |

---

## 7. The Queue Endpoint — Producer Side

📄 **File**: `backend/app/routers/chat.py`
**Endpoint**: `POST /chat/message/queue`
**HTTP Status**: 202 Accepted (not 200 — means "received but not yet processed")

### All Imports Used in chat.py

```python
# 📄 backend/app/routers/chat.py  — imports section
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from app.schemas.chat import (
    ChatStartRequest, ChatStartResponse,
    ChatMessageRequest, ChatMessageResponse,
    ChatQueueRequest, ChatQueueResponse,
    TriggerNodeOption, NodeOption,
)
from app.services.chat_service import start_chat_session, process_message, check_sync_response
from app.services.faq_service import FAQService
from app.dependencies.cache import get_faq_service
from app.logging_config import get_logger
```

### Function: `queue_message()` — The Producer

**Function signature**: `def queue_message(request: ChatQueueRequest, db: Session = Depends(get_db), faq_service: FAQService = Depends(get_faq_service))`
**What it does**: Checks workflow/FAQ first (instant). If nothing matches, publishes a job to RabbitMQ and returns 202.

```python
# 📄 backend/app/routers/chat.py  — queue_message() endpoint
@router.post("/message/queue", response_model=ChatQueueResponse, status_code=202)
def queue_message(request, db, faq_service):
    job_id = str(uuid.uuid4())   # unique ID for this job

    # ── Fast path: check workflow nodes and FAQ cache ──────────────────────
    sync_response, sync_options = check_sync_response(
        session_id=request.session_id,
        user_message=request.message,
        db=db,
        faq_service=faq_service,
    )

    if sync_response is not None:
        # Got an answer immediately — no queue needed
        return ChatQueueResponse(
            job_id=job_id,
            queued=False,
            cache_hit=True,
            bot_response=sync_response,
            options=sync_options,
        )

    # ── Slow path: RAG needed — enqueue the job ────────────────────────────
    job_payload = {
        "job_id":       job_id,
        "session_id":   request.session_id,
        "user_message": request.message,
    }
    published = rabbitmq_service.publish_message(job_payload)

    if not published:
        raise HTTPException(503, "Messaging service unavailable.")

    return ChatQueueResponse(
        job_id=job_id,
        session_id=request.session_id,
        queued=True,
        cache_hit=False,
    )
```

The response the browser receives has two possible shapes:

**Shape 1 — Answered instantly (no queue)**:
```json
{
  "job_id": "550e8400-...",
  "queued": false,
  "cache_hit": true,
  "bot_response": "Our opening hours are 9am–5pm Monday to Friday.",
  "options": []
}
```

**Shape 2 — Queued for RAG processing**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": 42,
  "queued": true,
  "cache_hit": false
}
```

The browser checks `queued`. If `true`, it opens a WebSocket and waits for the result.

---

## 8. The ChatWorker — Consumer Side

📄 **File**: `backend/app/worker/chat_worker.py`

The ChatWorker is the consumer. It runs in a background daemon thread, permanently waiting for jobs from RabbitMQ.

### All Imports Used in chat_worker.py

```python
# 📄 backend/app/worker/chat_worker.py  — imports section
import logging
import threading
from typing import Any, Dict, Optional

from app.config import WORKER_PREFETCH_COUNT
from app.services.rabbitmq_service import RabbitMQService
from app.services.redis_pubsub_service import RedisPubSubService, get_redis_pubsub_service
from database import SessionLocal
```

### Function Reference Table for ChatWorker

| Function | Parameters | Returns | Purpose |
|---|---|---|---|
| `__init__()` | `rabbitmq_service`, `pubsub_service` (both optional) | — | Wire up RabbitMQ + Redis services |
| `_get_db_session()` | none | `Session` | Create a fresh SQLAlchemy database session |
| `_publish_response()` | `job_id`, `session_id`, `payload: Dict` | `bool` | Publish result to Redis Pub/Sub channel |
| `_process_job()` | `message: Dict` | `None` | Main logic: validate → RAG → publish result |
| `start()` | none | `None` (blocks) | Connect to RabbitMQ, start consuming loop |

---

### `__init__(self, rabbitmq_service, pubsub_service)` — Setup

📄 **File**: `backend/app/worker/chat_worker.py`
**What it does**: Stores references to the RabbitMQ service (for consuming) and Redis Pub/Sub service (for publishing results). Uses dependency injection so both can be replaced with mocks in tests.

```python
# 📄 backend/app/worker/chat_worker.py  — __init__() method
def __init__(
    self,
    rabbitmq_service: Optional[RabbitMQService] = None,
    pubsub_service:   Optional[RedisPubSubService] = None,
):
    # RabbitMQ consumer — picks up jobs from the queue
    self._rabbitmq = rabbitmq_service or RabbitMQService()

    # Redis Pub/Sub publisher — sends results to WebSocket handlers
    self._pubsub: RedisPubSubService = pubsub_service or get_redis_pubsub_service()

    self._running = False                        # is the worker main loop active?
    self._thread: Optional[threading.Thread] = None  # reference to worker thread
```

The worker holds a reference to both the RabbitMQ service (to consume jobs) and the Redis Pub/Sub service (to publish results back). Both are injected as parameters — this makes the worker testable (you can pass mock services in tests).

---

### `_get_db_session(self)` — Database Session

📄 **File**: `backend/app/worker/chat_worker.py`
**Function signature**: `def _get_db_session(self) -> Session`
**Returns**: A new SQLAlchemy `Session` object
**What it does**: Opens a raw database connection. The caller must close it in a `finally` block.

```python
# 📄 backend/app/worker/chat_worker.py  — _get_db_session() method
def _get_db_session(self):
    """Create and return a new SQLAlchemy database session.
    Caller is responsible for closing it.
    """
    return SessionLocal()  # SessionLocal is imported from database.py
```

The worker needs its own database sessions. It **cannot** use FastAPI's `Depends(get_db)` because it runs outside the request lifecycle — there is no HTTP request, so there is no request context. `SessionLocal()` creates a raw SQLAlchemy session directly.

The caller (`_process_job`) closes it in a `finally` block so the connection is always returned to the pool.

---

### `_publish_response(self, job_id, session_id, payload)` — Send Result to Redis

📄 **File**: `backend/app/worker/chat_worker.py`
**Function signature**: `def _publish_response(self, job_id: str, session_id: int, payload: Dict[str, Any]) -> bool`
**Parameters**:
- `job_id` — the UUID for this job; used to name the Redis channel
- `session_id` — the chat session ID (included in the published payload)
- `payload` — the full result dict to publish

**Returns**: `True` if published, `False` if Redis is unavailable
**What it does**: Constructs the channel name `rag_stream:{job_id}` and calls `redis_pubsub_service.publish()`. The WebSocket endpoint subscribed to this channel receives the message instantly.

```python
# 📄 backend/app/worker/chat_worker.py  — _publish_response() method
def _publish_response(self, job_id: str, session_id: int, payload: Dict[str, Any]) -> bool:
    # Channel name matches what websocket.py subscribes to
    channel = f"rag_stream:{job_id}"
    published = self._pubsub.publish(channel, payload)
    # pubsub.publish() is defined in:
    #   backend/app/services/redis_pubsub_service.py → RedisPubSubService.publish()
    return published
```

After processing a job, the result is published to a Redis channel. The channel name uses the unique `job_id`, so each job has its own dedicated channel. The WebSocket endpoint subscribed to this channel is waiting for exactly this message.

---

### `_process_job(self, message)` — Core Processing Logic

📄 **File**: `backend/app/worker/chat_worker.py`
**Function signature**: `def _process_job(self, message: Dict[str, Any]) -> None`
**Parameters**: `message` — the deserialized dict consumed from RabbitMQ
**Returns**: Nothing — result is published to Redis
**What it does**: The main brain of the worker. Validates input, opens a DB session, runs the RAG pipeline, publishes a success or error payload to Redis. ALWAYS publishes something so the WebSocket never hangs.

This is the function that is passed as the `callback` to `rabbitmq_service.consume_messages()`.

```python
def _process_job(self, message: Dict) -> None:
    job_id       = message.get("job_id", "unknown")
    session_id   = message.get("session_id")
    user_message = message.get("user_message", "")

    # ── Validate input ───────────────────────────────────────────────────────
    if not session_id or not user_message:
        # Publish an error so the WebSocket doesn't hang forever
        self._publish_response(job_id, session_id, {
            "status": "error",
            "response": "Invalid job payload.",
            "is_done": True,
        })
        return

    db = None
    try:
        db = self._get_db_session()

        # ── Run RAG pipeline ─────────────────────────────────────────────────
        from app.services.chat_service import process_rag_message
        bot_response, next_options, _ = process_rag_message(
            session_id=session_id,
            user_message=user_message,
            db=db,
        )

        # ── Publish success ──────────────────────────────────────────────────
        self._publish_response(job_id, session_id, {
            "job_id":       job_id,
            "session_id":   session_id,
            "response":     bot_response,
            "next_options": next_options,
            "status":       "success",
            "is_done":      True,
        })

    except Exception as e:
        # ── Publish error so WebSocket doesn't hang ──────────────────────────
        self._publish_response(job_id, session_id, {
            "job_id":   job_id,
            "session_id": session_id,
            "response": "An error occurred while processing your request.",
            "status":   "error",
            "is_done":  True,
        })
    finally:
        if db:
            db.close()
```

**The most important guarantee**: The worker ALWAYS publishes a result — either success or error. This means the WebSocket endpoint will NEVER hang waiting for a message that never comes. Even if the RAG pipeline crashes, the browser receives an error message and can show the user a helpful message instead of a frozen UI.

---

### How the Worker is Started

📄 **File**: `backend/app/main.py` — application startup event

```python
# 📄 backend/app/main.py  — startup event (runs once when FastAPI starts)
@app.on_event("startup")
async def startup_event():
    # ... other startup tasks (DB tables, Redis check) ...

    # Start the ChatWorker in a background daemon thread
    from app.worker.chat_worker import ChatWorker
    worker = ChatWorker()                                  # creates RabbitMQ + Redis connections
    thread = threading.Thread(target=worker.start, daemon=True)
    thread.start()
    logger.info("ChatWorker started in background thread")
```

`daemon=True` means this thread will be automatically killed when the main FastAPI process exits. You don't need to manually stop it on shutdown. If FastAPI restarts, the worker thread restarts too.

---

## 9. Configuration Settings

📄 **File**: `backend/app/config.py` — RabbitMQ section

```python
# 📄 backend/app/config.py  — RabbitMQ configuration block

# ============================================================================
# RabbitMQ Configuration
# ============================================================================
RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "localhost")   # broker hostname
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", "5672"))   # AMQP port
RABBITMQ_USER  = os.getenv("RABBITMQ_USER", "guest")       # broker username
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASS", "guest")       # broker password
RABBITMQ_QUEUE_NAME  = os.getenv("RABBITMQ_QUEUE_NAME", "rag_processing_queue")
RABBITMQ_EXCHANGE    = ""    # default exchange = direct routing (no fanout)
RABBITMQ_HEARTBEAT   = 60   # seconds between heartbeat packets
RABBITMQ_BLOCKED_CONNECTION_TIMEOUT = 300  # seconds before timeout if broker blocked

# Worker Configuration
WORKER_PREFETCH_COUNT = int(os.getenv("WORKER_PREFETCH_COUNT", "1"))
# 1 = process one message at a time before asking for the next
```

| Setting | Default | What it controls |
|---|---|---|
| `RABBITMQ_HOST` | `localhost` | Broker server address |
| `RABBITMQ_PORT` | `5672` | AMQP protocol port |
| `RABBITMQ_USER` | `guest` | Broker login username |
| `RABBITMQ_PASS` | `guest` | Broker login password |
| `RABBITMQ_QUEUE_NAME` | `rag_processing_queue` | Name of the job queue |
| `RABBITMQ_EXCHANGE` | `""` | Empty = default exchange (direct) |
| `RABBITMQ_HEARTBEAT` | `60` | Seconds between heartbeat packets |
| `RABBITMQ_BLOCKED_CONNECTION_TIMEOUT` | `300` | Timeout if broker is overloaded |
| `WORKER_PREFETCH_COUNT` | `1` | Messages in flight per consumer |

---

## 10. Key Concepts

### Why daemon=True for the worker thread?

A daemon thread is a background thread that does not prevent the Python process from exiting. If you used a non-daemon thread and someone pressed Ctrl+C to stop FastAPI, the process would hang waiting for the `start_consuming()` loop to finish (which it never would on its own). Daemon threads are killed automatically.

### What happens if RabbitMQ is down?

The `is_available()` check at the start of `publish_message()` will return `False`. The method tries to reconnect once. If reconnection fails, it returns `False` to the caller, and the REST endpoint raises HTTP 503 (Service Unavailable). The browser receives that error and can show a "please try again" message. No message is lost because nothing was ever written — the user can simply retry.

### What happens if the worker crashes mid-job?

Because the worker has not yet called `basic_ack()` on the message, RabbitMQ still considers the message "in-flight". When the connection drops (due to the crash), RabbitMQ re-queues the message and delivers it to the next available consumer (or the same worker when it restarts). This is the "at-least-once delivery" guarantee.

### Can you have multiple workers?

Yes. You can start multiple `ChatWorker` threads (or processes on different machines). Each one connects to RabbitMQ and calls `consume_messages`. RabbitMQ distributes messages in a round-robin fashion — each job goes to exactly one worker. With `prefetch_count=1`, load is balanced naturally: a slow worker gets fewer jobs because it acknowledges slowly.

### Job Message Format

Every message in the queue looks exactly like this:

```json
{
  "job_id":      "550e8400-e29b-41d4-a716-446655440000",
  "session_id":  42,
  "user_message": "What does section 4.2 say about penalties?"
}
```

And every result published back to Redis looks like this:

```json
{
  "job_id":       "550e8400-e29b-41d4-a716-446655440000",
  "session_id":   42,
  "response":     "Section 4.2 states that late penalties are calculated at 1.5% per month...",
  "next_options": [],
  "status":       "success",
  "is_done":      true
}
```
