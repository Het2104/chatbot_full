# 4. Worker Service — Deep Technical Learning

---

## 4.1 Concept Introduction

A **worker service** is a background process that performs work independently of the main application server. The worker:
- Does not serve HTTP requests
- Does not respond to the user directly
- Runs continuously, picking up jobs from a queue
- Does the heavy lifting (AI calls, data processing)

In your system, the `ChatWorker` (`worker/chat_worker.py`) is the engine room of the chatbot. All the computationally expensive work — running the RAG pipeline, calling OpenAI, processing documents — happens here.

---

## 4.2 Why the Worker is Separated from the API Server

The core principle is **separation of concerns**:

```
WITHOUT separation (bad):
┌──────────────────────────────────────────────────────┐
│  FastAPI API Server                                  │
│                                                      │
│  Request comes in:                                   │
│  1. Validate JWT                                     │
│  2. Check FAQ cache                                  │
│  3. Run RAG pipeline (expensive!)                    │
│  4. Call OpenAI API (slow!)                          │
│  5. Return response                                  │
│                                                      │
│  Problem: Steps 3-4 can take 15 seconds.              │
│  All other requests queue up behind current one.     │
│  10 concurrent users = 10 threads blocked for 15s   │
└──────────────────────────────────────────────────────┘

WITH separation (your system):
┌──────────────────┐    queue    ┌────────────────────┐
│  FastAPI Server  │ ─────────► │    ChatWorker      │
│                  │             │                    │
│  1. Validate JWT │             │  1. Consume job    │
│  2. Check cache  │             │  2. Run RAG        │
│  3. Publish job  │             │  3. Call OpenAI    │
│  4. Return 202   │             │  4. Publish result │
│                  │             │                    │
│  Returns in <1ms │             │  Takes 2-15 sec    │
└──────────────────┘             └────────────────────┘
```

**Benefits:**
1. API server handles thousands of requests per second
2. Workers scale independently (add more workers for AI load)
3. If AI calls are slow, workers slow down — API remains fast
4. Worker crash doesn't affect API server

---

## 4.3 ChatWorker Class Architecture

```python
class ChatWorker:
    def __init__(self, rabbitmq_service, pubsub_service):
        self._rabbitmq = rabbitmq_service   # For consuming jobs
        self._pubsub = pubsub_service        # For publishing results
        self._running = False
        self._thread = None

    def start(self):
        """Start consuming in a background thread"""
        
    def stop(self):
        """Gracefully stop consuming"""
        
    def _consume_loop(self):
        """Main consume loop — blocks on RabbitMQ"""
        
    def _process_job(self, job_data):
        """Process one job: RAG pipeline → Redis publish"""
        
    def _publish_error(self, session_id, job_id, error_msg):
        """Always notify client even on failure"""
```

**Why class-based?**
- State management: `_running`, `_thread`, `_rabbitmq`, `_pubsub` live on the instance
- Lifecycle methods: `start()` and `stop()` clearly define the worker lifecycle
- Testability: easy to mock `rabbitmq_service` and `pubsub_service` in tests
- Reusability: multiple worker instances can be created with different configurations

---

## 4.4 Worker Startup Flow

In `backend/app/main.py`, the worker is started at application startup using FastAPI's **lifespan** context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    worker = ChatWorker(rabbitmq_service=..., pubsub_service=...)
    worker.start()          # Starts background thread
    
    yield                   # App is running here
    
    # SHUTDOWN
    worker.stop()           # Gracefully stops thread
```

**Worker thread lifecycle:**

```
FastAPI starts
      │
      ▼
lifespan() runs
      │
      ▼
ChatWorker.start()
      │
      ▼
threading.Thread(target=self._consume_loop).start()
      │
      ▼
_consume_loop() runs:
  → connect to RabbitMQ
  → channel.basic_qos(prefetch_count=1)
  → channel.basic_consume(
        queue="rag_processing_queue",
        on_message_callback=self._on_message,
        auto_ack=False
    )
  → channel.start_consuming()  ← BLOCKS on this thread, not main thread
      │
      ▼
For each message received:
  → _process_job() called
      │
      ├─ Success → basic_ack()
      └─ Error   → basic_nack(requeue=True) + publish error to Redis
