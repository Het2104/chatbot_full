# 1. System Architecture — Deep Technical Learning

---

## 1.1 Concept Introduction

**System architecture** describes how components of a software system are structured, how they communicate, and why each component exists. In a distributed system, multiple processes run independently, communicate over a network, and collectively deliver a single user experience.

Your chatbot system is a **distributed asynchronous system**. That means:

- The component that **receives** the user's message is different from the component that **processes** it
- Processing happens asynchronously — the user does not wait for AI to finish before getting a response acknowledgment
- Multiple services collaborate using network protocols (HTTP, WebSocket, AMQP, Redis protocol)

---

## 1.2 Monolith vs Distributed — Deep Comparison

### Monolithic Architecture

```
┌──────────────────────────────────────────────────────┐
│                  SINGLE APP PROCESS                  │
│                                                      │
│  HTTP Request → Validate → Query AI → Send Response  │
│                                                      │
│  Everything runs inside one Python process            │
└──────────────────────────────────────────────────────┘
```

**Problems with monolith for AI chatbot:**

| Problem | Explanation |
|---|---|
| Blocking I/O | While Python waits for OpenAI response (2-15s), no other requests are served |
| No fault isolation | If AI call crashes, entire app crashes |
| No independent scaling | Cannot scale only the AI-heavy code without scaling everything |
| Thread exhaustion | Under high concurrency, all threads are blocked waiting for AI |
| Slow deployments | One change anywhere requires redeploying everything |

### Distributed Architecture

```
┌──────────────┐     queue     ┌──────────────┐
│  API Server  │  ─────────►  │   Worker     │
│  (FastAPI)   │               │  (ChatWorker)│
└──────────────┘               └──────────────┘
       │                               │
       │ WebSocket                     │ Redis
       │                               │ Pub/Sub
       ▼                               ▼
┌──────────────┐               ┌──────────────┐
│   Frontend   │ ◄─────────── │    Redis     │
│   (Next.js)  │               │   Broker     │
└──────────────┘               └──────────────┘
```

**Benefits of distributed architecture for AI chatbot:**

| Benefit | Explanation |
|---|---|
| Non-blocking API | API server accepts request and returns immediately |
| Independent scaling | You can run 10 workers and 1 API server |
| Fault isolation | If worker crashes, API server keeps running |
| Backpressure management | RabbitMQ holds jobs when workers are busy instead of dropping them |
| Technology flexibility | Each service can use the best tool for its job |

---

## 1.3 Your System's Components Explained

### Component 1: FastAPI Application Server (`backend/app/main.py`)

The central entry point. It:
- Registers all HTTP and WebSocket routers
- Starts the ChatWorker in a background thread at startup
- Creates dependency injection bindings for services
- Handles CORS, logging, and application lifecycle events

**Why FastAPI?**
- Async-native (built on Starlette/asyncio)
- Automatic OpenAPI documentation
- Pydantic validation built-in
- Fast enough for production workloads

### Component 2: RabbitMQ Message Broker

A **message broker** is an intermediary that receives messages from producers and delivers them to consumers. Think of it as a post office — the sender drops a letter, and the post office guarantees delivery to the recipient.

**Why RabbitMQ over Celery/Redis queue?**
- Battle-tested at scale (used by Instagram, GitHub, etc.)
- Native support for complex routing (exchanges, bindings)
- Message durability (messages survive broker restart)
- Acknowledgment protocol ensures at-least-once delivery
- Management UI built-in at port 15672

### Component 3: ChatWorker (`backend/app/worker/chat_worker.py`)

A background service that:
- Consumes jobs from RabbitMQ
- Runs the RAG (Retrieval-Augmented Generation) pipeline
- Calls OpenAI for AI-generated responses
- Publishes results to Redis Pub/Sub

The worker runs in a **background thread** inside the same FastAPI process (see `main.py` lifespan events). In a production cluster, you would run it as a separate process/container.

### Component 4: Redis (Dual Role)

Redis serves **two different functions** in this system:

| Role | Mechanism | Purpose |
|---|---|---|
| Pub/Sub broker | `PUBLISH` / `SUBSCRIBE` | Routes worker result to the correct WebSocket connection |
| FAQ cache | `SET key value EX ttl` | Returns cached FAQ answers instantly |

Using one Redis instance for both is fine in development. In production, you would consider separate Redis instances to avoid memory and CPU contention.

