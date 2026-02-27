# Advanced Distributed Chatbot System — Deep Learning Guide

> **Purpose:** After completing every file in this guide, you will be able to sit in front of your senior engineer and confidently explain every architectural decision, every data flow, every failure scenario, and every scaling strategy in this system. This is not surface-level documentation — it is a structured engineering study.

---

## What This System Does

This is a **production-grade, distributed AI chatbot platform** built with the following technology stack:

| Layer | Technology | Role |
|---|---|---|
| API Server | FastAPI (Python) | Handles HTTP requests, WebSocket, SSE |
| Message Queue | RabbitMQ | Decouples API from AI processing |
| Real-time Streaming | Redis Pub/Sub | Routes AI responses back to WebSocket clients |
| FAQ Caching | Redis (string keys) | Returns cached answers instantly without hitting AI |
| Authentication | JWT (JSON Web Tokens) | Stateless, secure user identity verification |
| AI Processing | OpenAI via Worker | Background consumer processes AI responses |
| RAG Pipeline | Milvus + LLM | Retrieval-Augmented Generation for smart answers |
| Persistence | PostgreSQL | Stores users, workflows, nodes, edges, sessions, messages |
| Object Storage | MinIO | Stores uploaded PDF files |
| Containerization | Docker + Compose | Single-command deployment of all services |

---

## Why Distributed Architecture?

When a user asks the chatbot a question, the answer requires calling OpenAI. That call can take **2 to 15 seconds**. If your API server blocks waiting for the AI response, every concurrent user request will stack up, exhaust your thread pool, and your server crashes.

**Distributed architecture solves this:**

```
User sends message  →  API returns immediately (job accepted)
                    →  Worker processes in background
                    →  Worker pushes result to Redis
                    →  WebSocket delivers result to user in real-time
```

The API server never blocks. The user experience is seamless.

---

## ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                                  │
│                                                                             │
│   HTTP POST /chat/message/queue     WS /ws/chat/{session_id}/{job_id}      │
└──────────────┬───────────────────────────────────┬──────────────────────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION SERVER                            │
│                                                                              │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │  Auth Router│  │  Chat Router     │  │  WebSocket Router            │   │
│  │  (JWT)      │  │  (POST /message) │  │  (WS /ws/chat/{id}/{job_id}) │   │
│  └─────────────┘  └────────┬─────────┘  └──────────────┬───────────────┘   │
│                             │                            │                   │
│                    ┌────────▼─────────┐      ┌──────────▼──────────────┐   │
│                    │  ChatService     │      │  RedisPubSubService     │   │
│                    │  ┌─────────────┐ │      │  subscribe(channel)     │   │
│                    │  │FAQ Cache Chk│ │      │  listen_once(timeout)   │   │
│                    │  │RabbitMQ Pub │ │      └─────────────────────────┘   │
│                    │  └─────────────┘ │                                     │
│                    └────────┬─────────┘                                     │
└─────────────────────────────┼─────────────────────────────────────────────-─┘
                              │
               ┌──────────────▼──────────────────────────────────────────────┐
               │                      MESSAGE QUEUE                          │
               │                                                             │
               │   ┌─────────────────────────────────────────────────────┐  │
               │   │                  RabbitMQ                           │  │
               │   │  Exchange: default (direct)                         │  │
               │   │  Queue: rag_processing_queue (durable, persistent)  │  │
               │   └──────────────────────────┬──────────────────────────┘  │
               └──────────────────────────────┼──────────────────────────────┘
                                              │
               ┌──────────────────────────────▼──────────────────────────────┐
               │                      CHAT WORKER                            │
               │                                                             │
               │   ┌─────────────────────────────────────────────────────┐  │
               │   │  ChatWorker (worker/chat_worker.py)                 │  │
               │   │  1. Consume job from RabbitMQ                       │  │
               │   │  2. Run RAG pipeline (Milvus + OpenAI)              │  │
               │   │  3. Publish result to Redis Pub/Sub                 │  │
               │   └──────────────────────────┬──────────────────────────┘  │
               └──────────────────────────────┼──────────────────────────────┘
                                              │
               ┌──────────────────────────────▼──────────────────────────────┐
               │                     REDIS                                   │
               │                                                             │
               │   ┌─────────────────────────┐  ┌───────────────────────┐   │
               │   │   Pub/Sub               │  │   Cache (FAQ/Session) │   │
               │   │   channel:              │  │   Key: faq:{hash}     │   │
               │   │   chat_response:{sid}   │  │   TTL: 3600s          │   │
               │   └─────────────────────────┘  └───────────────────────┘   │
               └──────────────────────────────────────────────────────────────┘
