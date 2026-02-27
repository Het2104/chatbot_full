# 9. Complete Request Flow — End-to-End Deep Trace

---

## 9.1 Introduction

This document traces a complete request through every layer of the system, from the moment a user opens the browser to the moment they see the AI response. This is the most important document in this guide — it ties together everything you have learned.

---

## 9.2 Prerequisite: System is Running

```
docker-compose up (or manual startup):

✅ FastAPI running on port 8000
✅ RabbitMQ running on port 5672 (management: 15672)
✅ Redis running on port 6379
✅ PostgreSQL running on port 5432
✅ Milvus running on port 19530
✅ MinIO running on port 9000
✅ Next.js frontend running on port 3000
✅ ChatWorker thread running inside FastAPI process
```

---

## 9.3 Phase 1: User Login

### 1.1 Frontend Action
User opens `http://localhost:3000`, enters username and password, clicks Login.

### 1.2 HTTP Request
```
POST http://localhost:3000/api/auth/login
Content-Type: application/json

{
  "username": "alice",
  "password": "mypassword123"
}
```

Next.js proxies to FastAPI (or frontend calls FastAPI directly depending on config).

### 1.3 FastAPI Receives Request
**File:** `backend/app/routers/auth.py`
```
POST /auth/login arrives at FastAPI
→ Pydantic validates request body (LoginRequest schema)
→ Calls auth_service.verify_password(request.password, user.hashed_password)
→ bcrypt.verify() — CPU operation, ~100ms
```

### 1.4 Password Verification
**File:** `backend/app/services/auth_service.py`
```python
verify_password("mypassword123", "$2b$12$LQv3c1yqBWVHxkd0LHAkCO...")
# bcrypt internally:
#   1. Extract salt from hash
#   2. Hash input password with same salt
#   3. Compare resulting hash with stored hash
#   Returns: True
```

### 1.5 Token Creation
```python
token = create_access_token({"sub": "alice"})
# Internally:
#   payload = {"sub": "alice", "exp": now + 30min, "iat": now}
#   jwt.encode(payload, SECRET_KEY, algorithm="HS256")
#   Returns: "eyJhbGci......"
```

### 1.6 Response to Frontend
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Frontend stores token in memory/localStorage. All future requests include:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 9.4 Phase 2: User Sends a Chat Message

### 2.1 Frontend Action
User types "What is the return policy?" in the chat box and clicks Send.

### 2.2 HTTP Request
```
POST http://localhost:8000/chat/message/queue
Authorization: Bearer eyJhbGci...
Content-Type: application/json

{
  "chatbot_id": 7,
  "session_id": null,
  "message": "What is the return policy?"
}
```

### 2.3 JWT Authentication Middleware
**File:** `backend/app/dependencies/`
```
FastAPI calls get_current_user() dependency before route runs:
→ Extract token from Authorization header
→ jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
  → Verify signature: HMAC-SHA256(header.payload, SECRET_KEY)
  → Check exp: 1709123456 > current_time? ✅
  → Returns: {"sub": "alice", "exp": ..., "iat": ...}
→ Query DB: SELECT * FROM users WHERE username = "alice"
→ User found and active: ✅
→ Inject user object into route
```

### 2.4 Chat Route Handler
**File:** `backend/app/routers/chat.py`
```
POST /chat/message/queue:
→ Create or retrieve ChatSession in PostgreSQL
  → session_id = 42
→ Save user message to chat_messages table
→ Call faq_service.check_faq_cache("What is the return policy?")
```

### 2.5 FAQ Cache Check
**File:** `backend/app/services/faq_service.py`
```
normalize: "what is the return policy?"
hash: md5("what is the return policy?") = "a1b2c3d4..."
redis_key: "faq:a1b2c3d4..."

redis_cache_service.get("faq:a1b2c3d4...")
  → Redis command: GET faq:a1b2c3d4...
```

#### PATH A: Cache HIT
```
Redis returns: "You can return any product within 30 days..."
→ Save AI response to chat_messages table
→ Return HTTP 200 immediately:
  {
    "session_id": 42,
    "response": "You can return any product within 30 days...",
    "from_cache": true,
    "job_id": null
  }
(No WebSocket needed — response already in HTTP response body)
```

#### PATH B: Cache MISS (continues to next phase)
```
Redis returns: nil
→ No FAQ match found in cache
→ Proceed to RabbitMQ queue
```

### 2.6 Publish to RabbitMQ
**File:** `backend/app/services/rabbitmq_service.py`
```python
job = {
    "job_id":       "550e8400-e29b-41d4-a716-446655440000",
    "session_id":   42,
    "chatbot_id":   7,
    "user_message": "What is the return policy?"
}

rabbitmq_service.publish(job)
# Internally:
#   with self._lock:  # Thread-safe
#     channel.basic_publish(
#         exchange="",
#         routing_key="rag_processing_queue",
#         body=json.dumps(job).encode(),
#         properties=BasicProperties(delivery_mode=2)  # Persistent
#     )
```

### 2.7 Immediate HTTP Response (202 Accepted)
```json
{
  "session_id": 42,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Processing your message..."
}
```