```

---

## 4.5 The RAG Pipeline in the Worker

When `_process_job()` runs, it executes the full RAG (Retrieval-Augmented Generation) pipeline:

```
User message: "What is the return policy?"
      │
      ▼
1. Embed query
   → Use embedding model to convert question to vector
   → [0.123, -0.456, 0.789, ...]  (768 or 1536 dimensions)
      │
      ▼
2. Vector search in Milvus
   → Find top-K most similar document chunks
   → Returns: ["Products can be returned within 30 days...",
               "Refunds are processed within 5-7 business days..."]
      │
      ▼
3. Build context-enhanced prompt
   → Combine retrieved chunks + user question
   → "Context: {chunks}\n\nQuestion: {user_message}\n\nAnswer:"
      │
      ▼
4. Call OpenAI
   → POST to OpenAI API with prompt
   → Wait for response (2-15 seconds)
   → "You can return any product within 30 days of purchase..."
      │
      ▼
5. Publish result to Redis Pub/Sub
   → channel: chat_response:{session_id}
   → payload: {response, next_options, status, is_done}
```

**RAG benefit:** Without RAG, OpenAI only knows what it was trained on. With RAG, it knows about YOUR specific business documents (uploaded PDFs), making it accurate for domain-specific questions.

---

## 4.6 Error Handling Strategy

**Critical principle:** The worker must ALWAYS publish something to Redis, even on error. If it doesn't, the WebSocket client will hang until timeout.

```python
def _process_job(self, job_data):
    try:
        # ... RAG pipeline ...
        self._pubsub.publish(channel, {
            "response": ai_response,
            "status": "success",
            "is_done": True
        })
        channel.basic_ack(delivery_tag)
        
    except OpenAIError as e:
        # OpenAI API failed — inform client
        self._pubsub.publish(channel, {
            "response": "AI service temporarily unavailable.",
            "status": "error",
            "is_done": True
        })
        channel.basic_nack(delivery_tag, requeue=False)
        
    except Exception as e:
        # Unexpected error — still inform client
        self._publish_error(session_id, job_id, str(e))
        channel.basic_nack(delivery_tag, requeue=True)
```

**Why `requeue=True` for some errors and `requeue=False` for others?**
- Transient errors (network timeout, overload): `requeue=True` — another attempt might succeed
- Permanent errors (malformed message, invalid user): `requeue=False` — retrying won't help

---

## 4.7 Worker Decoupling Logic

**Decoupling** means components don't know about each other directly. The ChatWorker knows nothing about:
- Which HTTP request triggered the job
- Which WebSocket connection is waiting
- The user's authentication state
- The frontend framework

It only knows:
- What message was in the queue (job_id, session_id, chatbot_id, user_message)
- Where to publish the result (Redis channel: `chat_response:{session_id}`)

This decoupling means you can:
- Change the API server completely — worker doesn't care
- Change the worker implementation — API server doesn't care
- Add more workers — the queue handles distribution
- Deploy workers in a different data center — communication still works via broker

---

## 4.8 Streaming Token Logic

**Current implementation:** The worker processes the full AI response and then publishes it as one complete message. This is called **batch response delivery**.

**Advanced streaming (future implementation):**
```
OpenAI streaming API → token by token → Redis PUBLISH per token
                                      → WebSocket delivers each token to frontend
                                      → Frontend renders tokens as they arrive
```

This creates the "typewriter effect" where text appears character by character. It requires:
- `stream=True` in OpenAI API call
- Loop over `response.choices[0].delta.content` tokens
- Redis PUBLISH for each token with `is_done=False`
- Final PUBLISH with `is_done=True`

---

## 4.9 Database Session Management in Worker

The worker needs database access (to store chat messages). It uses a **scoped session**:

```python
# In chat_worker.py
from database import SessionLocal

def _process_job(self, job_data):
    db = SessionLocal()
    try:
        # ... process with db ...
    finally:
        db.close()  # Always close, even on error
```

**Why not a global database session?**
Workers are long-running processes. A global session holds a database connection open forever, which:
- Prevents database connection pool cleanup
- Can accumulate uncommitted transactions
- Causes connection count exhaustion at scale

---

## 4.10 ASCII: Worker Full Lifecycle

```
FastAPI Startup
      │
      ▼
