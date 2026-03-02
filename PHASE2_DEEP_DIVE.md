# Phase 2 Deep Dive — JWT · Redis FAQ Cache · RabbitMQ · Redis Pub/Sub · WebSocket

> **What this document covers**
> A complete, code-level explanation of everything you built in Phase 2 of your chatbot project.
> For every feature you will find: what it is, why it exists, how it works, which file/function does what, code snippets from your actual project, and the exact data-flow from request to response.

---

## Table of Contents

1. [Big Picture — How Phase 2 Fits Together](#1-big-picture)
2. [JWT Authentication](#2-jwt-authentication)
3. [Redis FAQ Cache](#3-redis-faq-cache)
4. [RabbitMQ Message Queue](#4-rabbitmq-message-queue)
5. [Redis Pub/Sub](#5-redis-pubsub)
6. [WebSocket Streaming](#6-websocket)
7. [Complete Async Chat Flow (all pieces together)](#7-complete-async-chat-flow)
8. [Configuration Reference](#8-configuration-reference)
9. [Key Concepts You Should Know](#9-key-concepts)

---

## 1. Big Picture

```
Phase 1 (what you already had)
-------------------------------
Browser → POST /chat/message → FastAPI → Workflow / FAQ / RAG → response

Phase 2 (what you added)
-------------------------------
1. Every chatbot management endpoint is now protected by JWT tokens.
2. FAQ lookups go through Redis cache first (avoids repeated DB queries).
3. RAG queries go to RabbitMQ so they run in a background worker.
4. The worker publishes the result to Redis Pub/Sub.
5. A WebSocket endpoint subscribes to Pub/Sub and streams the result to the browser.
```

### Directory Map (Phase 2 files only)

```
backend/
  app/
    config.py                        ← all env-var constants (JWT, Redis, RabbitMQ)
    models/
      user.py                        ← User database model
    schemas/
      auth.py                        ← Pydantic validation for register/login
    routers/
      auth.py                        ← POST /auth/register, /auth/login, GET /auth/me
      websocket.py                   ← WS  /ws/chat/{session_id}/{job_id}
      chat.py                        ← POST /chat/message/queue  (new async endpoint)
    services/
      auth_service.py                ← hash_password, verify_password, create/decode token
      faq_service.py                 ← FAQService class (cache-first FAQ lookups)
      redis_cache_service.py         ← RedisCacheService (generic get/set/delete/TTL)
      redis_pubsub_service.py        ← RedisPubSubService (publish / subscribe / listen)
      rabbitmq_service.py            ← RabbitMQService (connect / publish / consume)
    dependencies/
      auth.py                        ← get_current_user, get_current_admin_user (FastAPI Depends)
      cache.py                       ← get_faq_service (FastAPI Depends)
    worker/
      chat_worker.py                 ← ChatWorker (RabbitMQ consumer → RAG → Pub/Sub)

frontend/
  services/
    api.ts                           ← queueMessage(), auth API calls, WS_BASE_URL
```

---

## 2. JWT Authentication

### What is JWT?

JWT (JSON Web Token) is a compact, self-contained token.
Instead of storing a session in the database, all user info is **encoded inside the token itself** and sent to the browser. The browser attaches the token to every subsequent request. The server just decodes it — no database lookup needed.

A JWT looks like this:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9   ← Header (algorithm + type)
.eyJzdWIiOjEsImVtYWlsIjoiYUBiLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzA5MDAwMDAwfQ==  ← Payload (your data)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ← Signature (proves it wasn't tampered)
```

### Your Token Payload

```python
# backend/app/services/auth_service.py
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    # Set expiration — default 30 minutes (configurable via ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,           # expiry timestamp
        "iat": datetime.utcnow() # issued-at timestamp
    })

    # Sign with SECRET_KEY using HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

When you call `login`, the token is created like this:
```python
# backend/app/routers/auth.py
access_token = create_access_token(
    data={
        "sub": user.id,      # subject = user ID (integer)
        "email": user.email,
        "role": user.role    # "user" or "admin"
    }
)
```

So the payload stored inside the JWT is `{ sub: 1, email: "a@b.com", role: "user", exp: ..., iat: ... }`.

---

### Auth Flow — Step by Step

```
1. Register
   Browser → POST /auth/register  { email, username, password }
   Server  → hashes password with bcrypt, saves User row, returns user info (no token yet)

2. Login
   Browser → POST /auth/login  { email, password }
   Server  → finds user, verifies bcrypt hash, creates JWT, returns token
   Browser → stores token in localStorage as "access_token"

3. Protected Request
   Browser → GET /chatbots  with header:  Authorization: Bearer <token>
   Server  → extracts token, decodes it, loads User from DB, proceeds

4. Token Expired
   Server  → returns 401
   Browser → clears localStorage, fires "auth:logout" event (api.ts line ~63)
```

---

### Functions and What They Do

#### `hash_password(password)` — `auth_service.py`

```python
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

- Uses **bcrypt** — a one-way hashing algorithm specifically designed for passwords.
- Every call produces a different hash (bcrypt adds a random salt internally).
- You can never reverse a bcrypt hash back to the original password.

#### `verify_password(plain, hashed)` — `auth_service.py`

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

- Takes the plain text the user typed and the stored hash.
- Returns `True` if they match, `False` otherwise.

#### `decode_access_token(token)` — `auth_service.py`

```python
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None   # expired, tampered, or wrong key
```

- Returns the decoded dict (the payload) if the token is valid.
- Returns `None` if the token is invalid, expired, or tampered.

#### `get_current_user` — `dependencies/auth.py`

This is a **FastAPI dependency** — you add it to a route and FastAPI automatically runs it before the route handler.

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials        # extract the raw JWT string
    payload = decode_access_token(token)   # decode and verify
    if payload is None:
        raise HTTPException(401, "Invalid or expired token")

    user_id = payload.get("sub")           # get user ID from token
    user = db.query(User).filter(User.id == user_id).first()  # load from DB
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return user
```

Usage in a route:
```python
@router.get("/chatbots")
def list_chatbots(current_user: User = Depends(get_current_user)):
    # current_user is guaranteed to be a valid, active user
    ...
```

#### `get_current_admin_user` — `dependencies/auth.py`

```python
def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user
```

Chains on top of `get_current_user`. Only allows users with `role == "admin"`.

---

### User Database Model — `models/user.py`

```python
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False)
    username      = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)   # bcrypt hash stored here
    full_name     = Column(String(255), nullable=True)
    role          = Column(String(50), default="user")    # "user" or "admin"
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, server_default=func.now())
```

**Important**: The plain text password is NEVER stored. Only `password_hash` is saved.

---

### Frontend — How JWT is sent

```typescript
// frontend/services/api.ts
const token = localStorage.getItem('access_token');
if (token) {
    headers['Authorization'] = `Bearer ${token}`;
}
```

Every `request()` call automatically reads the token from `localStorage` and adds it to the `Authorization` header. If the server returns `401`, the token is cleared and a logout event fires.

---

## 3. Redis FAQ Cache

### Why Cache FAQs?

Every time a user sends a message that matches an FAQ, your code was doing a SQL query like:
```sql
SELECT * FROM faqs WHERE chatbot_id = ? AND question = ? AND is_active = true
```

If thousands of users ask the same FAQ simultaneously, this query runs thousands of times. Redis caching means:

1. **First request** → hit DB → store result in Redis (1 second)
2. **Second request (within 1 hour)** → hit Redis → return instantly (< 1ms)

### Cache Key Design

```python
# backend/app/services/faq_service.py
def _generate_cache_key(self, chatbot_id: int, question: str) -> str:
    normalized = question.lower().strip()              # "Hello?" → "hello?"
    question_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]  # short hash
    return f"faq:chatbot:{chatbot_id}:{question_hash}"
    # Example: "faq:chatbot:1:a3f5c8d9e2b1"
```

Child FAQ cache key:
```python
def _generate_children_cache_key(self, chatbot_id: int, parent_id: int) -> str:
    return f"faq:children:chatbot:{chatbot_id}:parent:{parent_id}"
    # Example: "faq:children:chatbot:1:parent:5"
```

**Why hash?** The question text could contain special characters or be very long. A short 12-char hash makes a clean, consistent key.

---

### Cache-First Strategy — `get_faq_by_question()`

```python
# backend/app/services/faq_service.py
def get_faq_by_question(self, chatbot_id, question, db, use_cache=True):
    cache_key = self._generate_cache_key(chatbot_id, question)

    # ── Step 1: Try Redis first ──────────────────────────────────────────────
    if use_cache and self.cache.is_available():
        cached_data = self.cache.get(cache_key)
        if cached_data:
            # Cache HIT — reconstruct FAQ object without touching the database
            return FAQ(**cached_data)

    # ── Step 2: Cache MISS — query the database ──────────────────────────────
    faq = db.query(FAQ).filter(
        FAQ.chatbot_id == chatbot_id,
        FAQ.question == question,
        FAQ.is_active == True
    ).first()

    # ── Step 3: Store in cache for next time (TTL = 1 hour by default) ───────
    if faq and use_cache:
        self.cache.set(cache_key, self._faq_to_dict(faq), ttl=FAQ_CACHE_TTL)

    return faq
```

**Flow**:
```
User sends "What is your return policy?"
         ↓
FAQService.get_faq_by_question()
         ↓
Is Redis available? Yes
         ↓
cache.get("faq:chatbot:1:a3f5c8d9e2b1")
         ↓
[Cache HIT] → return FAQ immediately (no DB)
[Cache MISS] → query DB → store in Redis → return FAQ
```

---

### RedisCacheService — `services/redis_cache_service.py`

This is a generic key-value cache layer. The FAQ service uses it, but any service could use it.

#### `get(key)` — Read from cache

```python
def get(self, key: str) -> Optional[Any]:
    if not self.is_available():
        return None   # graceful fallback: cache offline = query DB
    
    value = self._client.get(key)
    if value is None:
        return None   # cache miss

    return json.loads(value)   # deserialize JSON back to Python dict
```

#### `set(key, value, ttl)` — Write to cache

```python
def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    serialized = json.dumps(value)    # convert dict → JSON string

    if ttl:
        self._client.setex(key, ttl, serialized)   # expires after `ttl` seconds
    else:
        self._client.set(key, serialized)          # no expiration

    return True
```

#### `delete(key)` — Invalidate cache entry

```python
def delete(self, key: str) -> bool:
    result = self._client.delete(key)
    return result > 0   # True if key existed and was deleted
```

This is called whenever an FAQ is updated or deleted so stale data never gets served.

#### `delete_pattern(pattern)` — Bulk delete

```python
def delete_pattern(self, pattern: str) -> int:
    # Example pattern: "faq:chatbot:1:*"
    # Deletes ALL cache keys for chatbot 1
    keys = self._client.keys(pattern)
    if keys:
        return self._client.delete(*keys)
    return 0
```

---

### TTL (Time-To-Live)

```python
# config.py
FAQ_CACHE_TTL: int = int(os.getenv("FAQ_CACHE_TTL", "3600"))  # 1 hour in seconds
```

- After 3600 seconds (1 hour), Redis automatically removes the key.
- The next request will be a cache miss and will reload from DB.
- This prevents stale FAQ answers from being served indefinitely.

---

### Connection Pool

```python
# redis_cache_service.py  (constructor)
pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,    # auto-decode bytes → str
    max_connections=50,       # up to 50 simultaneous Redis connections
)
self._client = redis.Redis(connection_pool=pool)
```

Without a connection pool, every `get()` or `set()` would open+close a TCP connection to Redis — very slow. With a pool, connections are reused.

---

## 4. RabbitMQ Message Queue

### Why a Message Queue?

RAG (searching your PDFs with AI) is slow — it can take 3–10 seconds. If your `/chat/message` endpoint waited for the RAG result before responding, the HTTP request would hang for 10 seconds. That's bad UX and can cause request timeouts.

**Solution**: Put the RAG job in a queue and return immediately. The browser then opens a WebSocket to receive the result when it's ready.

```
Without queue:
  Browser → POST /chat/message → [wait 8 seconds] → response

With queue:
  Browser → POST /chat/message/queue → [instant 202 response] → "job queued"
  Browser → opens WebSocket
  Worker  → processes RAG → publishes result
  Browser → receives result via WebSocket
```

---

### RabbitMQ Concepts Applied in Your Project

| Concept | Your Value | Meaning |
|---|---|---|
| Queue | `rag_processing_queue` | The list where jobs wait |
| Exchange | `""` (default) | Direct routing (no fanout) |
| Routing Key | `rag_processing_queue` | Which queue to send to |
| Durability | `durable=True` | Queue survives RabbitMQ restart |
| Persistence | `delivery_mode=2` | Message survives RabbitMQ restart |
| Prefetch | `prefetch_count=1` | Worker processes one job at a time |

---

### RabbitMQService Functions

#### `connect()` — Establish connection

```python
# backend/app/services/rabbitmq_service.py
def connect(self) -> bool:
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=60,                   # keep connection alive every 60s
        blocked_connection_timeout=300, # wait 5 min if broker is busy
    )
    self._connection = pika.BlockingConnection(parameters)
    self._channel = self._connection.channel()

    # Check if queue exists (passive=True won't create it or change params)
    self._channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, passive=True)
    return True
```

#### `publish_message(message)` — Put job in queue

```python
def publish_message(self, message: Dict[str, Any], ...) -> bool:
    body = json.dumps(message)      # dict → JSON string
    self._channel.basic_publish(
        exchange="",                # default exchange
        routing_key=RABBITMQ_QUEUE_NAME,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,        # persistent — survives broker restart
            content_type="application/json",
        ),
    )
    return True
```

**Auto-reconnect**: If the connection dropped (stale socket), `publish_message` catches the error, reconnects, and retries once before giving up.

#### `consume_messages(callback)` — Start worker loop

```python
def consume_messages(self, callback, prefetch_count=1):
    self._channel.basic_qos(prefetch_count=prefetch_count)  # one at a time

    def _on_message(ch, method, properties, body):
        message = json.loads(body)        # JSON → dict
        callback(message)                 # call user's handler
        ch.basic_ack(delivery_tag=method.delivery_tag)  # tell RabbitMQ: done

    self._channel.basic_consume(
        queue=RABBITMQ_QUEUE_NAME,
        on_message_callback=_on_message
    )
    self._channel.start_consuming()       # blocks — runs forever
```

If `callback` throws an exception, the message is `basic_nack`'ed (rejected) and put back in the queue.

---

### Job Message Format

```python
# Published to RabbitMQ by POST /chat/message/queue
{
    "job_id":       "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "session_id":   42,          # chat session ID
    "user_message": "What does section 3.2 say about refunds?"
}
```

---

### The Queue Endpoint — `POST /chat/message/queue`

```python
# backend/app/routers/chat.py
@router.post("/message/queue", status_code=202)
def queue_message(request, db, faq_service):
    job_id = str(uuid.uuid4())   # generate unique job ID

    # Step 1: Check workflow node and FAQ first (fast — no queue needed)
    sync_response, sync_options = check_sync_response(
        session_id=request.session_id,
        user_message=request.message,
        db=db,
        faq_service=faq_service,
    )

    if sync_response is not None:
        # Workflow or FAQ matched → return immediately, no queue
        return ChatQueueResponse(queued=False, cache_hit=True, bot_response=sync_response)

    # Step 2: No static match → publish to RabbitMQ for RAG processing
    job_payload = {
        "job_id":       job_id,
        "session_id":   request.session_id,
        "user_message": request.message,
    }
    rabbitmq_service.publish_message(job_payload)

    # Return 202 Accepted immediately
    return ChatQueueResponse(job_id=job_id, session_id=request.session_id, queued=True)
```

**Key point**: The endpoint returns in milliseconds even if RAG takes 10 seconds, because the actual RAG work happens in the ChatWorker background thread.

---

## 5. Redis Pub/Sub

### What is Pub/Sub?

Pub/Sub (Publish/Subscribe) is a messaging pattern where:
- A **publisher** sends a message to a **channel** (doesn't know who receives it)
- One or more **subscribers** receive messages from that channel in real time

In your project:
- **Publisher** = ChatWorker (publishes RAG result)
- **Channel** = `rag_stream:{job_id}` (one channel per job)
- **Subscriber** = WebSocket endpoint (one per connected browser tab)

```
ChatWorker ──publish──► "rag_stream:550e8400" ──subscribe──► WebSocket handler
```

---

### Channel Naming

```python
# config.py
REDIS_PUBSUB_CHANNEL_PREFIX: str = "chat_response"  # legacy prefix in code

# redis_pubsub_service.py — in practice uses:
channel = f"rag_stream:{job_id}"
# e.g.: "rag_stream:550e8400-e29b-41d4-a716-446655440000"
```

One unique channel per job (by UUID). This means multiple concurrent users each get their own channel — no cross-talk.

---

### RedisPubSubService Functions

#### `publish(channel, message)` — Send message

```python
def publish(self, channel: str, message: Dict[str, Any]) -> bool:
    body = json.dumps(message)                   # dict → JSON string
    receivers = self._publish_client.publish(channel, body)
    # receivers = number of subscribers that received the message
    return True
```

#### `publish_to_session(session_id, message)` — Convenience wrapper

```python
def publish_to_session(self, session_id: int, message: Dict[str, Any]) -> bool:
    channel = self.get_channel_name(session_id)  # "chat_response:42"
    return self.publish(channel, message)
```

#### `subscribe(channel)` — Start listening

```python
def subscribe(self, channel: str) -> Optional[PubSub]:
    # Creates a dedicated connection just for subscribing
    # (pub/sub cannot share a connection used for regular commands)
    sub_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, ...)
    pubsub = sub_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel)
    return pubsub    # caller uses this object to receive messages
```

**Important**: Pub/Sub subscriptions need their own Redis connection — you cannot reuse the same connection that does `GET`/`SET`. That's why `subscribe()` creates a new connection each time.

#### `collect_job_response(job_id, timeout)` — Full response collection

This is the smart function that handles both your internal worker and a Docker-based worker:

```python
def collect_job_response(self, job_id: str, timeout: float = 60.0):
    channel = f"rag_stream:{job_id}"
    buffer_key = f"rag_buffer:{job_id}"

    # ── Path A: Docker worker buffered replay ────────────────────────────────
    # Docker worker stores each token in a Redis List before publishing
    # If we are late to subscribe, we missed the Pub/Sub messages.
    # Reading the buffer replays them.
    buffered = self._publish_client.lrange(buffer_key, 0, -1)
    if buffered:
        tokens = []
        for raw in buffered:
            msg = json.loads(raw)
            if msg["type"] == "token":
                tokens.append(msg["content"])
            elif msg["type"] == "complete":
                return {"response": "".join(tokens), "status": "success", "is_done": True}

    # ── Path B: Live Pub/Sub subscription ────────────────────────────────────
    # Subscribe and wait for the worker to publish
    pubsub_conn = self.subscribe(channel)
    deadline = time.monotonic() + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None   # timeout

        msg_raw = pubsub_conn.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg_raw is None:
            continue      # no message yet, keep waiting

        msg = json.loads(msg_raw["data"])

        # Internal ChatWorker sends a single complete message
        if msg.get("is_done") or msg.get("status") in ("success", "error"):
            return {"response": msg["response"], "status": msg["status"], "is_done": True}
```

#### `listen_once(pubsub, timeout)` — Wait for exactly one message

```python
def listen_once(self, pubsub: PubSub, timeout: float = 30.0):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None      # timed out, no message arrived

        message = pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=min(1.0, remaining)  # poll in 1-second windows
        )
        if message and message.get("type") == "message":
            return json.loads(message["data"])   # return the payload
```

---

### Response Message Published by ChatWorker

```python
# Success
{
    "job_id":       "550e8400-...",
    "session_id":   42,
    "response":     "Section 3.2 states that refunds must be requested within 30 days...",
    "next_options": [],
    "status":       "success",
    "is_done":      True
}

# Error
{
    "job_id":       "550e8400-...",
    "session_id":   42,
    "response":     "An error occurred while processing your request.",
    "next_options": [],
    "status":       "error",
    "is_done":      True
}
```

---

## 6. WebSocket

### What is a WebSocket?

WebSocket is a **persistent, two-way connection** between browser and server. Unlike HTTP (request → response → connection closes), a WebSocket stays open. Either side can send a message at any time.

In your project you only use it one-way (server → browser) to push the RAG result when the ChatWorker finishes.

---

### The WebSocket Endpoint — `routers/websocket.py`

```python
@router.websocket("/ws/chat/{session_id}/{job_id}")
async def websocket_chat(websocket: WebSocket, session_id: int, job_id: str):
    # Step 1: Accept the connection (completes the WebSocket handshake)
    await websocket.accept()

    pubsub_service = get_redis_pubsub_service()

    # Step 2: Collect the full RAG response
    # asyncio.to_thread() runs the blocking Redis poll in a thread pool
    # so it doesn't block FastAPI's async event loop
    result = await asyncio.to_thread(
        pubsub_service.collect_job_response,
        job_id,
        WEBSOCKET_RESPONSE_TIMEOUT,  # 60 seconds default
    )

    # Step 3: Send result to browser
    if result is None:
        await websocket.send_json({
            "response": "Request timed out. Please try again.",
            "status": "error",
            "is_done": True,
        })
    else:
        await websocket.send_json(result)

    # Step 4: Close cleanly
    await websocket.close()
```

#### Why `asyncio.to_thread()`?

`collect_job_response` uses a blocking Redis poll loop (it sleeps and polls every second). If you `await` it directly in an async function, it would **block FastAPI's entire event loop** — no other requests could be processed while waiting. `asyncio.to_thread()` moves the blocking function to a separate OS thread, letting the event loop keep running freely.

---

### Frontend WebSocket Usage — `services/api.ts`

```typescript
// Step 1: Send message to queue endpoint
const result = await queueMessage(sessionId, message);

if (result.cache_hit) {
    // Workflow or FAQ matched — no WebSocket needed
    displayResponse(result.bot_response);
} else {
    // RAG path — open WebSocket to wait for worker result
    const ws = new WebSocket(
        `${WS_BASE_URL}/ws/chat/${result.session_id}/${result.job_id}`
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        displayResponse(data.response);
        ws.close();
    };

    ws.onerror = () => {
        displayError("Connection error");
    };
}
```

---

### ChatWorker — `worker/chat_worker.py`

The ChatWorker runs in a **background thread** (started when FastAPI starts) and processes jobs from RabbitMQ.

```python
class ChatWorker:
    def _process_job(self, message: Dict[str, Any]) -> None:
        job_id     = message["job_id"]
        session_id = message["session_id"]
        user_message = message["user_message"]

        db = self._get_db_session()

        # Run RAG pipeline (Workflow + FAQ already checked in REST endpoint)
        from app.services.chat_service import process_rag_message
        bot_response, next_options, _session = process_rag_message(
            session_id=session_id,
            user_message=user_message,
            db=db,
        )

        # Publish result to Redis Pub/Sub → WebSocket picks it up
        self._publish_response(job_id, session_id, {
            "job_id":       job_id,
            "session_id":   session_id,
            "response":     bot_response,
            "next_options": next_options,
            "status":       "success",
            "is_done":      True,
        })
```

```python
def _publish_response(self, job_id, session_id, payload):
    channel = f"rag_stream:{job_id}"
    self._pubsub.publish(channel, payload)
```

---

### Worker Startup

```python
# backend/app/main.py  (startup event)
@app.on_event("startup")
async def startup_event():
    ...
    worker = ChatWorker()
    thread = threading.Thread(target=worker.start, daemon=True)
    thread.start()
```

The worker is a **daemon thread** — it runs in the background and dies automatically when the main FastAPI process exits.

---

## 7. Complete Async Chat Flow

This shows all five Phase 2 systems working together for a RAG query:

```
Browser                  FastAPI                  RabbitMQ            ChatWorker           Redis
  │                         │                         │                    │                  │
  │  POST /chat/message/queue                          │                    │                  │
  │  { session_id: 42,       │                         │                    │                  │
  │    message: "refunds?" } │                         │                    │                  │
  │─────────────────────────►│                         │                    │                  │
  │                         │── check workflow nodes ──┤                    │                  │
  │                         │── check Redis FAQ cache──┼────────────────────┼─────────────────►│
  │                         │◄─────────────────────────┼────────────────────┼──────── miss ────│
  │                         │── publish job ──────────►│                    │                  │
  │◄── 202 { job_id, queued: true } ─────────────────  │                    │                  │
  │                         │                         │                    │                  │
  │  WS /ws/chat/42/{job_id}│                         │                    │                  │
  │─────────────────────────►│                         │                    │                  │
  │                         │── subscribe ─────────────┼────────────────────┼─────────────────►│
  │                         │        [waiting...]      │                    │                  │
  │                         │                         │── consume job ─────►│                  │
  │                         │                         │                    │── RAG query ─────►│
  │                         │                         │                    │◄── answer ────────│
  │                         │                         │                    │── publish result──►│
  │                         │◄─────────────────────── Pub/Sub message ─────┼──────────────────│
  │◄── WS JSON response ────│                         │                    │                  │
  │                         │                         │                    │                  │
```

### Step-by-Step Summary

| Step | What Happens | File |
|---|---|---|
| 1 | Browser POSTs to `/chat/message/queue` | `routers/chat.py` |
| 2 | Endpoint checks workflow nodes (DB query) | `chat_service.py` |
| 3 | Endpoint checks FAQ cache (Redis first, then DB) | `faq_service.py` |
| 4 | No match → publish job to RabbitMQ | `rabbitmq_service.py` |
| 5 | Return 202 Accepted + job_id to browser | `routers/chat.py` |
| 6 | Browser opens WebSocket `/ws/chat/{session_id}/{job_id}` | `frontend/services/api.ts` |
| 7 | WebSocket handler subscribes to Redis channel `rag_stream:{job_id}` | `routers/websocket.py` |
| 8 | ChatWorker thread picks up job from RabbitMQ | `worker/chat_worker.py` |
| 9 | ChatWorker runs RAG pipeline | `chat_service.py` |
| 10 | ChatWorker publishes result to Redis `rag_stream:{job_id}` | `redis_pubsub_service.py` |
| 11 | WebSocket handler receives message from Redis | `redis_pubsub_service.py` |
| 12 | WebSocket sends JSON to browser | `routers/websocket.py` |
| 13 | Browser displays response, closes WebSocket | `frontend/services/api.ts` |

---

## 8. Configuration Reference

All configuration lives in `backend/app/config.py` and reads from a `.env` file.

### JWT

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `your-secret-key-...` | Signs JWT tokens — change in production! |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token validity duration |

### Redis

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis server address |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number (0–15) |
| `REDIS_PASSWORD` | `""` | Redis auth (empty = no password) |
| `CACHE_ENABLED` | `true` | Master switch for FAQ caching |
| `FAQ_CACHE_TTL` | `3600` | Seconds before FAQ cache expires (1 hour) |
| `WEBSOCKET_RESPONSE_TIMEOUT` | `60` | Max seconds WebSocket waits for worker |

### RabbitMQ

| Variable | Default | Purpose |
|---|---|---|
| `RABBITMQ_HOST` | `localhost` | RabbitMQ broker address |
| `RABBITMQ_PORT` | `5672` | AMQP port |
| `RABBITMQ_USER` | `guest` | Broker username |
| `RABBITMQ_PASS` | `guest` | Broker password |
| `RABBITMQ_QUEUE_NAME` | `rag_processing_queue` | Queue for chat jobs |
| `WORKER_PREFETCH_COUNT` | `1` | Jobs processed in parallel per worker |

---

## 9. Key Concepts

### Graceful Degradation

Every Phase 2 service is optional. If Redis or RabbitMQ is unavailable:
- Redis cache: `is_available()` returns `False` → code falls through to DB query
- RabbitMQ: `/chat/message/queue` returns HTTP 503
- WebSocket: sends error JSON, closes connection

Your chatbot never crashes; it just degrades gracefully.

### Singletons

```python
# redis_pubsub_service.py  (bottom of file)
_redis_pubsub_service: Optional[RedisPubSubService] = None

def get_redis_pubsub_service() -> RedisPubSubService:
    global _redis_pubsub_service
    if _redis_pubsub_service is None:
        _redis_pubsub_service = RedisPubSubService()
    return _redis_pubsub_service
```

The service objects (Redis, RabbitMQ) are created once and reused. Creating a new Redis connection for every HTTP request would be very slow.

### FastAPI `Depends()`

`Depends()` is FastAPI's dependency injection. It calls a function before your route handler, and the return value is passed as a parameter. This is how JWT protection is added to routes without duplicating logic:

```python
@router.get("/chatbots")
def list_chatbots(current_user: User = Depends(get_current_user)):
    # FastAPI automatically called get_current_user() and passed the result here
    ...
```

### Thread Safety

`RabbitMQService.publish_message()` uses a `threading.Lock()`:

```python
with self._lock:
    self._channel.basic_publish(...)
```

Because multiple FastAPI request threads might call `publish_message()` at the same time, the lock ensures only one thread uses the RabbitMQ channel at a time (the pika library is not thread-safe by default).

### bcrypt vs MD5

- **bcrypt** (for passwords): intentionally slow, uses a random salt, cannot be reversed. Designed to resist brute-force attacks.
- **MD5** (for FAQ cache keys): fast, deterministic, used only to make a consistent short key. NOT for security. The FAQ question itself is not sensitive.

### Message Acknowledgement in RabbitMQ

```python
ch.basic_ack(delivery_tag=method.delivery_tag)   # success: remove from queue
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # failure: put back
ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # bad message: discard
```

Until a message is acknowledged (`ack`), RabbitMQ holds it. If the worker crashes, RabbitMQ re-delivers the message to another worker. This guarantees no job is lost.

### `asyncio.to_thread()` vs `await`

| `await some_coroutine()` | `await asyncio.to_thread(some_blocking_fn)` |
|---|---|
| Runs async code on the event loop | Runs blocking code on a thread pool |
| Does not block other requests | Does not block other requests |
| Cannot call blocking I/O | Can call blocking I/O (e.g., Redis poll) |

Use `asyncio.to_thread()` whenever you need to call a synchronous library (like `redis-py` or `pika`) from an `async` FastAPI route.

---

*This document was generated from the actual source code of your project. Every code snippet is from real files in your workspace.*