**The HTTP connection closes here.** The user gets an immediate acknowledgment.

---

## 9.5 Phase 3: WebSocket Connection Opens

### 3.1 Frontend Opens WebSocket
```javascript
// Frontend (Next.js)
const ws = new WebSocket(
    `ws://localhost:8000/ws/chat/42/550e8400-e29b-41d4-a716-446655440000`
);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setResponse(data.response);  // Update React state
};
```

### 3.2 WebSocket Handshake
```
Client → Server:
  GET /ws/chat/42/550e8400... HTTP/1.1
  Upgrade: websocket
  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==

Server → Client:
  HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

Connection is now a persistent WebSocket.

### 3.3 Redis Subscription
**File:** `backend/app/routers/websocket.py`
```python
await websocket.accept()

pubsub_service = get_redis_pubsub_service()
# Check availability
if not pubsub_service.is_available():
    await websocket.send_json({...error...})
    return

# Subscribe to Redis channel for this session
subscription = pubsub_service.subscribe("chat_response:42")
# Redis command: SUBSCRIBE chat_response:42
```

### 3.4 WebSocket Waits (Non-Blocking)
```python
# This runs in a thread pool — event loop is NOT blocked
result = await asyncio.to_thread(
    pubsub_service.listen_once,
    subscription,
    60  # 60 second timeout
)

# listen_once() polls every 1 second:
#   pubsub.get_message(timeout=1.0)
#   → Waits up to 1s for Redis message
#   → Returns None if no message yet
#   → Loops until message or timeout
```

At this point, the WebSocket handler is BLOCKED in a thread (not blocking the event loop), waiting for the Redis message from the worker.

---

## 9.6 Phase 4: Worker Processes the Job

### 4.1 RabbitMQ Delivers Message to Worker
```
ChatWorker thread is running channel.start_consuming()
→ RabbitMQ has [job1] in queue
→ Delivers message to worker callback
→ channel.basic_consume callback fires
```

### 4.2 Worker Extracts Job
**File:** `backend/app/worker/chat_worker.py`
```python
job_data = json.loads(body)
# {
#   "job_id": "550e8400...",
#   "session_id": 42,
#   "chatbot_id": 7,
#   "user_message": "What is the return policy?"
# }
```

### 4.3 RAG Pipeline Execution
**File:** `backend/app/rag/`
```
Step 1: Embed user message
  → Call embedding model
  → "What is the return policy?" → [0.123, -0.456, ...]

Step 2: Search Milvus vector database
  → Find top-3 most similar document chunks
  → Returns: [
      "Products may be returned within 30 days of purchase...",
      "Refunds are processed within 5-7 business days...",
      "Items must be in original packaging..."
    ]

Step 3: Build augmented prompt
  → "Context:\n{chunks}\n\nQuestion: What is the return policy?\n\nAnswer:"

Step 4: Call OpenAI API
  → POST https://api.openai.com/v1/chat/completions
  → model: "gpt-4"
  → messages: [{role: "user", content: augmented_prompt}]
  → [waiting 2-10 seconds...]
  → Response: "You can return any product within 30 days of purchase.
               Items must be in their original packaging.
               Refunds are processed within 5-7 business days."
```

### 4.4 Worker Publishes to Redis
**File:** `backend/app/services/redis_pubsub_service.py`
```python
channel_name = "chat_response:42"
payload = {
    "job_id":       "550e8400...",
    "session_id":   42,
    "response":     "You can return any product within 30 days...",
    "next_options": ["Tell me more", "Contact support"],
    "status":       "success",
    "is_done":      True
}

self._publish_client.publish(
    channel_name, 
    json.dumps(payload)
)
# Redis command: PUBLISH chat_response:42 "{...json...}"
```

### 4.5 Worker ACKs the Message
```python
channel.basic_ack(delivery_tag=method.delivery_tag)
# Message permanently deleted from RabbitMQ queue
```

---

## 9.7 Phase 5: Response Delivered to Frontend

### 5.1 Redis Delivers to WebSocket Handler
```
Redis broadcasts PUBLISH to all SUBSCRIBE chat_response:42 connections
→ WebSocket handler's listen_once() gets the message:
  pubsub.get_message()  →  returns {type: "message", data: "{...json...}"}
→ json.loads(data) → dict
→ listen_once() returns the dict
```

### 5.2 WebSocket Handler Sends to Frontend
**File:** `backend/app/routers/websocket.py`
```python
result = await asyncio.to_thread(listen_once, ...)
# result = {"response": "You can return...", "is_done": True, ...}

if result:
    await websocket.send_json(result)
    # WebSocket text frame sent to browser
```

### 5.3 WebSocket Closes
```python
# After send_json, is_done=True means the function returns
# WebSocket closes when the async function exits
# finally block runs:
#   pubsub_service.unsubscribe(subscription)
#   → Redis UNSUBSCRIBE chat_response:42
#   → Redis connection returned to pool
```

