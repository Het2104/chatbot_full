# AI Chatbot Platform

A full-stack multi-chatbot platform where admins build chatbots with visual conversation workflows, FAQ trees, and a Retrieval-Augmented Generation (RAG) knowledge base powered by real web pages and PDFs. End-users chat with those bots in real time via a Next.js frontend.

---

## Features

| # | Feature | Description |
|---|---|---|
| 1 | **Multi-chatbot management** | Create, list, and delete independent chatbot instances |
| 2 | **Visual workflow builder** | Design branching conversation flows as directed graphs using a drag-and-drop canvas |
| 3 | **Hierarchical FAQ manager** | Nested parent/child Q&A trees with Redis caching (1-hour TTL) |
| 4 | **PDF knowledge base** | Upload PDFs (up to 10 MB); OCR fallback for scanned documents |
| 5 | **URL ingestion** | Scrape any public webpage into the same vector store as PDFs |
| 6 | **RAG-powered answers** | Semantic search over all indexed content via Milvus + Groq LLM |
| 7 | **Waterfall answer resolution** | Per message: workflow → FAQ cache → RAG → default fallback |
| 8 | **Async chat queue** | Heavy RAG/LLM work offloaded via RabbitMQ to a background worker |
| 9 | **Real-time streaming** | WebSocket pushes worker results live to the browser via Redis Pub/Sub |
| 10 | **JWT authentication** | Register/login, Bearer token, role-based access (`user` / `admin`) |
| 11 | **MinIO PDF storage** | Raw PDFs stored in an S3-compatible bucket |
| 12 | **Source management** | List and delete both PDFs and indexed URLs from the Knowledge Base UI |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| **Visual Editor** | @xyflow/react |
| **Backend API** | FastAPI, Python, Uvicorn |
| **ORM / Validation** | SQLAlchemy 2.0, Pydantic 2.9 |
| **Relational DB** | PostgreSQL 15 |
| **Vector DB** | Milvus (pymilvus 2.4.9) |
| **Cache / Pub-Sub** | Redis 7 |
| **Message Queue** | RabbitMQ 3 |
| **Object Storage** | MinIO (S3-compatible) |
| **Embeddings** | `BAAI/bge-large-en-v1.5` via sentence-transformers (1024-dim) |
| **LLM** | Groq API — `llama3-8b-8192` |
| **PDF / OCR** | PyPDF2, pytesseract, pdf2image, Pillow |
| **Web Scraping** | BeautifulSoup4, requests |
| **Auth** | JWT — python-jose, passlib/bcrypt (HS256) |

---

## Project Structure

