# Docker Setup Guide

This guide explains how to run all backend services (PostgreSQL, Redis, MinIO, Milvus) using Docker Compose.

## 📋 Prerequisites

- Docker Desktop installed (Windows/Mac) or Docker + Docker Compose (Linux)
- At least 4GB RAM available for Docker
- Ports available: 5432, 6379, 9000, 9001, 19530, 8081

## 🚀 Quick Start

### 1. Configure Environment Variables

Copy the example environment file:

```bash
# From backend directory
cp .env.example .env
```

Edit `.env` and set your configuration (especially `GROQ_API_KEY` and `SECRET_KEY`).

### 2. Start All Services

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f redis
docker-compose logs -f postgres
```

### 3. Verify Services are Running

```bash
# Check service status
docker-compose ps

# Should show all services as "healthy" or "running"
```

### 4. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove all data (⚠️ WARNING: Deletes all data)
docker-compose down -v
```

---

## 📦 Services Included

| Service | Port | Purpose | Web UI |
|---------|------|---------|--------|
| **PostgreSQL** | 5432 | Main database | - |
| **Redis** | 6379 | FAQ cache & Pub/Sub | http://localhost:8081 (dev mode) |
| **MinIO** | 9000, 9001 | PDF storage | http://localhost:9001 |
| **Milvus** | 19530 | Vector database (RAG) | - |
| **Redis Commander** | 8081 | Redis UI (dev only) | http://localhost:8081 |

---

## 🔧 Individual Service Management

### Start Only Specific Services

```bash
# Start only PostgreSQL and Redis (minimal setup)
docker-compose up -d postgres redis

# Start PostgreSQL, Redis, and MinIO
docker-compose up -d postgres redis minio

# Start all services including Milvus (full RAG support)
docker-compose up -d
```

### Restart a Service

```bash
docker-compose restart redis
docker-compose restart postgres
```

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service (last 100 lines)
docker-compose logs --tail=100 redis

# Follow logs in real-time
docker-compose logs -f postgres redis
```

---

## 🔍 Redis Cache Management

### Access Redis CLI

```bash
# Connect to Redis container
docker exec -it chatbot-redis redis-cli

# Inside Redis CLI:
PING                          # Test connection
KEYS faq:*                    # List all FAQ cache keys
GET "faq:chatbot:1:abc123"   # Get specific cached FAQ
FLUSHDB                       # Clear all cache (⚠️ WARNING)
TTL "faq:chatbot:1:abc123"   # Check remaining TTL
INFO stats                    # View cache statistics
```

### Redis Commander Web UI (Development Mode)

Start with dev profile to include Redis Commander:

```bash
docker-compose --profile dev up -d
```

Then visit: http://localhost:8081

Features:
- Browse all keys
- View cache hit/miss statistics
- Delete specific keys
- Monitor real-time operations

---

## 💾 Data Persistence

All data is stored in Docker volumes and persists across container restarts:

- `postgres_data` - Database tables
- `redis_data` - Cached FAQ data
- `minio_data` - Uploaded PDF files
- `milvus_data` - Vector embeddings
- `etcd_data` - Milvus metadata
- `pulsar_data` - Milvus message queue

### View Volumes

```bash
docker volume ls | grep chatbot
```

### Backup Data

```bash
# Backup PostgreSQL
docker exec chatbot-postgres pg_dump -U chatbot chatbot_db > backup.sql

# Backup Redis
docker exec chatbot-redis redis-cli SAVE
docker cp chatbot-redis:/data/dump.rdb redis_backup.rdb

# Backup MinIO (PDFs)
docker exec chatbot-minio mc mirror /data /backup
```

### Restore Data

```bash
# Restore PostgreSQL
docker exec -i chatbot-postgres psql -U chatbot chatbot_db < backup.sql

# Restore Redis
docker cp redis_backup.rdb chatbot-redis:/data/dump.rdb
docker-compose restart redis
```

---

## 🌐 Connecting FastAPI to Docker Services

### Local Development (FastAPI runs on host)

Update your `.env` file:

```env
# PostgreSQL
DATABASE_URL=postgresql://chatbot:chatbot123@localhost:5432/chatbot_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

Then run FastAPI normally:

```bash
cd backend
uvicorn app.main:app --reload
```

### FastAPI in Docker (Future)

If you later containerize FastAPI, change hosts to service names:

```env
DATABASE_URL=postgresql://chatbot:chatbot123@postgres:5432/chatbot_db
REDIS_HOST=redis
MINIO_ENDPOINT=minio:9000
MILVUS_HOST=milvus
```

---

## 🐛 Troubleshooting

### Redis Connection Failed

```bash
# Check if Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
docker exec chatbot-redis redis-cli ping
```

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose ps postgres

# Test connection
docker exec chatbot-postgres psql -U chatbot -d chatbot_db -c "SELECT 1;"
```

### Port Already in Use

```bash
# Find process using port 6379 (Redis)
netstat -ano | findstr :6379

# Kill process (Windows PowerShell)
Stop-Process -Id <PID> -Force

# Or change port in docker-compose.yml:
ports:
  - "6380:6379"  # Use port 6380 on host
```

### Container Won't Start

```bash
# Remove and recreate
docker-compose down
docker-compose up -d

# View detailed logs
docker-compose logs --tail=50 redis
```

### Reset Everything

```bash
# Stop all containers
docker-compose down

# Remove all volumes (⚠️ DELETES ALL DATA)
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose up -d
```

---

## 📊 Monitoring & Health Checks

### Check Service Health

```bash
# View health status
docker-compose ps

# Inspect specific service
docker inspect chatbot-redis --format='{{.State.Health.Status}}'
```

### Monitor Redis Performance

```bash
# Real-time stats
docker exec chatbot-redis redis-cli --stat

# Monitor commands
docker exec chatbot-redis redis-cli MONITOR

# Memory usage
docker exec chatbot-redis redis-cli INFO memory
```

### Database Statistics

```bash
# PostgreSQL stats
docker exec chatbot-postgres psql -U chatbot -d chatbot_db -c "\dt+"
docker exec chatbot-postgres psql -U chatbot -d chatbot_db -c "SELECT pg_size_pretty(pg_database_size('chatbot_db'));"
```

---

## 🔒 Security Best Practices

### Production Recommendations

1. **Change Default Passwords**
   ```env
   POSTGRES_PASSWORD=<strong-random-password>
   REDIS_PASSWORD=<strong-redis-password>
   MINIO_SECRET_KEY=<strong-minio-password>
   ```

2. **Enable Redis Password**
   ```bash
   # In docker-compose.yml, Redis command:
   --requirepass your-strong-password
   
   # In .env:
   REDIS_PASSWORD=your-strong-password
   ```

3. **Use External Networks**
   - Don't expose all ports publicly
   - Use reverse proxy (nginx/traefik)
   - Enable SSL/TLS

4. **Regular Backups**
   - Schedule automated backups
   - Test restore procedures
   - Store backups securely

---

## 📝 Useful Commands Reference

```bash
# Start services
docker-compose up -d                    # All services
docker-compose up -d postgres redis     # Specific services

# Stop services
docker-compose stop                     # Stop all
docker-compose stop redis               # Stop specific

# Restart services
docker-compose restart                  # Restart all
docker-compose restart redis postgres   # Restart specific

# View logs
docker-compose logs -f                  # Follow all logs
docker-compose logs --tail=100 redis    # Last 100 lines

# Execute commands in containers
docker exec -it chatbot-redis redis-cli           # Redis CLI
docker exec -it chatbot-postgres psql -U chatbot  # PostgreSQL CLI

# Clean up
docker-compose down                     # Stop and remove containers
docker-compose down -v                  # Also remove volumes
docker system prune -a                  # Clean all Docker resources
```

---

## 🎯 Next Steps

1. ✅ Start Docker services: `docker-compose up -d`
2. ✅ Verify all services are healthy: `docker-compose ps`
3. ✅ Run database migrations: `python run_migration.py`
4. ✅ Start FastAPI: `uvicorn app.main:app --reload`
5. ✅ Test FAQ caching: Create an FAQ and query it twice (check logs for cache hit)

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [MinIO Documentation](https://min.io/docs/minio/container/index.html)
- [Milvus Documentation](https://milvus.io/docs)
