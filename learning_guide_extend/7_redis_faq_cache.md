# 7. Redis FAQ Cache — Deep Technical Learning

---

## 7.1 Concept Introduction

**Caching** is the practice of storing the result of an expensive operation so that future requests for the same result can be served quickly from memory instead of repeating the expensive operation.

In your chatbot system, answering most user questions requires:
1. Embedding the question (CPU + network call)
2. Searching Milvus for similar documents (network call)
3. Calling OpenAI to generate a response (network call, costs money, takes 2-15s)

If 100 users ask "What is the return policy?", you would normally make 100 OpenAI API calls. With caching, you make **1 call** and serve the other 99 from Redis in microseconds.

---

## 7.2 Why Redis for Caching

Redis is an **in-memory data store** — all data lives in RAM. RAM access is ~100 nanoseconds. Network database access is ~1-10 milliseconds. Redis cache hit is **10,000x faster** than hitting the database or calling an API.

**Why not use Python's `functools.lru_cache`?**
- Only works within one process
- Not shared across multiple API server instances
- Cleared on process restart

**Why Redis over Memcached?**
- Redis supports complex data structures (lists, sets, sorted sets, hashes)
- Redis has built-in persistence options
- Redis supports TTL per key
- Redis also handles Pub/Sub in your system (dual-purpose)

---

## 7.3 FAQ Cache Architecture

Your `RedisCacheService` (`services/redis_cache_service.py`) is a generic caching layer. The `FaqService` (`services/faq_service.py`) uses it for FAQ-specific caching:

```
User asks: "What is the return policy?"
                │
                ▼
FaqService.get_faq_cached(question)
                │
                ▼
Compute cache key:
  import hashlib
  key = f"faq:{hashlib.md5(question.lower().strip().encode()).hexdigest()}"
  → "faq:a1b2c3d4e5f6..."
                │
                ▼
RedisCacheService.get(key)
                │
         ┌──────┴──────────┐
         │                 │
    CACHE HIT         CACHE MISS
         │                 │
    return cached     Query PostgreSQL FAQs
    answer            Compare question similarity
         │            Find best match
         │            If match found:
         │              answer = matched_faq.answer
         │              RedisCacheService.set(key, answer, ttl=3600)
         │                 │
         └─────────────────┘
                │
                ▼
         Return answer
         (or None if no match)
```

---

## 7.4 Cache Key Design

**Cache key:** `faq:{md5_hash_of_normalized_question}`

**Normalization:** `question.lower().strip()`

Why normalize?
- "What is the return policy?" 
- "what is the return policy?" 
- "  What is the return policy?  "

All three are the same question but different strings. Without normalization, you'd miss cache hits and waste storage.

**Why MD5 hash?**
- Variable-length question text → fixed-length 32-char key
- Avoids special characters in Redis keys
- Not used for security — just for key generation (MD5 is fine here)

**Example:**
```python
question = "What is the return policy?"
normalized = question.lower().strip()  → "what is the return policy?"
key_bytes  = normalized.encode()       → b"what is the return policy?"
hash       = hashlib.md5(key_bytes).hexdigest() → "a1b2c3d4e5f67890..."
redis_key  = f"faq:{hash}"            → "faq:a1b2c3d4e5f67890..."
```

---

## 7.5 TTL — Time To Live

Every cache entry in your system has a TTL (Time To Live) in seconds. After the TTL expires, Redis automatically deletes the key.

**Why TTL matters:**

Without TTL:
- Cache entries live forever
- FAQ answers change (admin updates policy), but old answers stay in cache
- Users get outdated information

With TTL = 3600 (1 hour):
- Stale answers expire after 1 hour
- Fresh answers loaded from database
- Balance between performance and freshness

**How Redis handles TTL:**
```redis
SET faq:a1b2c3 "Return within 30 days" EX 3600
               │                          │
               └── key-value pair         └── expires in 3600 seconds
```