```
chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                      # App factory, router registration, startup
│   │   ├── config.py                    # All env vars & constants
│   │   ├── routers/
│   │   │   ├── auth.py                  # /auth/*
│   │   │   ├── chatbots.py              # /chatbots/*
│   │   │   ├── workflows.py             # /chatbots/{id}/workflows/*
│   │   │   ├── nodes.py                 # /workflows/{id}/nodes/*
│   │   │   ├── edges.py                 # /workflows/{id}/edges/*
│   │   │   ├── chat.py                  # /chat/*
│   │   │   ├── faqs.py                  # /chatbots/{id}/faqs/*
│   │   │   ├── upload.py                # /api/upload/pdf*
│   │   │   ├── url_router.py            # /api/upload/url*
│   │   │   └── websocket.py             # /ws/chat/*
│   │   ├── models/                      # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── chatbot.py
│   │   │   ├── workflow.py
│   │   │   ├── node.py
│   │   │   ├── edge.py
│   │   │   ├── faq.py
│   │   │   ├── chat_session.py
│   │   │   ├── chat_message.py
│   │   │   └── indexed_url.py           # Tracks ingested web pages
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── chat_service.py          # Waterfall resolution logic
│   │   │   ├── faq_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── pdf_processing_service.py
│   │   │   ├── url_processing_service.py  # URL → chunk → embed → Milvus
│   │   │   ├── url_scraping_service.py    # HTTP fetch + HTML → text (SSRF-safe)
│   │   │   ├── minio_storage.py
│   │   │   ├── redis_cache_service.py
│   │   │   ├── redis_pubsub_service.py
│   │   │   └── rabbitmq_service.py
│   │   ├── rag/
│   │   │   ├── offline/                 # chunker, embedder, text_cleaner, text_extractor
│   │   │   ├── online/                  # retriever, generator, query_embedder,
│   │   │   │                            #   context_builder, prompt_builder, response_formatter
│   │   │   └── storage/                 # milvus_store.py
│   │   ├── worker/                      # chat_worker.py — RabbitMQ consumer
│   │   ├── schemas/                     # Pydantic request/response models
│   │   └── dependencies/                # auth.py, cache.py (FastAPI DI)
│   ├── data/
│   │   ├── raw_pdfs/
│   │   └── processed/
│   ├── logs/
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                     # Landing page
│   │   ├── layout.tsx                   # Root layout
│   │   ├── login/
│   │   ├── register/
│   │   ├── dashboard/[id]/              # Main chatbot dashboard
│   │   ├── chat/[id]/                   # Chat view
│   │   ├── workflows/[id]/              # Workflow visual editor
│   │   └── unauthorized/
│   ├── components/
│   │   ├── Dashboard/
│   │   │   ├── Layout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── Workflows.tsx
│   │   │   ├── FAQManager.tsx
│   │   │   └── KnowledgeBase.tsx        # PDF upload + URL ingest + tabbed list
│   │   ├── PdfUploadButton.tsx
│   │   ├── UrlIngestButton.tsx
│   │   ├── NavBar.tsx
│   │   └── withAuth.tsx                 # Auth HOC
│   ├── contexts/                        # AuthContext
│   └── services/
│       └── api.ts                       # Centralised fetch wrapper
└── data/
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop
- Milvus (standalone) running on port `19530`
- MinIO running on port `9000`

> Milvus and MinIO are **not** included in `docker-compose.yml`. Run them separately — see [backend/DOCKER_SETUP.md](backend/DOCKER_SETUP.md).

---

### 1. Environment Setup

Copy the example and fill in your values:

```bash
cd backend
cp .env.example .env   # or create .env manually
```

**Required variables:**

```dotenv
# Database
DATABASE_URL=postgresql://chatbot:chatbot123@localhost:5432/chatbot_db
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=chatbot123
POSTGRES_DB=chatbot_db
POSTGRES_PORT=5432

# LLM — get a free key at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# JWT — use a long random string
SECRET_KEY=your-very-long-secret-key-at-least-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Milvus (vector database)
MILVUS_HOST=localhost
MILVUS_PORT=19530

# MinIO (object storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=pdfs
MINIO_SECURE=false

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
CACHE_ENABLED=true
FAQ_CACHE_TTL=3600

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest
RABBITMQ_QUEUE_NAME=rag_processing_queue

# Optional tuning
LLM_MODEL=llama3-8b-8192
LOG_LEVEL=INFO
WEBSOCKET_RESPONSE_TIMEOUT=120
```

---

### 2. Start Infrastructure (Docker)

```bash
cd backend

# Starts: PostgreSQL, Redis, RabbitMQ, background worker
docker-compose up -d

# Dev mode — also starts Redis Commander at http://localhost:8081
docker-compose --profile dev up -d
```

---

### 3. Run the Backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create database tables (first time only)
python run_migration.py

# Create indexed_urls table (URL ingestion feature)
python run_url_migration.py

# Start the API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API is now available at **http://127.0.0.1:8000**
Interactive docs at **http://127.0.0.1:8000/docs**

---

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:3000**

---

### 5. Create an Admin User

```bash
cd backend
python create_admin.py
```

---

## API Reference

**Base URL:** `http://127.0.0.1:8000`

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and receive JWT token |
| `GET` | `/auth/me` | Get current authenticated user |

### Chatbots

| Method | Path | Description |
|---|---|---|
| `POST` | `/chatbots` | Create a chatbot |
| `GET` | `/chatbots` | List all chatbots |
| `GET` | `/chatbots/{id}` | Get chatbot by ID |
| `DELETE` | `/chatbots/{id}` | Delete chatbot (cascades all data) |

### Workflows

| Method | Path | Description |
|---|---|---|
| `POST` | `/chatbots/{id}/workflows` | Create a workflow |
| `GET` | `/chatbots/{id}/workflows` | List workflows |
| `PUT` | `/workflows/{id}/activate` | Activate a workflow |
| `DELETE` | `/workflows/{id}` | Delete workflow |

### Nodes & Edges

