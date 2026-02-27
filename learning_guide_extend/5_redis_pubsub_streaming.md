# 5. Redis Pub/Sub Streaming — Deep Technical Learning

---

## 5.1 Concept Introduction

**Redis Pub/Sub (Publish/Subscribe)** is a messaging pattern where:
- **Publishers** send messages to a named **channel** without knowing who is listening
- **Subscribers** subscribe to a channel and receive all messages published to it in real-time
- Redis acts as the **broker** in between

Think of it as a **radio broadcast:**
- The radio station (publisher) broadcasts on frequency 101.5 FM (channel)
- Every radio tuned to 101.5 FM (subscribers) hears the broadcast
- The station doesn't know who is listening
- The listeners don't communicate back through the radio

---

## 5.2 Why Redis Pub/Sub is Used in This Project

**The core problem:**

When the `ChatWorker` finishes processing an AI response, it has the answer. But the WebSocket handler (in a completely different code path, running in the FastAPI async event loop) needs that answer to send to the frontend.

**How to bridge the worker thread → WebSocket handler?**

```
Option 1: Shared in-memory variable
  Problem: Only works if worker and WebSocket handler are in the same process.
           In production with multiple servers, they won't be.

Option 2: Database polling
  Worker writes to DB. WebSocket handler polls DB every 0.5s.
  Problem: Latency (0-0.5s delay). Database overloaded with polls.

Option 3: Redis Pub/Sub  ← YOUR CHOICE
  Worker publishes to Redis channel.
  WebSocket handler subscribes to that channel.
  Message delivered in milliseconds.
  Works across multiple servers.
  No polling needed.
```

---

## 5.3 Pub/Sub vs Message Queue — Key Differences

| Feature | Pub/Sub (Redis) | Message Queue (RabbitMQ) |
|---|---|---|
| **Delivery** | Fire-and-forget | At-least-once guaranteed |
| **Persistence** | No — lost if no subscriber | Yes — messages stored in queue |
| **Consumers** | All subscribers get message | One consumer per message |
| **History** | No — subscriber must be live | Yes — queue holds unprocessed messages |
| **Use case** | Real-time notifications | Reliable job processing |
| **Your use** | Worker → WebSocket delivery | API → Worker job processing |

**Critical point:** Pub/Sub messages are **lost if no subscriber is listening**. This is why the design requires the WebSocket to subscribe BEFORE the worker publishes. The flow guarantees this:
1. WebSocket handler subscribes to channel (Step 1)
2. POST /chat/message/queue publishes job to RabbitMQ (Step 2)
3. Worker processes and publishes to Redis (Step 3)
4. WebSocket receives from Redis (Step 4)

The WebSocket is always subscribed before the worker can possibly publish.

---

## 5.4 Channel Naming Convention

Your system uses a naming convention for Redis channels:

```
chat_response:{session_id}
   └─────────┘ └─────────┘
   prefix       unique identifier
   (constant)   (from db session)

Examples:
  chat_response:42    ← Session 42's response channel
  chat_response:107   ← Session 107's response channel
  chat_response:8     ← Session 8's response channel
```

**Why include session_id in channel name?**
- Multiple users are chatting simultaneously
- Each needs their own channel
- Worker knows `session_id` from the job payload
- WebSocket knows `session_id` from the URL path (`/ws/chat/{session_id}`)
- They independently construct the same channel name — routing is implicit

---

## 5.5 Internal Working — Step-by-Step Lifecycle

### Subscribe Side (WebSocket Handler)

```python
# In routers/websocket.py
pubsub_service = get_redis_pubsub_service()

# 1. Create a PubSub object for this session
subscription = pubsub_service.subscribe(f"chat_response:{session_id}")

# 2. Block in asyncio.to_thread so event loop isn't blocked
message = await asyncio.to_thread(
    pubsub_service.listen_once, 
    subscription,
    timeout=WEBSOCKET_RESPONSE_TIMEOUT
)

# 3. Unsubscribe and clean up
pubsub_service.unsubscribe(subscription)
```