Redis uses two mechanisms:
1. **Passive expiry:** Check TTL when key is accessed. If expired, delete and return nil.
2. **Active expiry:** Background task periodically sweeps for expired keys and deletes them.

---

## 7.6 Cache-First Strategy

Your system implements a **cache-first (read-through cache)** strategy:

```
Request comes in
      │
      ▼
Check cache → HIT? → Return cached value (fast path)
      │
     MISS
      │
      ▼
Compute expensive answer
      │
      ▼
Store in cache with TTL
      │
      ▼
Return answer
```

**Contrast with write-through cache:**
- Write-through: When FAQ is updated in DB, also update cache immediately
- Read-through (your system): Cache is updated lazily on next cache miss

Your system favors simplicity with TTL-based invalidation.

---

## 7.7 Cache Invalidation Strategy

Cache invalidation is one of the hardest problems in computer science (along with naming things and off-by-one errors). Your strategy is **TTL-based expiry** — the simplest valid approach.

**Three main invalidation strategies:**

| Strategy | How | Pros | Cons |
|---|---|---|---|
| TTL expiry | Cache auto-deletes after N seconds | Simple, no DB triggers needed | Stale window (up to TTL seconds) |
| Active deletion | When FAQ updated, delete cache key | No stale window | Admin must trigger cache delete explicitly |
| Write-through | When FAQ saved, write to cache too | Always fresh, no stale | More complex DB write logic |

**Your system:** TTL expiry (3600s default). When an admin updates a FAQ answer, the old cached response expires within 1 hour. For most business use cases, this is acceptable.

**Production improvement:** Add active cache invalidation in the FAQ update API endpoint:
```python
# When admin updates FAQ answer
def update_faq(faq_id, new_answer):
    db.update(faq_id, new_answer)
    cache_key = f"faq:{compute_hash(faq.question)}"
    cache_service.delete(cache_key)
```

---

## 7.8 Serialization Strategy

Redis stores strings. Your cache must serialize Python objects to strings and deserialize them back.

Your `RedisCacheService` uses **JSON serialization**:

```python
# Storing (in redis_cache_service.py)
self._client.setex(
    name=key,
    time=ttl,
    value=json.dumps(value)  # Python dict → JSON string
)

# Retrieving
raw = self._client.get(key)
return json.loads(raw)  # JSON string → Python dict
```

**Why JSON over pickle?**
- `pickle` is Python-specific — cached values can't be read by other languages
- JSON is human-readable — debuggable with `redis-cli`
- `pickle` can execute arbitrary code if tampered with (security risk)

---

## 7.9 Cost Optimization Analysis

**Without cache:**
- 100 users ask "What is the return policy?" per day
- 100 × $0.002 per 1K tokens (OpenAI pricing) × ~500 tokens per response
- = $0.10 per day = $36.50 per year for ONE frequently asked question

**With cache:**
- First request: 1 OpenAI call
- Next 99: served from Redis (< 1ms, $0 cost)
- = $0.001 for that question per day = $0.365 per year

**For a chatbot with 50 common questions and 1,000 daily users:**
- Without cache: ~$18,250/year in OpenAI costs
- With 90% cache hit rate: ~$1,825/year
- **Savings: ~$16,425/year**

This is why the FAQ cache is a **business-critical** feature, not just a performance optimization.

---

## 7.10 Redis Connection Pool Details

```python
# From redis_cache_service.py
pool_config = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_DB,
    "socket_timeout": REDIS_SOCKET_TIMEOUT,
    "socket_connect_timeout": REDIS_SOCKET_CONNECT_TIMEOUT,
    "decode_responses": True,  # Auto-decode bytes → str
    "max_connections": 50,
}
pool = redis.ConnectionPool(**pool_config)
self._client = redis.Redis(connection_pool=pool)
```

**What connection pooling does:**
- Creates a pool of persistent connections to Redis
- When your code calls `client.get(key)`, it checks out a connection from the pool
- After the call returns, the connection goes back to the pool
- If all 50 connections are in use, new requests wait briefly
- Much faster than creating a new TCP connection for every cache operation (TCP handshake = ~1ms)

