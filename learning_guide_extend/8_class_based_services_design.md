# 8. Class-Based Services Design — Deep Technical Learning

---

## 8.1 Concept Introduction

**Class-based services** is an architectural pattern where business logic is encapsulated in classes rather than standalone functions. Each service class:
- Manages its own state (connections, configuration, internal flags)
- Exposes a clear public interface (methods)
- Handles its own initialization, connection, and teardown
- Is testable in isolation by mocking dependencies

Your entire `services/` directory follows this pattern: `RabbitMQService`, `RedisCacheService`, `RedisPubSubService`, `FaqService`, `ChatService`, `AuthService`.

---

## 8.2 Why Class-Based Over Function-Based

**Function-based (procedural) approach:**
```python
# functions/rabbitmq.py
_connection = None
_channel = None

def connect():
    global _connection, _channel
    _connection = pika.BlockingConnection(...)
    _channel = _connection.channel()

def publish(message):
    global _channel
    _channel.basic_publish(...)
```

**Problems:**
- Global state is dangerous in concurrent environments
- Hard to test — you can't easily create two instances with different configs
- Hard to mock in tests
- State scattered across module-level variables
- No clear ownership of the connection lifecycle

**Class-based approach (your system):**
```python
class RabbitMQService:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._lock = threading.Lock()
    
    def connect(self) -> bool:
        ...
    
    def publish(self, message: dict) -> bool:
        ...
```

**Benefits:**
- State is encapsulated (lives on `self`)
- Multiple instances possible (e.g., test instance vs production instance)
- Easy to mock: `mock_rabbitmq = MagicMock(spec=RabbitMQService)`
- Clear lifecycle: `__init__` → `connect()` → `publish()` → `disconnect()`
- Thread-safe via instance-level lock

---

## 8.3 Separation of Concerns

Each service in your system has **one clear responsibility**:

```
services/
├── auth_service.py          → Password hashing, JWT operations ONLY
├── rabbitmq_service.py      → RabbitMQ connection, publish, consume ONLY
├── redis_cache_service.py   → Redis get/set/delete/TTL ONLY
├── redis_pubsub_service.py  → Redis publish/subscribe ONLY
├── faq_service.py           → FAQ lookup + cache logic ONLY
├── chat_service.py          → Chat session management ONLY
├── rag_service.py           → Vector search + LLM integration ONLY
├── pdf_processing_service.py → PDF parsing + embedding ONLY
└── minio_storage.py         → File upload/download ONLY
```

**Why this matters:**
- A bug in caching doesn't affect RabbitMQ logic
- You can swap the cache from Redis to Memcached by changing only `redis_cache_service.py`
- A new developer can understand one service completely in isolation
- Each service can be unit tested independently

---

## 8.4 Dependency Injection Pattern

**Dependency Injection (DI)** means a class receives its dependencies (other objects it needs) from outside, rather than creating them internally.

**Without DI (tightly coupled):**
```python
class ChatWorker:
    def __init__(self):
        self._rabbitmq = RabbitMQService()   # Hard-coded dependency
        self._pubsub = RedisPubSubService()   # Hard-coded dependency
```

**Problems:**
- Cannot test `ChatWorker` in isolation — it always creates real RabbitMQ and Redis connections
- Cannot swap implementation (e.g., use a mock broker in tests)

**With DI (your implementation — loosely coupled):**
```python
class ChatWorker:
    def __init__(
        self,
        rabbitmq_service: Optional[RabbitMQService] = None,
        pubsub_service: Optional[RedisPubSubService] = None,
    ):
        self._rabbitmq = rabbitmq_service or RabbitMQService()
        self._pubsub = pubsub_service or get_redis_pubsub_service()
```

**Benefits:**
- In production: `ChatWorker()` — creates real services
- In tests: `ChatWorker(rabbitmq_service=mock_rabbitmq, pubsub_service=mock_pubsub)` — uses mocks
- In integration test: `ChatWorker(rabbitmq_service=test_rabbitmq)` — uses test queue

