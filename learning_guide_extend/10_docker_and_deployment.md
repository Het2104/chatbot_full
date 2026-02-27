# 10. Docker and Deployment — Deep Technical Learning

---

## 10.1 Concept Introduction

**Docker** is a platform for packaging applications into **containers** — lightweight, isolated environments that include the application code, runtime, system libraries, and all dependencies. A container runs the same way on any machine that has Docker installed.

**Why containers?**

> "It works on my machine" is the most common software problem.

Without containers:
```
Developer's machine: Python 3.11, Redis 7.0, Ubuntu 22.04
Staging server:      Python 3.9,  Redis 6.2, CentOS 7
Production server:   Python 3.10, Redis 6.0, Debian 11
→ Different behaviors, subtle bugs, deployment failures
```

With containers:
```
Developer's machine: Docker image (Python 3.11, Redis 7.0, exact packages)
Staging server:      Same Docker image
Production server:   Same Docker image
→ Identical environment everywhere
```

---

## 10.2 Docker vs Virtual Machine

```
Virtual Machine:
┌─────────────────────────────────────────────────────────────┐
│  Host OS (Linux/Windows/Mac)                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ Hypervisor   │                                           │
│  │  ┌─────────┐ │   ┌─────────┐        ┌─────────┐        │
│  │  │Guest OS │ │   │Guest OS │        │Guest OS │        │
│  │  │(Linux)  │ │   │(Ubuntu) │        │(CentOS) │        │
│  │  │  App    │ │   │  App    │        │  App    │        │
│  │  └─────────┘ │   └─────────┘        └─────────┘        │
│  └──────────────┘                                           │
│  Each VM: GB of disk, minutes to start, full OS overhead    │
└─────────────────────────────────────────────────────────────┘

Docker Container:
┌─────────────────────────────────────────────────────────────┐
│  Host OS (Linux/Mac)                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Docker Engine                                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Container  │  │ Container  │  │ Container  │     │  │
│  │  │ FastAPI    │  │ Redis      │  │ RabbitMQ   │     │  │
│  │  │ app only   │  │ process    │  │ process    │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  │  Shares host OS kernel — no Guest OS needed          │  │
│  └──────────────────────────────────────────────────────┘  │
│  Each container: MB of disk, seconds to start, minimal OHd │
└─────────────────────────────────────────────────────────────┘
```

---

## 10.3 Dockerfile — Your FastAPI Service

```dockerfile
# Base image: official Python 3.11 slim (minimal)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy only requirements first (layer caching optimization)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port FastAPI listens on
EXPOSE 8000

# Command to run when container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker layer caching explanation:**
```
Layer 1: FROM python:3.11-slim        (cached — rarely changes)
Layer 2: WORKDIR /app                  (cached — never changes)
Layer 3: COPY requirements.txt .       (cached — changes only when deps change)
Layer 4: RUN pip install...            (cached — most expensive, cached if requirements same)
Layer 5: COPY . .                      (rebuilt on every code change)
Layer 6: CMD [...]                     (cached — rarely changes)

When you change one .py file:
  Layers 1-4 served from cache (fast)
  Layer 5 rebuilt (only copy, fast)
  Total rebuild: ~5 seconds instead of ~2 minutes
```

---

## 10.4 Docker Compose — Full Service Orchestration

Your `backend/docker-compose.yml` defines all services and their relationships:

```yaml
version: "3.8"

services:
  
  fastapi:
    build: .
    ports:
      - "8000:8000"         # host:container
    environment:
      - RABBITMQ_HOST=rabbitmq
      - REDIS_HOST=redis
      - DATABASE_URL=postgresql://user:pass@postgres:5432/chatdb
    depends_on:
      - rabbitmq
      - redis
      - postgres
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs    # Persist logs outside container

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"         # AMQP protocol
      - "15672:15672"       # Management UI
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=secret
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq  # Persist queue data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=chatdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
    volumes:
      - milvus_data:/var/lib/milvus
    restart: unless-stopped

volumes:
  rabbitmq_data:
  redis_data:
  postgres_data:
  milvus_data:
```

---

## 10.5 Service Networking in Docker Compose

When services are in the same Docker Compose network, they communicate using **service names as hostnames**:

```
From FastAPI container:
  RABBITMQ_HOST = "rabbitmq"  (not "localhost")
  REDIS_HOST    = "redis"     (not "localhost")
  DATABASE_URL  = "postgresql://user:pass@postgres:5432/chatdb"

Docker's internal DNS resolves:
  "rabbitmq" → 172.18.0.2  (internal Docker IP)
  "redis"    → 172.18.0.3
  "postgres" → 172.18.0.4

From your host machine:
  localhost:8000  → FastAPI
  localhost:5672  → RabbitMQ AMQP
  localhost:15672 → RabbitMQ Management UI
  localhost:6379  → Redis
```

---

## 10.6 Environment Variables — The Right Way

Environment variables separate configuration from code. Your `config.py` reads all configuration from environment:

```python
# config.py
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
SECRET_KEY    = os.getenv("SECRET_KEY", "dev-insecure-key")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
```

**Three environments, three configs:**

```
Development (local):
  .env file:
    SECRET_KEY=dev-key-not-secret
    OPENAI_API_KEY=sk-dev-...
    REDIS_HOST=localhost