---

## 7.11 Graceful Degradation

Your `RedisCacheService` handles Redis unavailability gracefully:

```python
def get(self, key: str):
    if not self._enabled or self._client is None:
        return None  # Cache miss — caller falls through to DB
    try:
        raw = self._client.get(key)
        return json.loads(raw) if raw else None
    except (RedisError, ConnectionError):
        return None  # Cache miss on error — system still works
```

If Redis is down:
- Every cache lookup returns `None` (miss)
- System falls back to live FAQ database queries and OpenAI calls
- Higher cost and latency, but system continues functioning
- No `try/except` crashes anywhere

---

## 7.12 Interview Questions and Answers

**Q: Why is caching important in an AI chatbot?**

A: AI API calls are expensive (monetary cost) and slow (latency). For frequently asked questions that have the same answer, recomputing the answer every time is wasteful. A cache stores the answer after the first computation and returns it instantly on subsequent requests, reducing costs by 80-90% and latency from seconds to milliseconds.

**Q: What is a cache miss and what happens in your system?**

A: A cache miss is when the requested key is not found in the cache (either never cached or TTL expired). In your system on a cache miss: the FAQ is looked up in PostgreSQL, if a matching FAQ exists the answer is returned and stored in Redis with a TTL, if no match the request proceeds to the RabbitMQ queue for AI processing.

**Q: What is TTL and why is it important?**

A: TTL (Time To Live) is the number of seconds before a cached entry is automatically deleted. Without TTL, stale data stays in cache forever. After a FAQ answer is updated in the database, the old cached response would continue being served indefinitely. TTL ensures the cache is refreshed periodically, balancing performance with data freshness.

**Q: What is cache invalidation and what strategy does this system use?**

A: Cache invalidation is the process of removing or updating cached data when the underlying source data changes. This system uses TTL-based expiry: entries automatically expire after a configured time period. Simple and zero-code, but with a stale window up to TTL duration.

**Q: What is the difference between `decode_responses=True` and false in Redis?**

A: With `decode_responses=True`, the Redis client automatically decodes bytes returned from Redis into Python strings using UTF-8. Without it, all values are raw bytes (e.g., `b"hello"` instead of `"hello"`). Setting it to `True` simplifies code since you rarely need raw bytes.

---

## 7.13 Common Mistakes

1. **Not setting TTL** — Cache grows unboundedly, stale data served forever
2. **Not normalizing cache key** — Same question in different case formats creates duplicate cache entries
3. **Caching errors** — If the FAQ lookup fails, never cache `None` or the error
4. **Not handling Redis failure** — If Redis goes down, whole FAQ system should still work (fallback to DB)
5. **Storing uncacheable objects** — Objects with database sessions, file handles, etc. cannot be JSON-serialized
6. **Too-long TTL** — Changes to FAQ answers take too long to reflect
7. **Too-short TTL** — Cache ineffective, high miss rate, high OpenAI costs

---

## 7.14 Production Considerations

- Use Redis Sentinel or Redis Cluster for HA cache
- Monitor cache hit rate (aim for >80% for FAQ scenarios)
- Set Redis `maxmemory` with `allkeys-lru` eviction policy: oldest unused keys evicted when memory full
- Implement cache warming: pre-populate cache with most common questions on system startup
- Use separate Redis databases (or instances) for cache vs Pub/Sub to avoid interference
- Alert on unexpectedly low cache hit rate (suggests new FAQ patterns not in cache)

---

## 7.15 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/services/redis_cache_service.py` | Generic Redis cache: get, set, delete, exists, health check |
| `backend/app/services/faq_service.py` | FAQ-specific cache logic with key hashing and TTL |
| `backend/app/routers/chat.py` | FAQ cache check before publishing to queue |
| `backend/app/config.py` | `REDIS_HOST`, `CACHE_ENABLED`, `REDIS_DB` |