| Method | Path | Description |
|---|---|---|
| `POST` | `/workflows/{id}/nodes` | Create a node (`trigger` or `response`) |
| `GET` | `/workflows/{id}/nodes` | List nodes |
| `PATCH` | `/nodes/{id}` | Update node text / position |
| `DELETE` | `/nodes/{id}` | Delete node |
| `POST` | `/workflows/{id}/edges` | Connect two nodes |
| `GET` | `/workflows/{id}/edges` | List edges |
| `DELETE` | `/edges/{id}` | Remove an edge |

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/start` | Start a chat session; returns trigger nodes |
| `POST` | `/chat/message` | Send message (synchronous response) |
| `POST` | `/chat/message/queue` | Enqueue message (async, returns `job_id`) |
| `WS` | `/ws/chat/{session_id}/{job_id}` | Stream async response via WebSocket |

### FAQs

| Method | Path | Description |
|---|---|---|
| `POST` | `/chatbots/{id}/faqs` | Create FAQ (parent or nested child) |
| `GET` | `/chatbots/{id}/faqs` | List FAQs |
| `GET` | `/faqs/{id}` | Get FAQ by ID |
| `PATCH` | `/faqs/{id}` | Update FAQ |
| `DELETE` | `/faqs/{id}` | Delete FAQ |

### Knowledge Base

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload/pdf` | Upload and process a PDF for RAG |
| `GET` | `/api/upload/pdfs` | List uploaded PDFs |
| `DELETE` | `/api/upload/pdf/{filename}` | Delete a PDF |
| `POST` | `/api/upload/url` | Scrape and index a public web page |
| `GET` | `/api/upload/urls` | List all indexed URLs |
| `DELETE` | `/api/upload/url/{id}` | Remove URL and its vectors from Milvus |

---

## How It Works

### RAG Pipeline (PDF or URL)

```
PDF upload           URL ingest
     │                   │
     ▼                   ▼
Extract text        Scrape page (SSRF-safe)
     │                   │
     └────────┬──────────┘
              ▼
         Clean text
              ▼
     Chunk (~2000 chars, 3-sentence overlap)
              ▼
     Embed  (BAAI/bge-large-en-v1.5, 1024-dim)
              ▼
     Store in Milvus  (source_file = filename or URL)
```

### Chat Message Flow (Async Path)

```
Browser
  │  POST /chat/message/queue
  ▼
FastAPI ──publish──► RabbitMQ (rag_processing_queue)
                          │
                          ▼
                    ChatWorker (Docker container)
                     Waterfall:
                       1. Workflow node match
                       2. FAQ (Redis cache hit)
                       3. RAG → Milvus search → Groq LLM
                       4. Default fallback message
                          │
                          └──publish──► Redis Pub/Sub
                                              │
FastAPI WebSocket ◄──subscribe────────────────┘
  │  /ws/chat/{session_id}/{job_id}
  ▼
Browser (live streamed response)
```

### Answer Priority

1. **Workflow node** — exact keyword match in the active workflow graph
2. **FAQ cache** — Redis-cached answer (1-hour TTL)
3. **RAG** — semantic search (Milvus, min score 0.3) → Groq LLM generates answer from retrieved chunks
4. **Default** — generic fallback message

---

## Docker Services

| Container | Image | Port | Purpose |
|---|---|---|---|
| `chatbot-postgres` | `postgres:15-alpine` | `5432` | Primary relational database |
| `chatbot-redis` | `redis:7-alpine` | `6379` | FAQ cache + Pub/Sub broker |
| `chatbot-rabbitmq` | `rabbitmq:3-management-alpine` | `5672` / `15672` | Message queue + management UI |
| `chatbot-worker` | local build | — | Background RAG/LLM processor |
| `chatbot-redis-commander` | redis-commander | `8081` | Redis web UI *(dev profile)* |

> **Separate services required:** Milvus on `:19530` and MinIO on `:9000` — see [backend/DOCKER_SETUP.md](backend/DOCKER_SETUP.md).

---

## Useful URLs (Local Dev)

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://127.0.0.1:8000 |
| API Docs (Swagger) | http://127.0.0.1:8000/docs |
| RabbitMQ Management | http://localhost:15672 (guest / guest) |
| Redis Commander | http://localhost:8081 *(dev profile)* |
| MinIO Console | http://localhost:9001 |