### Component 5: PostgreSQL Database (`backend/database.py`)

Stores all persistent data:
- Users and hashed passwords
- Chatbots, workflows, nodes, edges
- Chat sessions and messages
- FAQ entries

### Component 6: Milvus Vector Database

Used in the RAG pipeline to store and search document embeddings. When the user asks a question, Milvus finds the most semantically similar document chunks, which are then passed to OpenAI as context.

### Component 7: MinIO Object Storage (`backend/app/services/minio_storage.py`)

Stores uploaded PDF files. When a PDF is uploaded, it is saved to MinIO (an S3-compatible object store) and then processed to extract text for embedding.

---

## 1.4 Data Flow — Request Lifecycle

```
Step 1: User opens browser
         → Frontend (Next.js) loads

Step 2: User logs in
         → POST /auth/login
         → FastAPI validates credentials
         → Returns JWT access token
         → Frontend stores token

Step 3: User sends chat message
         → POST /chat/message/queue
         → JWT verified in middleware
         → ChatService checks Redis FAQ cache
         → If HIT → immediate response (no queue)
         → If MISS → publish to RabbitMQ, return job_id

Step 4: Frontend opens WebSocket
         → WS /ws/chat/{session_id}/{job_id}
         → WebSocket handler subscribes to Redis channel

Step 5: Worker processes job
         → ChatWorker consumes from RabbitMQ
         → Runs RAG pipeline
         → Gets AI response from OpenAI
         → Publishes result to Redis channel

Step 6: Result delivered
         → WebSocket handler receives from Redis
         → Sends JSON to frontend via WebSocket
         → Frontend renders response
         → WebSocket closes
```

---

## 1.5 Why Each Technology Was Chosen

| Need | Problem | Solution | Alternative Considered |
|---|---|---|---|
| Handle concurrent users | Blocking AI calls exhaust threads | Async API + message queue | Synchronous REST blocks |
| Non-blocking AI response | AI takes 2-15s | Background worker | Thread-per-request doesn't scale |
| Real-time delivery | HTTP is request-response | WebSocket persistent connection | Short polling wastes resources |
| Worker result routing | Multiple concurrent users | Redis Pub/Sub channels | Database polling is slow |
| Repeated questions | Same FAQ hit OpenAI multiple times | Redis FAQ cache | No cache burns API credits |
| Reliable job delivery | Worker might crash | RabbitMQ ACK/NACK | In-memory queue loses jobs |

---

## 1.6 ASCII: Full System Topology with Ports

```
                        ┌─────────────────┐
                        │   Next.js       │
                        │   localhost:3000 │
                        └────────┬────────┘
                                 │ HTTP / WS
                        ┌────────▼────────┐
                        │   FastAPI       │
                        │   localhost:8000 │
                        │                 │
                        │  main.py        │
                        │  routers/       │
                        │  services/      │
                        │  worker/ (thread)│
                        └─┬──────┬────────┘
                          │      │
         ┌────────────────┘      └────────────────┐
         │                                         │
┌────────▼────────┐                      ┌────────▼────────┐
│   RabbitMQ      │                      │   Redis         │
│   localhost:5672 │                      │   localhost:6379 │
│   mgmt:15672    │                      │                 │
│                 │                      │  Pub/Sub        │
│  Queue:         │                      │  Cache          │
│  rag_processing_│                      └─────────────────┘
│  queue          │
└─────────────────┘
         │
┌────────▼────────┐     ┌─────────────────┐
│   ChatWorker    │────►│   Milvus        │
│   (thread)      │     │   localhost:19530│
└─────────────────┘     └─────────────────┘
         │
┌────────▼────────┐
│   OpenAI API    │
│   (external)    │
└─────────────────┘
```

---

## 1.7 Technical Deep Dive: Async vs Sync Architecture

FastAPI is built on **asyncio** — Python's native event loop for cooperative multitasking.

**Synchronous (blocking) flow:**
```python
# This BLOCKS the event loop for 10 seconds
result = requests.post("https://api.openai.com/v1/...", ...)
# Nobody else can be served until this returns
```

**Asynchronous (non-blocking) flow:**
```python
# This YIELDS control back to the event loop immediately
result = await httpx.AsyncClient().post("https://api.openai.com/v1/...", ...)
# While waiting, FastAPI can serve OTHER requests
```