ChatWorker.start()
      │
      ▼
Background Thread: _consume_loop()
      │
      ▼
Connect to RabbitMQ ──── FAIL ──► Log error, retry after 5s
      │
      │ SUCCESS
      ▼
basic_qos(prefetch_count=1)
      │
      ▼
basic_consume(queue="rag_processing_queue", auto_ack=False)
      │
      ▼
start_consuming()  ← thread blocks here, waiting
      │
      │ [Message arrives]
      ▼
_on_message(ch, method, properties, body)
      │
      ▼
json.loads(body)  →  job_data dict
      │
      ▼
_process_job(job_data)
      │
      ├─ FAQ cache hit?  →  publish cache result  →  ACK  →  done
      │
      └─ RAG pipeline
              │
              ▼
         Milvus similarity search
              │
              ▼
         OpenAI API call
              │
         ┌────┴──────────┐
         │ SUCCESS       │ FAILURE
         ▼               ▼
    publish result   publish error
    to Redis         to Redis
         │               │
         ▼               ▼
        ACK            NACK
         │               │
         └───────┬───────┘
                 ▼
         back to start_consuming()
         waiting for next message
```

---

## 4.11 Interview Questions and Answers

**Q: Why is the worker separate from the API server?**

A: Because AI processing is slow (2-15 seconds). If the API server waited for AI to finish, no other requests could be served. The worker handles AI processing independently in a background process. The API server stays fast for all users.

**Q: How does the worker know which WebSocket to send the result to?**

A: The job contains a `session_id`. The worker publishes the result to Redis channel `chat_response:{session_id}`. The WebSocket handler that's waiting for that specific `session_id` is subscribed to that channel and receives the message.

**Q: What happens if the worker crashes mid-processing?**

A: The message was unacknowledged (ACK was not sent). RabbitMQ detects the disconnection via heartbeat timeout and automatically requeues the message. Another worker instance picks it up. The WebSocket client eventually times out on the current request and can retry.

**Q: Can you have multiple workers running at the same time?**

A: Yes. Multiple `ChatWorker` instances can consume from the same `rag_processing_queue`. RabbitMQ distributes messages round-robin across workers with `prefetch_count=1` ensuring fair load distribution. In production, workers run as separate containers.

**Q: Why must the worker always publish to Redis even on error?**

A: The WebSocket handler is blocking, waiting for a Redis message. If the worker fails silently and publishes nothing, the WebSocket client hangs until its timeout (60 seconds). By always publishing a response (success or error), the client immediately gets notified instead of waiting.

---

## 4.12 Common Mistakes

1. **Not publishing to Redis on worker failure** — WebSocket client hangs for 60 seconds
2. **Using `auto_ack=True`** — Message lost if worker crashes mid-processing
3. **Not closing database sessions** — Connection pool exhaustion after hours of running
4. **Not handling heartbeat** — Long AI calls cause RabbitMQ to drop connection, duplicate job processing
5. **Starting worker outside lifespan context** — Worker might start before app is ready, or not stop gracefully
6. **Not logging worker errors** — Silent failures in background thread are invisible without logs

---

## 4.13 Production Considerations

- Run worker as a separate Docker container (not a thread inside FastAPI)
- Use container orchestration (Kubernetes, Docker Swarm) to auto-restart crashed workers
- Set worker count based on OpenAI API rate limits (too many workers = rate limit errors)
- Implement exponential backoff for OpenAI call retries
- Set up Dead Letter Queue for messages that fail permanently
- Monitor worker queue depth — alert if > N messages (workers not keeping up)
- Log structured JSON from workers for centralized log aggregation (ELK stack)

---

## 4.14 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/worker/chat_worker.py` | Full ChatWorker class implementation |
| `backend/app/main.py` | Worker startup in lifespan context |
| `backend/app/services/rabbitmq_service.py` | Queue consumption setup |
| `backend/app/services/redis_pubsub_service.py` | Result publishing |
| `backend/app/rag/` | RAG pipeline implementation |
| `backend/app/config.py` | `WORKER_PREFETCH_COUNT`, `WEBSOCKET_RESPONSE_TIMEOUT` |