### 5.4 Frontend Receives and Renders
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // data = {
    //   "response": "You can return any product within 30 days...",
    //   "next_options": ["Tell me more", "Contact support"],
    //   "status": "success",
    //   "is_done": true
    // }
    
    setMessage(data.response);
    setOptions(data.next_options);
    ws.close();  // Close WebSocket after receiving complete response
};
```

Browser renders the AI response. User sees: "You can return any product within 30 days..."

---

## 9.8 Timing Analysis

```
T=0ms:    POST /chat/message/queue arrives at FastAPI
T=2ms:    JWT verified (cryptographic operation)
T=5ms:    FAQ cache checked (Redis lookup: ~0.5ms, cache miss)
T=8ms:    Job published to RabbitMQ
T=10ms:   HTTP response 202 returned to frontend
T=11ms:   Frontend opens WebSocket
T=12ms:   WebSocket accepted, Redis subscription created
T=12ms:   Frontend shows "Processing..." indicator

[Background — user does not wait for this]
T=15ms:   Worker picks up job from RabbitMQ
T=200ms:  Embedding model returns query vector
T=500ms:  Milvus vector search returns top-3 chunks
T=2500ms: OpenAI returns AI response (2 seconds — fast day)
T=2501ms: Worker publishes to Redis channel chat_response:42
T=2502ms: Redis delivers to WebSocket handler subscription
T=2503ms: WebSocket sends JSON to frontend
T=2504ms: Frontend renders response text

Total visible latency to user: ~2.5 seconds (dominated by OpenAI)
HTTP overhead: 10ms
WebSocket overhead: 1ms
Redis overhead: 1ms
```

---

## 9.9 Full ASCII Flow Diagram

```
Browser                FastAPI              RabbitMQ          Worker            Redis
  │                       │                     │                │                │
  │  POST /chat/message   │                     │                │                │
  │──────────────────────►│                     │                │                │
  │                       │ verify JWT          │                │                │
  │                       │ check FAQ cache     │                │                │
  │                       │─────────────────────────────────────────────────────►│
  │                       │◄─────────────────────────────────────────────────────│
  │                       │ MISS                │                │                │
  │                       │ publish job         │                │                │
  │                       │────────────────────►│                │                │
  │  202 + job_id         │                     │                │                │
  │◄──────────────────────│                     │                │                │
  │                       │                     │ deliver job    │                │
  │                       │                     │───────────────►│                │
  │  WS /ws/chat/42/job   │                     │                │                │
  │──────────────────────►│                     │                │                │
  │  101 Switching Proto  │                     │                │                │
  │◄──────────────────────│                     │                │                │
  │                       │ SUBSCRIBE           │                │                │
  │                       │ chat_response:42    │                │                │
  │                       │────────────────────────────────────────────────────►│
  │                       │ [waiting for msg]   │                │                │
  │                       │                     │                │ RAG pipeline   │
  │                       │                     │                │ OpenAI call    │
  │                       │                     │                │ PUBLISH result │
  │                       │                     │                │───────────────►│
  │                       │ Redis delivers msg  │                │                │
  │                       │◄────────────────────────────────────────────────────│
  │  WS: {response: "..."}│                     │                │                │
  │◄──────────────────────│                     │                │                │
  │  [renders response]   │                     │                │                │
  │  WS close             │                     │                │                │
  │──────────────────────►│                     │                │                │
  │                       │ UNSUBSCRIBE         │                │                │
  │                       │────────────────────────────────────────────────────►│
```

---

## 9.10 Interview Questions and Answers

**Q: Walk me through exactly what happens from when a user sends a message to when they see the response.**

A: (Use the full flow above as your answer, phrased in your own words — this is the most important question)

**Q: At what point does the HTTP connection close in this flow?**

A: After the `POST /chat/message/queue` route returns `202 Accepted` with the `job_id`. The HTTP connection closes at ~10ms. The WebSocket connection then opens separately.

**Q: How does the system ensure the WebSocket is subscribed before the worker publishes?**

A: The POST endpoint publishes to RabbitMQ. The worker then needs to: dequeue the message from RabbitMQ, run embedding, run Milvus search, call OpenAI — all taking at minimum ~500ms. The WebSocket connection typically opens within ~100ms of the POST response. The subscription is ready well before the worker publishes.

**Q: What happens if the WebSocket opens after the worker has already published?**

A: The Redis Pub/Sub message is already delivered and gone. The WebSocket subscription would never receive it. The WebSocket would time out after 60 seconds. This is the race condition that the system's sequencing prevents by design.

---

## 9.11 Key Files Reference

| File | Phase |
|---|---|
| `backend/app/routers/auth.py` | Phase 1: Login |
| `backend/app/services/auth_service.py` | Phase 1: JWT creation |
| `backend/app/routers/chat.py` | Phase 2: Message endpoint |
| `backend/app/services/faq_service.py` | Phase 2: Cache check |
| `backend/app/services/rabbitmq_service.py` | Phase 2: Queue publish |
| `backend/app/routers/websocket.py` | Phase 3: WebSocket + Redis subscribe |
| `backend/app/worker/chat_worker.py` | Phase 4: Job processing |
| `backend/app/rag/` | Phase 4: RAG pipeline |
| `backend/app/services/redis_pubsub_service.py` | Phases 3, 4, 5: Subscribe/publish/deliver |