---

## 8.5 FastAPI Dependency Injection

FastAPI has a built-in DI system via `Depends()`. Your project uses this to inject services into route handlers:

```python
# In dependencies/
def get_rabbitmq_service() -> RabbitMQService:
    return rabbitmq_service  # Return singleton instance

# In a router
@router.post("/chat/message/queue")
async def queue_message(
    request: ChatRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

**What FastAPI DI does:**
1. Before calling the route function, FastAPI calls all `Depends(...)` functions
2. Their return values are injected as parameters
3. If any dependency raises `HTTPException`, the route is not called at all
4. Dependencies can have their own dependencies (hierarchical)

---

## 8.6 Singleton Pattern for Services

Services like `RabbitMQService` and `RedisPubSubService` use the **singleton pattern** — only one instance exists for the entire application lifecycle:

```python
# In services/redis_pubsub_service.py
_redis_pubsub_service: Optional[RedisPubSubService] = None

def get_redis_pubsub_service() -> RedisPubSubService:
    global _redis_pubsub_service
    if _redis_pubsub_service is None:
        _redis_pubsub_service = RedisPubSubService()
    return _redis_pubsub_service
```

**Why singletons for services?**
- Connection pools are expensive to create — create once, reuse always
- All routes share the same connection pool efficiently
- Configuration loaded once at startup
- State (connected/disconnected) managed in one place

---

## 8.7 SOLID Principles in Your Codebase

**S — Single Responsibility Principle:**
Each service class has one job. `RedisCacheService` only caches. `RabbitMQService` only queues. They don't overlap.

**O — Open/Closed Principle:**
Services are open for extension (you can subclass to add monitoring), closed for modification (you don't change `RabbitMQService` to add caching).

**L — Liskov Substitution Principle:**
Any class that satisfies the `RabbitMQService` interface can be used in `ChatWorker`. Test mocks work because they satisfy the same interface.

**I — Interface Segregation Principle:**
`RedisCacheService` has a focused interface: `get()`, `set()`, `delete()`, `exists()`, `health_check()`. It doesn't expose Redis-specific internals.

**D — Dependency Inversion Principle:**
`ChatWorker` depends on abstractions (`RabbitMQService` interface), not concretions (pika-specific implementation). This is enforced by constructor injection.

---

## 8.8 Health Check Pattern

Every service in your system implements a `health_check()` method:

```python
# In rabbitmq_service.py
def health_check(self) -> dict:
    return {
        "service": "rabbitmq",
        "status": "healthy" if self._connected else "unhealthy",
        "connected": self._connected,
        "queue": RABBITMQ_QUEUE_NAME,
    }
```

This allows your API to expose a `/health` endpoint that aggregates all service health:

```python
@router.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "rabbitmq": rabbitmq_service.health_check(),
            "redis_cache": cache_service.health_check(),
            "redis_pubsub": pubsub_service.health_check(),
        }
    }
```

**Why health checks matter:**
- Docker health checks: `docker-compose` can restart a container if health check fails
- Kubernetes readiness probes: LB only sends traffic to healthy pods
- Monitoring: Datadog/Prometheus can alert when a service becomes unhealthy

---

## 8.9 Error Handling Pattern

Every service follows a consistent pattern: **raise or return, never silently swallow**:

```python
def publish(self, message: dict) -> bool:
    try:
        ...
        return True
    except pika.exceptions.AMQPError as e:
        logger.error(f"RabbitMQ publish failed: {e}")
        return False  # Caller decides what to do with False
    
def get(self, key: str) -> Optional[Any]:
    try:
        ...
        return value
    except RedisError as e:
        logger.error(f"Redis get failed: {e}")
        return None  # Graceful degradation — caller treats as cache miss