### Publish Side (ChatWorker)

```python
# In worker/chat_worker.py
channel_name = f"chat_response:{session_id}"

self._pubsub.publish(channel_name, {
    "job_id":       job_id,
    "session_id":   session_id,
    "response":     ai_response,
    "next_options": next_options,
    "status":       "success",
    "is_done":      True
})
```

### The `listen_once()` Mechanism

```python
# In services/redis_pubsub_service.py
def listen_once(self, pubsub: PubSub, timeout: float = 60.0):
    """
    Block until ONE message arrives on the subscribed channel, 
    then return it.
    """
    deadline = time.time() + timeout
    
    while time.time() < deadline:
        remaining = deadline - time.time()
        message = pubsub.get_message(
            ignore_subscribe_messages=True, 
            timeout=min(1.0, remaining)
        )
        if message and message["type"] == "message":
            return json.loads(message["data"])
    
    return None  # Timeout
```

---

## 5.6 asyncio.to_thread — Why It's Used

FastAPI is async. `pubsub.get_message()` is a **blocking** call (it waits for bytes from Redis). You cannot call blocking operations directly in an async function — it would freeze the event loop.

```
WRONG (blocks entire event loop — all WebSockets freeze):
async def websocket_chat(...):
    message = pubsub.get_message(...)  # BLOCKING inside async!

RIGHT (offloads blocking call to thread pool):
async def websocket_chat(...):
    message = await asyncio.to_thread(  # Non-blocking from event loop perspective
        pubsub_service.listen_once, 
        subscription, 
        timeout
    )
```

`asyncio.to_thread()` runs the blocking function in a thread pool executor. The event loop can serve other WebSocket connections while one is blocked in `listen_once()`.

---

## 5.7 Connection Pool Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   RedisPubSubService                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  _publish_client (connection pooled, shared)        │    │
│  │  → Used for all PUBLISH calls                       │    │
│  │  → max_connections=50                               │    │
│  │  → Thread-safe: pool manages connection checkout    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Per-subscription PubSub objects (one per WebSocket):        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ PubSub  │  │ PubSub  │  │ PubSub  │  ...               │
│  │ user 1  │  │ user 2  │  │ user 3  │                     │
│  │ session │  │ session │  │ session │                     │
│  │ #42     │  │ #107    │  │ #8      │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
│  Each has own Redis connection                               │
│  Each subscribes to own channel                              │
└──────────────────────────────────────────────────────────────┘
```

**Why separate subscription objects?**
Redis `PubSub` objects maintain their own redis connection after subscribing. Sharing one PubSub across multiple subscribers would mix their messages. Each WebSocket needs its own isolated subscription.

---

## 5.8 Message Format

Published message (JSON string in Redis):

```json
{
  "job_id":       "550e8400-e29b-41d4-a716-446655440000",
  "session_id":   42,
  "response":     "You can return products within 30 days...",
  "next_options": ["Tell me more", "Contact support", "View policy"],
  "status":       "success",
  "is_done":      true
}
```

`is_done: true` means this is the final message for this session. The WebSocket handler closes after receiving it.

---

## 5.9 What If Redis Restarts Mid-Request?

```
Timeline:
  T=0:  WebSocket opens, subscribes to chat_response:42
  T=1:  Job published to RabbitMQ
  T=5:  Redis crashes
  T=6:  Worker finishes processing
  T=6:  Worker tries to PUBLISH to Redis → ConnectionError
  T=6:  Worker catches error, logs it
  T=60: WebSocket times out → sends timeout error to client

Recovery:
  T=61: Redis restarts
  T=61: Worker reconnects (on next pub attempt)
  T=61: WebSocket subscription is gone (connection died at T=5)
