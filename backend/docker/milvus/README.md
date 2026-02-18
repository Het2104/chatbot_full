# Milvus Docker Setup

This folder contains Docker Compose configuration for Milvus vector database.

## Services

- **Milvus** (port 19530): Vector database for storing and searching embeddings
- **Attu** (port 3001): Web UI for managing Milvus collections and viewing data
- **MinIO** (ports 9000, 9001): Object storage backend for Milvus
- **etcd** (port 2379): Metadata coordination service
- **Pulsar** (port 6650): Message queue for Milvus operations

## Quick Start

### Start Services
```powershell
.\start.bat
```

Wait 60-90 seconds for all services to initialize.

### Check Status
```powershell
.\status.bat
```

### Stop Services
```powershell
.\stop.bat
```

## Access Points

- **Milvus API**: `localhost:19530` (use pymilvus client)
- **Milvus Health Check**: http://localhost:9091/healthz
- **Attu Web UI**: http://localhost:3001
  - Visual interface to browse collections, view vectors, and inspect chunks
  - No login required
- **MinIO Console**: http://localhost:9001
  - Username: `minioadmin`
  - Password: `minioadmin`

## Data Persistence

All data is stored in local volumes:
```
volumes/
├── etcd/        - Metadata
├── minio/       - Vector data files
├── pulsar/      - Message queue logs
└── milvus/      - Milvus runtime data
```

## Troubleshooting

### Containers won't start
1. Check Docker Desktop is running
2. Check ports are not in use (19530, 3001, 9000, 9001, 2379, 6650)
3. Check system has enough RAM (3GB minimum)

### Health check fails
Wait 90 seconds after starting. Milvus needs time to initialize.

### Reset everything
```powershell
.\stop.bat
docker-compose down -v  # Remove volumes
.\start.bat
```