```

**The contract:** services return `None` or `False` on error, never raise (except in critical cases). The caller (router, worker) can handle the failure appropriately.

---

## 8.10 Thread Safety

Services accessed by multiple threads/coroutines need thread safety.

**`RabbitMQService`** uses a `threading.Lock()` on `publish()`:
```python
def publish(self, message: dict) -> bool:
    with self._lock:  # Only one thread can publish at a time
        self._channel.basic_publish(...)
```

**`RedisCacheService`** and **`RedisPubSubService`** use Redis connection pools, which are thread-safe by design — the pool manages concurrent connection checkout.

**`RedisPubSubService._publish_client`** is a pooled client (thread-safe for PUBLISH). Per-subscription `PubSub` objects are NOT shared across threads — each WebSocket creates its own.

---

## 8.11 Clean Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        ROUTERS (Interface Layer)                 │
│  auth.py  chat.py  websocket.py  workflows.py  faqs.py           │
│  Receive HTTP/WS requests, call services, return responses       │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ calls
┌──────────────────────────────────▼───────────────────────────────┐
│                       SERVICES (Business Layer)                  │
│  AuthService  ChatService  FaqService  RagService                │
│  Implement business logic, orchestrate calls to infrastructure   │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ calls
┌──────────────────────────────────▼───────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
│  RabbitMQService  RedisCacheService  RedisPubSubService          │
│  MinioStorage     Database (SQLAlchemy)  Milvus                  │
│  Talk to external systems / databases / brokers                  │
└──────────────────────────────────────────────────────────────────┘
```

**Dependency rule:** Routers can call Services. Services can call Infrastructure. But Infrastructure never calls Services or Routers. Data flows DOWN through layers.

---

## 8.12 Interview Questions and Answers

**Q: Why use class-based services instead of functions?**

A: Classes encapsulate state (database connections, connection pools, configuration) with the methods that operate on that state. Functions with global state are fragile in concurrent environments and hard to test. Classes allow multiple instances with different configurations, clear lifecycle management (`__init__`, `connect()`, `close()`), and easy mocking in tests.

**Q: What is dependency injection and why does it matter?**

A: Dependency injection means a class receives its dependencies externally instead of creating them internally. It matters for testability (inject mock objects in tests), flexibility (swap implementations), and separation of concerns (class doesn't need to know how to construct its dependencies).

**Q: What is the singleton pattern and why are services singletons?**

A: Singleton means only one instance of a class exists in the whole application. Services are singletons because creating connection pools on every request would be prohibitively expensive. One connection pool is created at startup and shared across all requests.

**Q: What is separation of concerns?**

A: Organizing code so each module/class has one clearly defined responsibility. If authentication logic changes, only `auth_service.py` changes. If the caching backend changes from Redis to Memcached, only `redis_cache_service.py` changes. Nothing else needs modifying.

---

## 8.13 Common Mistakes

1. **Mixing responsibilities** — putting cache logic inside HTTP router (hard to test, hard to reuse)
2. **Using global mutable variables** — thread-unsafe, hard to test, hidden state
3. **Not using connection pooling** — creating new Redis/DB connection per request is slow
4. **Not implementing health checks** — can't tell if dependencies are healthy without them
5. **Hardcoding dependencies** — `self._rabbitmq = RabbitMQService()` inside `__init__` without injection parameter

---

## 8.14 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/services/rabbitmq_service.py` | Class-based RabbitMQ: connection pool, publish, consume |
| `backend/app/services/redis_cache_service.py` | Class-based Redis cache: get, set, delete, TTL |
| `backend/app/services/redis_pubsub_service.py` | Class-based Redis Pub/Sub: publish, subscribe, listen |
| `backend/app/services/auth_service.py` | Function-based (stateless): hash, verify, create token |
| `backend/app/services/faq_service.py` | Orchestrates DB + cache for FAQ lookups |
| `backend/app/services/chat_service.py` | Orchestrates session management |
| `backend/app/worker/chat_worker.py` | Class-based worker with injected services |
| `backend/app/dependencies/` | FastAPI `Depends()` wiring |