```

---

## Complete System Request Flow (Summary)

```
1.  User logs in  →  POST /auth/login  →  JWT token returned
2.  Frontend stores JWT in memory / localStorage
3.  User sends a chat message → POST /chat/message/queue (with JWT in header)
4.  Auth middleware validates JWT
5.  ChatService checks Redis FAQ cache → if HIT → return immediately
6.  If cache MISS → publish job to RabbitMQ queue → return job_id to client
7.  Frontend opens WebSocket → WS /ws/chat/{session_id}/{job_id}
8.  WebSocket handler subscribes to Redis channel chat_response:{session_id}
9.  ChatWorker (running in background) consumes job from RabbitMQ
10. Worker runs RAG pipeline → queries Milvus → calls OpenAI
11. Worker publishes result to Redis channel chat_response:{session_id}
12. WebSocket handler receives Redis message → sends to frontend via WebSocket
13. Frontend renders the AI response
14. WebSocket connection closes gracefully
```

---

## Guide File Index

| File | Topic | What You Will Learn |
|---|---|---|
| [1_system_architecture.md](1_system_architecture.md) | System Architecture | Why distributed, monolith vs distributed, data flow |
| [2_authentication_jwt.md](2_authentication_jwt.md) | JWT Authentication | Token structure, creation, verification, security |
| [3_rabbitmq_queue.md](3_rabbitmq_queue.md) | RabbitMQ Message Queue | Queue lifecycle, exchanges, ACK/NACK, durability |
| [4_worker_service.md](4_worker_service.md) | Chat Worker | Background processing, decoupling, error handling |
| [5_redis_pubsub_streaming.md](5_redis_pubsub_streaming.md) | Redis Pub/Sub | Streaming, channels, message bridging |
| [6_websocket_sse.md](6_websocket_sse.md) | WebSocket & SSE | Real-time delivery, lifecycle, disconnect handling |
| [7_redis_faq_cache.md](7_redis_faq_cache.md) | Redis FAQ Cache | Cache-first strategy, TTL, invalidation |
| [8_class_based_services_design.md](8_class_based_services_design.md) | Class-Based Design | Clean architecture, dependency injection, SOLID |
| [9_complete_request_flow.md](9_complete_request_flow.md) | End-to-End Flow | Full lifecycle trace from login to response render |
| [10_docker_and_deployment.md](10_docker_and_deployment.md) | Docker & Deployment | Containers, Compose, networking, environment vars |
| [11_scaling_and_production_considerations.md](11_scaling_and_production_considerations.md) | Scale & Production | Horizontal scaling, clustering, monitoring, security |

---

## Key Source File — Function Reference

This section lists every important function in the main referenced files so you know exactly what each file contains and what each function does before you dive into the topic files.

---

### `backend/app/main.py` — Application Entry Point

| Function / Event | What It Does |
|---|---|
| `startup_event()` | Runs once at app start: creates DB tables, initializes Redis cache and Pub/Sub services, logs readiness status |
| `shutdown_event()` | Runs once at app stop: gracefully closes Redis cache and Pub/Sub connections, logs shutdown |

**Routers registered inside `main.py`:** `auth`, `chatbots`, `workflows`, `nodes`, `edges`, `chat`, `faqs`, `upload`, `websocket`

---

### `backend/app/services/auth_service.py` — JWT and Password Utilities

| Function | What It Does |
|---|---|
| `hash_password(password)` | Hashes a plain-text password using bcrypt. Returns the bcrypt hash string to store in the database. |
| `verify_password(plain_password, hashed_password)` | Compares a plain-text input against a stored bcrypt hash. Returns `True` if they match, `False` otherwise. |
| `create_access_token(data, expires_delta)` | Builds a JWT payload with `sub`, `exp`, and `iat` claims, signs it with `SECRET_KEY` using HS256, and returns the encoded token string. |
| `decode_access_token(token)` | Decodes and verifies a JWT token using `SECRET_KEY`. Returns the payload dict on success, `None` if the token is invalid or expired. |

---

### `backend/app/services/rabbitmq_service.py` — RabbitMQ Producer/Consumer

| Method | What It Does |
|---|---|
| `__init__()` | Initializes the service with `None` connection/channel, a `threading.Lock`, and `_connected = False`. Does NOT connect yet. |
| `connect()` | Opens a `pika.BlockingConnection`, creates a channel, declares the durable queue (with passive-check fallback), and sets `_connected = True`. Returns `True` on success. |
| `disconnect()` | Closes the channel and connection gracefully, then resets all internal state to `None`. |
| `is_available()` | Returns `True` only if both the connection and channel are non-None and open. Used before every publish/consume operation. |
| `health_check()` | Calls `connection.process_data_events()` to confirm the connection is alive. Returns `True` if healthy. |
| `publish_message(message, queue_name, priority)` | Serializes the dict to JSON, acquires the threading lock, and calls `basic_publish` with `delivery_mode=2` (persistent). Auto-reconnects and retries once on stale connection. Returns `True` on success. |
| `consume_messages(callback, queue_name, prefetch_count)` | Sets `basic_qos(prefetch_count)`, registers an internal wrapper callback that deserializes JSON and calls user callback, then calls `start_consuming()` (blocking). On callback success → ACK; on exception → NACK with requeue. |
| `stop_consuming()` | Calls `channel.stop_consuming()` to break out of the blocking consume loop. |

**Module-level singleton:** `rabbitmq_service = RabbitMQService()` — shared instance imported by routers and the worker.

---

### `backend/app/services/redis_cache_service.py` — Redis Key-Value Cache

| Method | What It Does |
|---|---|
| `__init__()` | Creates a Redis connection pool with `max_connections=50` and pings Redis to verify. Sets `_enabled = False` if connection fails (graceful degradation). |
| `is_available()` | Returns `True` if cache is enabled and `_client` is not `None`. |
| `health_check()` | Sends `PING` to Redis. Returns `True` if Redis responds. |
| `get(key)` | Fetches a key from Redis, JSON-deserializes the value. Returns `None` on miss or error (graceful degradation). |
| `set(key, value, ttl)` | JSON-serializes `value` and writes it to Redis. If `ttl` is provided, uses `SETEX` (key expires automatically). Returns `True` on success. |
| `delete(key)` | Deletes a specific key from Redis. Returns `True` if deleted, `False` if key not found. |
| `delete_pattern(pattern)` | Finds all keys matching a glob pattern (e.g. `faq:chatbot:1:*`) and bulk-deletes them. Returns count of deleted keys. |
| `exists(key)` | Returns `True` if the key is present in Redis. |
| `get_ttl(key)` | Returns remaining TTL in seconds for a key. Returns `-1` if no expiration, `-2` if key does not exist. |
| `close()` | Closes the Redis connection pool. |

**Module-level singleton factory:** `get_redis_cache_service()` — returns (or creates) the single `RedisCacheService` instance.

---

### `backend/app/services/redis_pubsub_service.py` — Redis Pub/Sub Streaming

| Method | What It Does |
|---|---|
| `__init__()` | Creates a pooled Redis publish client (`max_connections=50`), pings Redis to verify, sets `_available`. |
| `is_available()` | Returns `True` if the publish client is ready. |
| `health_check()` | Pings Redis and returns `True`/`False`. |
| `get_channel_name(session_id)` | Builds the standard channel name: `chat_response:{session_id}`. |
| `publish(channel, message)` | Serializes `message` to JSON and calls `PUBLISH channel body`. Returns `True` if published. |
| `publish_to_session(session_id, message)` | Convenience wrapper: calls `get_channel_name()` then `publish()`. |
| `collect_job_response(job_id, timeout)` | Waits for the full AI response for a given `job_id`. First checks `rag_buffer:{job_id}` Redis List for a buffered replay (Docker worker), then subscribes to `rag_stream:{job_id}` and collects live token or complete messages. Returns a normalized response dict or `None` on timeout. |
| `subscribe(channel)` | Creates a **new** dedicated Redis connection (not pooled) and subscribes it to the given channel. Returns the `PubSub` object. Each WebSocket connection gets its own. |
| `unsubscribe(pubsub, channel)` | Unsubscribes the PubSub object from the channel and closes its connection. Must be called in `finally` to avoid connection leaks. |
| `listen_once(pubsub, timeout)` | Polls `pubsub.get_message()` in a loop (1-second windows) until a real message arrives or `timeout` expires. Returns the deserialized dict or `None`. Designed to be called via `asyncio.to_thread()`. |
| `close()` | Closes the shared publish client pool. |

**Module-level singleton factory:** `get_redis_pubsub_service()` — returns (or creates) the single `RedisPubSubService` instance.

---

### `backend/app/worker/chat_worker.py` — Background Job Consumer

| Method | What It Does |
|---|---|
| `__init__(rabbitmq_service, pubsub_service)` | Accepts injected `RabbitMQService` and `RedisPubSubService` (or creates defaults). Initializes `_running = False`. |
| `_get_db_session()` | Creates and returns a new `SessionLocal` SQLAlchemy DB session. Caller is responsible for closing it. |
| `_publish_response(job_id, session_id, payload)` | Publishes a result payload to `rag_stream:{job_id}` via `RedisPubSubService.publish()`. Used for both success and error responses. |
| `_process_job(message)` | Core job handler: validates the job payload, opens a DB session, calls `process_rag_message()` (RAG pipeline), publishes the result to Redis, and closes the DB session in `finally`. On any error, always publishes an error response so the WebSocket never hangs. |
| `start(run_in_thread)` | Starts the worker. If `run_in_thread=True`, wraps `_run_consumer()` in a daemon `threading.Thread`. If `False`, blocks the calling thread (used in Docker standalone mode). |
| `_run_consumer()` | Internal loop: connects to RabbitMQ, calls `consume_messages()` (blocking), and on failure sleeps 5 seconds and retries — infinite reconnect loop. |
| `stop()` | Stops the consumer loop by calling `rabbitmq_service.stop_consuming()`, sets `_running = False`, and joins the thread with a 5-second timeout. |
| `is_running()` | Returns `True` if the consumer loop is active. |

**Module-level singleton:** `chat_worker = ChatWorker()` — shared instance used by `main.py` lifespan.

---

### `backend/app/routers/websocket.py` — WebSocket Endpoint

| Function | What It Does |
|---|---|
| `websocket_chat(websocket, session_id, job_id)` | The single WebSocket handler at `WS /ws/chat/{session_id}/{job_id}`. Accepts the connection, checks Redis availability, calls `collect_job_response(job_id, timeout)` via `asyncio.to_thread()` to wait for the worker result without blocking the event loop, sends the result JSON to the client, and closes the connection. Handles `WebSocketDisconnect` for clean teardown. |

---

## What You Will Be Able to Explain After This Guide

After studying all 11 files you will confidently answer:

- **Why** did you choose RabbitMQ over direct API calls?
- **How** does the WebSocket know when the AI has finished responding?
- **What** happens if Redis goes down while a user is waiting?
- **How** does JWT authentication work without a database lookup on every request?
- **Why** is the worker separated from the API server?
- **How** does the FAQ cache reduce OpenAI API costs?
- **What** is the difference between Redis Pub/Sub and a message queue?
- **How** would you scale this system to handle 10,000 concurrent users?
- **What** happens if RabbitMQ crashes while jobs are in the queue?
- **How** do you prevent race conditions in a distributed system?
- **What** are the failure modes in each component and how does the system recover?

---

## How to Use This Guide

1. Read each file in order (1 → 11)
2. After each section, close the file and try to explain it out loud
3. Answer the interview questions without looking at the answers
4. Map each concept back to a file in `backend/app/`
5. After completing all 11 files, re-read `9_complete_request_flow.md` — it should now make complete sense

---

*This guide was written to prepare you to speak confidently, technically, and accurately about every engineering decision in this system.*