Staging (docker-compose):
  docker-compose.yml environment section:
    SECRET_KEY=staging-secret-key-xr7b9...
    REDIS_HOST=redis  (service name, not localhost)

Production (Kubernetes):
  Kubernetes Secrets:
    SECRET_KEY=prod-secret-key-j7k2...  (encrypted at rest)
    OPENAI_API_KEY=sk-prod-...
```

**Never commit secrets to Git.** Add `.env` to `.gitignore`.

---

## 10.7 Volume Mounts

```
Bind mount:
  - ./logs:/app/logs
  Maps host directory → container directory
  Files persist on host even when container is deleted
  Used for: logs, development code hot-reload

Named volume:
  rabbitmq_data:/var/lib/rabbitmq
  Docker manages the storage location
  Data persists across container restarts
  Used for: database files, queue data, cache data
```

**Why volumes for RabbitMQ, Redis, PostgreSQL?**
Without volumes, data is stored inside the container filesystem. If the container is recreated (e.g., `docker-compose down && docker-compose up`), all data is lost. Volumes persist data independently of container lifecycle.

---

## 10.8 Running Locally vs Production

| Aspect | Local Development | Production |
|---|---|---|
| Command | `docker-compose up --build` | `docker-compose -f docker-compose.prod.yml up -d` |
| Config | `.env` file | Environment variables / Kubernetes Secrets |
| Logging | Console / file | Centralized logging (ELK, CloudWatch) |
| Scaling | 1 of each service | Multiple FastAPI instances, multiple workers |
| SSL | None | TLS termination at Nginx/load balancer |
| Workers | Thread inside FastAPI | Separate container |
| Monitoring | None | Prometheus, Grafana, alerts |

---

## 10.9 Restart Policies

```yaml
restart: unless-stopped
```

Options:
- `no` — Never restart (default)
- `always` — Always restart, even on manual stop
- `on-failure` — Restart only if exit code is non-zero
- `unless-stopped` — Restart always except when manually stopped ← **your choice**

**Why `unless-stopped`?**
If Redis crashes, Docker restarts it automatically. FastAPI has no Redis → degrades gracefully. Redis comes back online → FastAPI reconnects automatically (your service has reconnection logic). Zero human intervention needed.

---

## 10.10 Health Checks in Docker

```yaml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s    # Check every 10 seconds
      timeout: 5s      # Fail if no response in 5 seconds
      retries: 3       # Mark unhealthy after 3 failures
      start_period: 10s  # Allow 10s grace at startup
```

FastAPI service with health check:
```yaml
services:
  fastapi:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**`depends_on` with health checks:**
```yaml
services:
  fastapi:
    depends_on:
      redis:
        condition: service_healthy  # Wait for Redis to pass health check
      rabbitmq:
        condition: service_healthy
```

Without this, FastAPI might start before Redis is ready, fail to connect, and crash.

---

## 10.11 Interview Questions and Answers

**Q: What is Docker and why is it used in this system?**

A: Docker packages applications and their dependencies into containers that run identically on any machine. It's used to ensure consistent environments across development, staging, and production, and to easily orchestrate multiple services (FastAPI, RabbitMQ, Redis, PostgreSQL, Milvus) with a single command.

**Q: What is the difference between `depends_on` and `condition: service_healthy`?**

A: `depends_on` alone only waits for the container to start, not for the service inside to be ready. A container can start in milliseconds but PostgreSQL inside needs 5-10 seconds to initialize. `condition: service_healthy` waits until the health check passes, ensuring the service is actually ready to accept connections.

**Q: Why do services use service names (like "redis") instead of "localhost" in Docker Compose?**

A: Each container has its own network namespace. "localhost" inside a container refers to that container itself, not the host or other containers. Docker Compose creates an internal DNS where service names resolve to container IPs, allowing services to find each other by name.

**Q: What happens to RabbitMQ data if you run `docker-compose down`?**

A: If named volumes are configured, data persists. `docker-compose down` stops and removes containers but preserves volumes. `docker-compose down -v` removes volumes too (destructive). Your compose file uses named volumes for all stateful services.

**Q: What is the purpose of Docker layer caching and how do you optimize it?**

A: Docker builds images in layers, and unchanged layers are served from cache on rebuild. The key optimization is copying `requirements.txt` before copying application code. Since dependencies change rarely but code changes often, the expensive `pip install` layer is cached and only rebuilt when `requirements.txt` changes.

---

## 10.12 Common Mistakes

1. **Not using volumes for stateful services** — Data lost on container recreation
2. **Hardcoding IP addresses instead of service names** — Breaks on every Docker start (IPs change)
3. **Using `depends_on` without health checks** — Service starts before dependencies are ready
4. **Committing .env files with secrets to Git** — Security disaster
5. **Not setting resource limits** — One service can consume all CPU/RAM and starve others
6. **Running as root inside containers** — Security vulnerability; use `USER nonroot` in Dockerfile
7. **Not setting `--host 0.0.0.0`** — Service only accessible from inside container, not from outside

---

## 10.13 Key Files Reference

| File | Purpose |
|---|---|
| `backend/docker-compose.yml` | Full multi-service Docker Compose configuration |
| `backend/docker/` | Additional Docker configuration files |
| `backend/requirements.txt` | Python dependencies for pip install in container |
| `backend/app/config.py` | All configuration read from environment variables |
| `backend/DOCKER_SETUP.md` | Setup instructions and Docker commands |