```

**Result:** The user gets a timeout response. They must re-submit the message. The job has been ACKed by the worker (or NACKed and requeued). This is an edge case that requires frontend retry logic.

---

## 5.10 Graceful Degradation

Your `RedisPubSubService` is designed with graceful degradation:

```python
# From redis_pubsub_service.py
if not pubsub_service.is_available():
    await websocket.send_json({
        "response": "Streaming service is temporarily unavailable.",
        "status": "error",
        "is_done": True,
    })
    return
```

If Redis is not available when the WebSocket connects, it immediately returns an error instead of hanging. The user gets instant feedback instead of a 60-second timeout.

---

## 5.11 Interview Questions and Answers

**Q: What is the difference between Redis Pub/Sub and RabbitMQ?**

A: Redis Pub/Sub is fire-and-forget — messages are not stored. If no subscriber is listening when a message is published, it's lost. Redis Pub/Sub is for real-time delivery when the consumer is guaranteed to be online. RabbitMQ stores messages in a durable queue. Messages persist until a consumer ACKs them. RabbitMQ is for reliable job processing. Your system uses both for different purposes: RabbitMQ for job queuing (worker might not be immediately ready), Redis Pub/Sub for response delivery (WebSocket is always subscribed before the worker publishes).

**Q: How does the worker know which WebSocket connection to send the response to?**

A: Via the channel name. The channel is `chat_response:{session_id}`. The worker knows the `session_id` from the job payload. The WebSocket handler knows it from the URL path. They independently compute the same channel name, so the message routes correctly.

**Q: What happens if two users have the same session_id?**

A: `session_id` is a PostgreSQL primary key (auto-increment integer, unique). Two users cannot have the same session_id. Each user's WebSocket subscribes to a unique channel.

**Q: Why is `asyncio.to_thread` needed for Redis subscription?**

A: The Redis `pubsub.get_message()` call is blocking — it waits for network bytes from Redis. Calling blocking code inside an async function freezes the entire asyncio event loop, preventing all other requests from being served. `asyncio.to_thread()` runs the blocking call in a thread pool, allowing the event loop to continue serving other connections.

**Q: What is the timeout behavior for Redis Pub/Sub?**

A: The `listen_once()` method polls with 1-second intervals up to `WEBSOCKET_RESPONSE_TIMEOUT` (default 60 seconds). If no message arrives within the timeout, it returns `None`. The WebSocket handler then sends a timeout error to the client.

---

## 5.12 Common Mistakes

1. **Calling `pubsub.get_message()` without timeout** — If no message ever comes and timeout=None, the thread blocks forever.
2. **Sharing one PubSub object across all users** — Messages from different channels get mixed together.
3. **Not unsubscribing after receiving message** — Every subscription holds a Redis connection open. Connection pool exhausts after ~50 concurrent users.
4. **Calling blocking Redis in async context without `asyncio.to_thread()`** — Event loop freezes, all connections stall.
5. **Not handling Redis connection failure in subscribe path** — App crashes instead of returning error to user.
6. **Publishing before subscriber is ready** — Message lost if WebSocket hasn't subscribed yet.

---

## 5.13 Performance Considerations

- Each WebSocket connection uses one Redis connection for subscription
- With 1,000 concurrent WebSocket users, you need 1,000+ Redis connections
- Set `max_connections` in connection pool appropriately
- Use Redis Cluster for high availability and horizontal scaling of Pub/Sub
- Consider Redis Streams for Pub/Sub with message persistence (unlike plain Pub/Sub)
- Monitor Redis memory usage — high throughput channels can spike memory

---

## 5.14 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/services/redis_pubsub_service.py` | Full Pub/Sub implementation: subscribe, publish, listen_once, unsubscribe |
| `backend/app/routers/websocket.py` | WebSocket handler — subscribe and listen |
| `backend/app/worker/chat_worker.py` | Worker — publish result after processing |
| `backend/app/config.py` | `REDIS_HOST`, `REDIS_PUBSUB_CHANNEL_PREFIX`, `WEBSOCKET_RESPONSE_TIMEOUT` |