**Why you need a worker anyway:**

Even with async, OpenAI calls can take 15+ seconds. Holding an HTTP connection open for 15 seconds is wasteful and fragile. The queue pattern means:
- HTTP connection closes immediately after job submission
- WebSocket connection (lightweight, persistent) waits for result
- Server resources are freed immediately

---

## 1.8 Interview Questions and Answers

**Q: What is the difference between synchronous and asynchronous architecture?**

A: In synchronous architecture, each request waits for all processing to complete before returning a response. In asynchronous architecture, the API accepts the request and returns immediately, while a background worker handles the heavy processing. The result is delivered through a separate channel (WebSocket, polling, webhook).

**Q: Why use a message queue instead of calling the worker directly via HTTP?**

A: Direct HTTP calls create tight coupling — if the worker is slow, the API server blocks. If the worker crashes, the API server gets an error. A message queue provides decoupling: the API server publishes the job and forgets about it. The queue holds the job until a worker picks it up. If the worker crashes, the message stays in the queue. Multiple workers can consume from the same queue for scaling.

**Q: What is the role of Redis in this system?**

A: Redis plays two roles: (1) as a Pub/Sub broker to route worker results to the correct WebSocket connection, and (2) as a cache to store frequently asked FAQ responses, reducing OpenAI API calls.

**Q: Why is the worker run inside the same FastAPI process in development?**

A: For simplicity in local development, the `ChatWorker` is started as a background thread when FastAPI starts (in `main.py` lifespan). In production, it would be deployed as a separate container/process to allow independent scaling.

**Q: What happens if the system receives 1,000 concurrent chat messages?**

A: All 1,000 jobs get published to RabbitMQ instantly. The queue holds them. The workers process them at their own pace (controlled by `WORKER_PREFETCH_COUNT`). Users see immediate acknowledgment and wait via WebSocket. No requests are dropped, no server overloads.

---

## 1.9 Common Mistakes Developers Make

1. **Running AI calls synchronously in the API server** — this is the most common mistake and immediately kills scalability.

2. **Not using acknowledgments** — if a worker crashes while processing, the job is lost. Always use ACK/NACK.

3. **Using one Redis connection globally without a pool** — Redis connections are not thread-safe. Always use a connection pool.

4. **Forgetting to close WebSocket subscriptions** — every subscribe creates a Redis connection. Leaking them exhausts Redis connection limits.

5. **Storing JWT tokens in localStorage without HTTPS** — tokens can be stolen via XSS. Use HttpOnly cookies in production.

---

## 1.10 Production Considerations

- Deploy API server, worker, RabbitMQ, Redis, and PostgreSQL as separate containers
- Use health checks for all services in Docker Compose
- Set `restart: always` on all containers
- Use environment variables for all secrets (never hardcode)
- Enable RabbitMQ durable queues and message persistence
- Use Redis Sentinel or Redis Cluster for high availability
- Use Nginx as a reverse proxy in front of FastAPI
- Enable SSL/TLS for all external traffic
- Implement rate limiting at the API gateway level

---

## 1.11 Failure Scenarios

| Failure | Impact | Recovery |
|---|---|---|
| FastAPI crashes | New requests fail | Restart container (Docker restart policy) |
| RabbitMQ crashes | Jobs published while down are lost | Resume after restart; use persistent messages |
| Redis crashes | WebSocket clients timeout; cache misses | System falls back to direct AI calls |
| Worker crashes | Jobs stay in queue (not ACKed) | RabbitMQ requeues unACKed messages automatically |
| OpenAI API timeout | Worker catches exception | Publishes error response to Redis channel |
| PostgreSQL crashes | All DB operations fail | Container restart; use read replicas for reads |

---

## 1.12 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/main.py` | Application entry point, worker startup |
| `backend/app/config.py` | All configuration constants |
| `backend/app/routers/chat.py` | Chat message endpoint |
| `backend/app/routers/websocket.py` | WebSocket endpoint |
| `backend/app/worker/chat_worker.py` | Background job processor |
| `backend/app/services/rabbitmq_service.py` | RabbitMQ producer/consumer |
| `backend/app/services/redis_pubsub_service.py` | Redis Pub/Sub client |
| `backend/app/services/redis_cache_service.py` | Redis cache client |
| `backend/docker-compose.yml` | Full service topology |
