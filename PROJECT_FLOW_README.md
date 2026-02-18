# Chatbot Project - Complete Flow & Architecture

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Database Schema](#database-schema)
5. [Complete Conversation Flow](#complete-conversation-flow)
6. [RAG Pipeline Detailed Flow](#rag-pipeline-detailed-flow)
7. [API Endpoints](#api-endpoints)
8. [Project Setup & Running](#project-setup--running)
9. [Key Features](#key-features)
10. [Code Structure](#code-structure)

---

## 🎯 Project Overview

**Multi-Modal AI Chatbot with RAG (Retrieval-Augmented Generation)**

This is a full-stack intelligent chatbot system that combines three response strategies:
1. **Workflow-based responses** - Pre-configured conversation flows with trigger-response patterns
2. **FAQ system** - Question-answer pairs with nested hierarchy
3. **RAG (Document-based AI)** - Answers from uploaded PDF documents using semantic search + LLM

**Key Innovation**: Automatic fallback system - if the chatbot can't find an answer in workflows, it checks FAQs, then searches PDFs, ensuring comprehensive coverage.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                           │
│        Next.js 16 + TypeScript + React 19                   │
│                                                              │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐      │
│  │  Workflow   │ │ Chat         │ │  PDF Upload    │      │
│  │  Builder    │ │ Interface    │ │  Component     │      │
│  │ (ReactFlow) │ │              │ │                │      │
│  └─────────────┘ └──────────────┘ └────────────────┘      │
│                                                              │
│         API Calls (REST - http://localhost:8000)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   BACKEND LAYER                             │
│                FastAPI (Python)                             │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │         CHAT SERVICE (Main Controller)           │      │
│  │                                                   │      │
│  │    User Message → Waterfall Processing:          │      │
│  │    1. Check Workflow Match (exact text)          │      │
│  │    2. Check FAQ Match (exact question)           │      │
│  │    3. RAG Query (semantic search in PDFs)        │      │
│  │    4. Default Response "I didn't understand"     │      │
│  └──────────────────────────────────────────────────┘      │
│           │              │              │                    │
│           ↓              ↓              ↓                    │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │ Workflow   │  │ FAQ         │  │ RAG Service  │        │
│  │ Processor  │  │ Processor   │  │ (Orchestrator)│       │
│  └────────────┘  └─────────────┘  └──────────────┘        │
│                                           │                  │
└───────────┬──────────────┬───────────────┴──────┬──────────┘
            │              │                      │
            ↓              ↓                      ↓
    ┌──────────────┐  ┌────────────┐    ┌──────────────────┐
    │ PostgreSQL   │  │  Milvus    │    │   Groq Cloud     │
    │   Database   │  │ Vector DB  │    │   LLM API        │
    │              │  │            │    │                  │
    │ • chatbots   │  │ Collection:│    │ llama-3.1-8b     │
    │ • workflows  │  │ rag_chunks │    │ Temperature: 0.0 │
    │ • nodes      │  │            │    │                  │
    │ • edges      │  │ 384-dim    │    │                  │
    │ • faqs       │  │ vectors    │    │                  │
    │ • sessions   │  └────────────┘    └──────────────────┘
    │ • messages   │
    └──────────────┘
```

---

## 💻 Technology Stack

### **Frontend**
- **Framework**: Next.js 16.1.6 (React 19.2.3)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4.1.18
- **Workflow Visualization**: @xyflow/react 12.10.0 (ReactFlow)
- **Icons**: lucide-react
- **Dev Server**: Port 3000

### **Backend**
- **Framework**: FastAPI (Python)
- **Database ORM**: SQLAlchemy
- **API Style**: RESTful JSON
- **CORS**: Configured for localhost:3000

### **Databases**
1. **PostgreSQL** - Structured data (chatbots, workflows, FAQs, conversations)
2. **Milvus Vector DB** - Semantic search for RAG
   - **etcd**: Metadata management
   - **MinIO**: Object storage for vectors
   - **Pulsar**: Internal message queue
   - **Attu**: Web UI for Milvus (optional)

### **AI/ML Stack**
- **Embeddings**: sentence-transformers with `all-MiniLM-L12-v2` (384 dimensions)
- **LLM**: Groq API with `llama-3.1-8b-instant`
- **PDF Processing**: PyPDF2 for text extraction
- **OCR**: Tesseract + Poppler for scanned PDFs

### **What's NOT Used** (from requirements)
- ❌ Hasura (using REST APIs instead of GraphQL)
- ❌ Redis (no caching layer implemented)
- ❌ Celery/RabbitMQ (no application-level task queues)

---

## 🗄️ Database Schema

### **PostgreSQL Tables**

#### 1. **chatbots**
```sql
id              SERIAL PRIMARY KEY
name            VARCHAR NOT NULL
description     TEXT
created_at      TIMESTAMP DEFAULT NOW()
```
- Root entity for the entire chatbot
- One chatbot can have multiple workflows, FAQs, and chat sessions

#### 2. **workflows**
```sql
id              SERIAL PRIMARY KEY
chatbot_id      INTEGER REFERENCES chatbots(id) ON DELETE CASCADE
name            VARCHAR NOT NULL
is_active       BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP DEFAULT NOW()
```
- Visual conversation flows designed in the workflow builder
- Only ONE workflow can be active per chatbot at a time

#### 3. **nodes**
```sql
id              SERIAL PRIMARY KEY
workflow_id     INTEGER REFERENCES workflows(id) ON DELETE CASCADE
node_type       VARCHAR NOT NULL  -- 'trigger' or 'response'
text            TEXT NOT NULL
created_at      TIMESTAMP DEFAULT NOW()
```
- **Trigger nodes**: User messages that start a conversation path
- **Response nodes**: Bot replies to triggers

#### 4. **edges**
```sql
id              SERIAL PRIMARY KEY
workflow_id     INTEGER REFERENCES workflows(id) ON DELETE CASCADE
from_node_id    INTEGER REFERENCES nodes(id) ON DELETE CASCADE
to_node_id      INTEGER REFERENCES nodes(id) ON DELETE CASCADE
created_at      TIMESTAMP DEFAULT NOW()

CONSTRAINT unique_edge UNIQUE (workflow_id, from_node_id, to_node_id)
```
- Connections between nodes defining conversation flow
- Unique constraint prevents duplicate edges

#### 5. **faqs**
```sql
id              SERIAL PRIMARY KEY
chatbot_id      INTEGER REFERENCES chatbots(id) ON DELETE CASCADE
question        TEXT NOT NULL
answer          TEXT NOT NULL
is_active       BOOLEAN DEFAULT TRUE
display_order   INTEGER
parent_id       INTEGER REFERENCES faqs(id) ON DELETE CASCADE
created_at      TIMESTAMP DEFAULT NOW()

CONSTRAINT unique_faq UNIQUE (chatbot_id, question)
```
- Simple question-answer pairs
- **parent_id**: Enables nested FAQs (sub-questions)
- Unique constraint prevents duplicate questions per chatbot

#### 6. **chat_sessions**
```sql
id              SERIAL PRIMARY KEY
chatbot_id      INTEGER REFERENCES chatbots(id) ON DELETE CASCADE
workflow_id     INTEGER REFERENCES workflows(id) ON DELETE SET NULL
started_at      TIMESTAMP DEFAULT NOW()
```
- Represents one conversation instance with a user
- workflow_id is nullable (allows flexible conversations)

#### 7. **chat_messages**
```sql
id              SERIAL PRIMARY KEY
session_id      INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE
sender          VARCHAR NOT NULL  -- 'user' or 'bot'
message_text    TEXT NOT NULL
timestamp       TIMESTAMP DEFAULT NOW()
```
- Individual messages within a chat session
- Preserves complete conversation history

### **Milvus Collection: rag_chunks**

```python
chunk_id        INT64 (Primary Key, Auto-increment)
embedding       FLOAT_VECTOR[384]  # 384-dimensional vector
text            VARCHAR[65535]     # Chunk text content
source_file     VARCHAR[512]       # PDF filename
chunk_index     INT64              # Position in document

Index: IVF_FLAT with Inner Product metric
```
- Stores PDF chunks as searchable vectors
- Inner Product = Cosine similarity (for normalized vectors)

---

## 🔄 Complete Conversation Flow

### **Step-by-Step: What Happens When User Sends a Message**

```
User opens chat interface → Frontend calls POST /chat/start
                          ↓
Backend creates chat_session in PostgreSQL
Returns list of trigger nodes from active workflow
                          ↓
User types message: "Hello"
                          ↓
Frontend calls POST /chat/message with message text
                          ↓
Backend: chat_service.process_message() begins
                          ↓
┌─────────────────────────────────────────────────────────┐
│          WATERFALL DECISION LOGIC                       │
│                                                          │
│  Priority 1: Check Workflow Match                       │
│  ↓                                                       │
│  • Get active workflow for this chatbot                 │
│  • Get all trigger nodes from workflow                  │
│  • Check if user message EXACTLY matches trigger text   │
│  • If match found:                                      │
│    - Find connected response node via edges             │
│    - Return response node text                          │
│    - STOP (don't check FAQ or RAG)                      │
│  ↓                                                       │
│  Priority 2: Check FAQ Match (if no workflow match)     │
│  ↓                                                       │
│  • Get all active FAQs for this chatbot                 │
│  • Check if user message EXACTLY matches FAQ question   │
│  • If match found:                                      │
│    - Return FAQ answer                                  │
│    - Return child FAQs as options (if parent_id)        │
│    - STOP (don't check RAG)                             │
│  ↓                                                       │
│  Priority 3: RAG Query (if no FAQ match)                │
│  ↓                                                       │
│  • Call rag_service.get_rag_response(user_message)      │
│  • RAG searches PDF documents (see detailed RAG flow)   │
│  • If relevant documents found:                         │
│    - Return AI-generated answer from PDFs               │
│    - STOP                                               │
│  • If no relevant documents:                            │
│    - Return "I don't know based on available info"      │
│    - Continue to fallback                               │
│  ↓                                                       │
│  Priority 4: Default Response (if nothing matched)      │
│  ↓                                                       │
│  • Return "I didn't understand"                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
Save both user message and bot response to chat_messages table
                          ↓
Return response to frontend
                          ↓
User sees response in chat interface
```

### **Code Implementation** (backend/app/services/chat_service.py)

```python
def process_message(self, session_id: int, user_message: str, db: Session) -> dict:
    """Main waterfall logic"""
    
    # Get session and chatbot info
    session = db.query(ChatSession).filter_by(id=session_id).first()
    chatbot_id = session.chatbot_id
    
    # Priority 1: Workflow match
    workflow_response = self._find_workflow_response(
        chatbot_id, user_message, db
    )
    if workflow_response:
        return {"response": workflow_response, "options": []}
    
    # Priority 2: FAQ match
    faq_response = self._find_faq_response(
        chatbot_id, user_message, db
    )
    if faq_response:
        return faq_response  # Includes answer + child options
    
    # Priority 3: RAG query
    rag_response = self._find_rag_response(user_message)
    if rag_response:
        return {"response": rag_response, "options": []}
    
    # Priority 4: Default
    return {"response": DEFAULT_BOT_RESPONSE, "options": []}
```

---

## 🤖 RAG Pipeline Detailed Flow

### **PHASE 1: OFFLINE PIPELINE (When PDF is Uploaded)**

```
User uploads PDF via frontend
              ↓
POST /api/upload/pdf (backend/app/routers/upload.py)
              ↓
┌─────────────────────────────────────────────────────────┐
│  Step 1: Save PDF to disk                               │
│  Location: backend/data/raw_pdfs/filename.pdf           │
│                                                          │
│  Step 2: Text Extraction                                │
│  File: app/rag/offline/text_extractor.py                │
│  ↓                                                       │
│  • Try PyPDF2 text extraction first                     │
│  • Check if text is sparse (< 100 chars or < 5 words)   │
│  • If sparse → Automatically trigger OCR                │
│    - Convert PDF pages to images (300 DPI)              │
│    - Use Tesseract OCR to extract text                  │
│  • Result: Raw text string                              │
│                                                          │
│  Step 3: Text Cleaning                                  │
│  File: app/rag/offline/text_cleaner.py                  │
│  ↓                                                       │
│  • Normalize whitespace (multiple spaces → single)      │
│  • Fix PDF artifacts (broken words, encoding issues)    │
│  • Remove excessive punctuation                         │
│  • Preserve paragraph structure                         │
│  • Result: Clean, normalized text                       │
│                                                          │
│  Step 4: Chunking                                       │
│  File: app/rag/offline/chunker.py                       │
│  ↓                                                       │
│  • Split text into sentences using regex                │
│  • Group sentences until 2000 chars reached             │
│  • Keep 2 sentences overlap between chunks              │
│  • Filter out tiny chunks (< 100 chars)                 │
│  • Result: List of TextChunk objects                    │
│    Example chunk:                                       │
│    {                                                     │
│      'chunk_id': 0,                                     │
│      'text': 'Theory X assumes...',                     │
│      'source_file': 'document.pdf',                     │
│      'chunk_index': 0,                                  │
│      'char_count': 1850                                 │
│    }                                                     │
│                                                          │
│  Step 5: Embedding Generation                           │
│  File: app/rag/offline/embedder.py                      │
│  ↓                                                       │
│  • Load model: all-MiniLM-L12-v2 (120MB, cached)       │
│  • Convert each chunk text → 384-dim vector             │
│  • Normalize vectors (for cosine similarity)            │
│  • Result: NumPy array shape (num_chunks, 384)          │
│                                                          │
│  Step 6: Store in Milvus                                │
│  File: app/rag/storage/milvus_store.py                  │
│  ↓                                                       │
│  • Connect to Milvus (localhost:19530)                  │
│  • Insert chunks with embeddings into 'rag_chunks'      │
│  • Build IVF_FLAT index for fast search                 │
│  • Store metadata: text, source_file, chunk_index       │
│                                                          │
└─────────────────────────────────────────────────────────┘
              ↓
PDF is now searchable! ✓
```

### **PHASE 2: ONLINE PIPELINE (When User Asks Question)**

```
User asks: "What is Theory X?"
              ↓
Chat service calls: rag_service.get_rag_response(question)
              ↓
┌─────────────────────────────────────────────────────────┐
│  Step 1: Query Embedding                                │
│  File: app/rag/online/query_embedder.py                 │
│  ↓                                                       │
│  • Load same model: all-MiniLM-L12-v2 (MUST match!)    │
│  • Convert question → 384-dim vector                    │
│  • Normalize vector                                     │
│  • Time: ~50ms                                          │
│                                                          │
│  Step 2: Vector Similarity Search                       │
│  File: app/rag/online/retriever.py                      │
│  ↓                                                       │
│  • Search Milvus collection 'rag_chunks'                │
│  • Find top-K most similar chunks (K=3)                 │
│  • Filter by min similarity score (threshold=0.3)       │
│  • Similarity metric: Inner Product (cosine)            │
│  • Time: ~100ms                                         │
│  • Result: 0-3 matching chunks with scores              │
│    Example:                                              │
│    [                                                     │
│      {                                                   │
│        'text': 'Theory X assumes employees...',         │
│        'score': 0.46,  # 46% similar                    │
│        'source_file': 'McGregor.pdf',                   │
│        'chunk_index': 5                                 │
│      },                                                  │
│      { 'text': '...', 'score': 0.42, ... },            │
│      { 'text': '...', 'score': 0.35, ... }             │
│    ]                                                     │
│                                                          │
│  Check: Did we find any chunks?                         │
│  • If empty → Return "I don't know based on docs"      │
│  • If found → Continue                                  │
│                                                          │
│  Step 3: Context Assembly                               │
│  File: app/rag/online/context_builder.py                │
│  ↓                                                       │
│  • Combine the 3 chunks into formatted context:         │
│                                                          │
│    Context 1 (from McGregor.pdf):                       │
│    Theory X assumes employees dislike work...           │
│                                                          │
│    Context 2 (from McGregor.pdf):                       │
│    Theory Y believes employees view work as natural...  │
│                                                          │
│    Context 3 (from Leadership.pdf):                     │
│    McGregor's theories influenced management...         │
│                                                          │
│  Step 4: Prompt Engineering                             │
│  File: app/rag/online/prompt_builder.py                 │
│  ↓                                                       │
│  • Build strict RAG prompt:                             │
│                                                          │
│    You are a helpful assistant that answers questions   │
│    based ONLY on the provided context.                  │
│                                                          │
│    CRITICAL RULES:                                      │
│    1. Answer ONLY from the context below                │
│    2. If not in context, say "I don't know"             │
│    3. Do NOT use external knowledge                     │
│    4. Do NOT guess or hallucinate                       │
│                                                          │
│    CONTEXT:                                              │
│    [assembled context from Step 3]                      │
│                                                          │
│    USER QUESTION:                                        │
│    What is Theory X?                                    │
│                                                          │
│    ANSWER:                                               │
│                                                          │
│  Step 5: LLM Generation                                 │
│  File: app/rag/online/generator.py                      │
│  ↓                                                       │
│  • Send prompt to Groq API                              │
│  • Model: llama-3.1-8b-instant                          │
│  • Temperature: 0.0 (completely deterministic)          │
│  • Max tokens: 500                                      │
│  • Time: ~300-700ms                                     │
│  • Result: LLM generated answer                         │
│                                                          │
│    "Theory X is a management theory that assumes        │
│     employees inherently dislike work and need to be    │
│     controlled and directed. According to this theory,  │
│     people avoid responsibility and prefer to be led."  │
│                                                          │
│  Step 6: Response Formatting                            │
│  File: app/rag/online/response_formatter.py             │
│  ↓                                                       │
│  • Clean up LLM response                                │
│  • Optionally add source citations                      │
│  • Return final answer                                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
              ↓
Return answer to chat_service
              ↓
Save to chat_messages table
              ↓
Return to frontend
              ↓
User sees answer in chat interface ✓

Total time: 0.5-1.0 seconds
```

---

## 📡 API Endpoints

### **Chat Endpoints** (backend/app/routers/chat.py)

```
POST /chat/start
Request:  { "chatbot_id": 1 }
Response: {
  "session_id": 123,
  "trigger_nodes": ["Hello", "Help", "Start"]
}
Purpose: Start new chat session, get available triggers

POST /chat/message
Request:  {
  "session_id": 123,
  "message": "What is Theory X?"
}
Response: {
  "response": "Theory X is a management theory...",
  "options": []  // Or list of child FAQs
}
Purpose: Send user message, get bot response
```

### **Chatbot Management** (backend/app/routers/chatbots.py)

```
POST   /chatbots                    Create chatbot
GET    /chatbots                    List all chatbots
GET    /chatbots/{id}               Get specific chatbot
DELETE /chatbots/{id}               Delete chatbot (cascades)
```

### **Workflow Management** (backend/app/routers/workflows.py)

```
POST   /chatbots/{id}/workflows    Create workflow
GET    /chatbots/{id}/workflows    List workflows
PUT    /workflows/{id}/activate    Set active workflow
DELETE /workflows/{id}              Delete workflow
```

### **Node Management** (backend/app/routers/nodes.py)

```
POST   /workflows/{id}/nodes        Create node (trigger/response)
GET    /workflows/{id}/nodes        List nodes
DELETE /nodes/{id}                  Delete node
```

### **Edge Management** (backend/app/routers/edges.py)

```
POST   /workflows/{id}/edges        Create edge (connection)
GET    /workflows/{id}/edges        List edges
DELETE /edges/{id}                  Delete edge
```

### **FAQ Management** (backend/app/routers/faqs.py)

```
POST   /chatbots/{id}/faqs          Create FAQ
GET    /chatbots/{id}/faqs          List FAQs (supports filtering)
GET    /faqs/{id}                   Get specific FAQ
PATCH  /faqs/{id}                   Update FAQ
DELETE /faqs/{id}                   Delete FAQ
```

### **PDF Upload** (backend/app/routers/upload.py)

```
POST   /api/upload/pdf              Upload PDF (triggers RAG indexing)
GET    /api/upload/pdfs             List indexed PDFs
```

---

## 🚀 Project Setup & Running

### **Prerequisites**
```bash
# Backend
- Python 3.8+
- PostgreSQL
- Tesseract OCR
- Poppler (for pdf2image)

# Frontend
- Node.js 16+
- npm or yarn

# Infrastructure
- Docker & Docker Compose (for Milvus)
```

### **Backend Setup**

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
# Create backend/.env file with:
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
GROQ_API_KEY=your_groq_api_key_here
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 5. Start Milvus (Docker)
cd docker/milvus
docker-compose up -d

# 6. Run migrations
cd ../..
python run_migration.py

# 7. Start FastAPI server
uvicorn app.main:app --reload --port 8000

# Backend running at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

### **Frontend Setup**

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev

# Frontend running at: http://localhost:3000
```

### **Access Points**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Milvus Attu UI**: http://localhost:8000 (if Attu enabled)

---

## ✨ Key Features

### **1. Visual Workflow Builder**
- Drag-and-drop interface using ReactFlow
- Create trigger nodes (user inputs)
- Create response nodes (bot replies)
- Connect nodes with edges to define conversation flow
- Set one workflow as active per chatbot

### **2. FAQ System**
- Simple question-answer format
- Nested FAQs (parent-child hierarchy)
- Exact text matching for questions
- Returns child options as follow-up questions

### **3. RAG System**
- Upload PDF documents (max 10MB)
- Automatic OCR for scanned PDFs
- Semantic search (not keyword-based)
- AI-generated answers grounded in documents
- Zero-hallucination enforcement (temp=0.0)
- Returns "I don't know" when uncertain

### **4. Conversation Tracking**
- Complete chat history saved in database
- User and bot messages timestamped
- Sessions linked to chatbots and workflows

### **5. Graceful Degradation**
- If Milvus is down, RAG is skipped (workflows/FAQs still work)
- If Groq API fails, RAG returns None (triggers default response)
- System remains functional even if components fail

---

## 📁 Code Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # All configuration constants
│   ├── database.py                # SQLAlchemy setup
│   ├── logging_config.py          # Logging configuration
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── chatbot.py
│   │   ├── workflow.py
│   │   ├── node.py
│   │   ├── edge.py
│   │   ├── faq.py
│   │   ├── chat_session.py
│   │   └── chat_message.py
│   │
│   ├── routers/                   # API endpoints (FastAPI routers)
│   │   ├── chat.py                # Chat endpoints
│   │   ├── chatbots.py            # Chatbot CRUD
│   │   ├── workflows.py           # Workflow CRUD
│   │   ├── nodes.py               # Node CRUD
│   │   ├── edges.py               # Edge CRUD
│   │   ├── faqs.py                # FAQ CRUD
│   │   └── upload.py              # PDF upload
│   │
│   ├── services/                  # Business logic
│   │   ├── chat_service.py        # ⭐ Main conversation logic (waterfall)
│   │   ├── rag_service.py         # ⭐ RAG pipeline orchestrator
│   │   └── pdf_processing_service.py
│   │
│   ├── rag/                       # RAG pipeline modules
│   │   ├── offline/               # Document ingestion
│   │   │   ├── text_extractor.py  # PDF → Text (with OCR)
│   │   │   ├── text_cleaner.py    # Text cleaning
│   │   │   ├── chunker.py         # Sentence-based chunking
│   │   │   └── embedder.py        # Text → Vectors
│   │   │
│   │   ├── online/                # Query processing
│   │   │   ├── query_embedder.py  # Question → Vector
│   │   │   ├── retriever.py       # Vector search
│   │   │   ├── context_builder.py # Assemble context
│   │   │   ├── prompt_builder.py  # Build LLM prompt
│   │   │   ├── generator.py       # Groq LLM call
│   │   │   └── response_formatter.py
│   │   │
│   │   └── storage/
│   │       └── milvus_store.py    # Vector DB operations
│   │
│   ├── schemas/                   # Pydantic request/response models
│   └── utils/                     # Helper functions
│
├── data/
│   ├── raw_pdfs/                  # Uploaded PDFs
│   └── processed/                 # Processed data
│
├── migrations/                    # SQL migration files
│   ├── 001_split_nodes_edges.sql
│   ├── 002_add_faqs_table.sql
│   └── ...
│
└── docker/
    └── milvus/
        └── docker-compose.yml     # Milvus stack

frontend/
├── app/
│   ├── page.tsx                   # Home page
│   ├── layout.tsx                 # Root layout
│   │
│   ├── chat/[id]/                 # Chat interface
│   │   └── page.tsx
│   │
│   ├── workflows/[id]/            # Workflow builder
│   │   ├── page.tsx
│   │   └── CustomNode.tsx         # ReactFlow node component
│   │
│   ├── chatbots/[id]/             # Chatbot details
│   │   └── page.tsx
│   │
│   └── dashboard/[id]/            # Dashboard
│       └── page.tsx
│
├── components/
│   ├── PdfUploadButton.tsx        # PDF upload component
│   └── Dashboard/                 # Dashboard components
│       ├── ChatInterface.tsx
│       ├── FAQManager.tsx
│       ├── KnowledgeBase.tsx
│       ├── Layout.tsx
│       ├── Sidebar.tsx
│       └── Workflows.tsx
│
└── services/
    └── api.ts                     # API client (Axios wrappers)
```

---

## 🔑 Key Files to Explain

### **Most Important Files (Start Here)**

1. **backend/app/services/chat_service.py** - Main conversation waterfall logic
2. **backend/app/services/rag_service.py** - RAG pipeline orchestrator
3. **backend/app/config.py** - All configuration in one place
4. **backend/app/routers/chat.py** - Chat API endpoints
5. **frontend/services/api.ts** - API calls from frontend

### **Core Conversation Flow**

```
User Message → chat.py (router) 
            → chat_service.py (waterfall logic)
            → workflow/FAQ/RAG check
            → Response back to user
```

### **Core RAG Flow**

```
PDF Upload → upload.py (router)
          → text_extractor.py (extract with OCR)
          → text_cleaner.py (clean)
          → chunker.py (split)
          → embedder.py (vectorize)
          → milvus_store.py (store)

User Query → rag_service.py (orchestrator)
          → query_embedder.py (embed question)
          → retriever.py (search Milvus)
          → context_builder.py (assemble)
          → prompt_builder.py (create prompt)
          → generator.py (call Groq LLM)
          → response_formatter.py (format)
          → Return answer
```

---

## 📊 Data Flow Summary

```
1. User creates chatbot
   → chatbots table in PostgreSQL

2. User designs workflow
   → workflows, nodes, edges tables in PostgreSQL

3. User adds FAQs
   → faqs table in PostgreSQL

4. User uploads PDF
   → data/raw_pdfs/ folder
   → Processed and stored in Milvus vector DB

5. User starts chat
   → chat_sessions table in PostgreSQL

6. User sends message
   → Check workflow (PostgreSQL)
   → Check FAQ (PostgreSQL)
   → Check RAG (Milvus → Groq)
   → chat_messages table (PostgreSQL)

7. User gets response
   → From workflow, FAQ, or RAG
```

---

## 🎓 Explaining to Your Senior - Key Points

### **What Makes This Project Strong**

1. **Multi-Modal Intelligence**
   - Not just one approach - combines structured (workflows) and unstructured (RAG) data
   - Intelligent fallback system ensures comprehensive coverage

2. **Zero-Hallucination RAG**
   - Temperature 0.0 = completely deterministic
   - Strict prompts prevent LLM from making things up
   - Returns "I don't know" instead of guessing

3. **Production-Ready Code**
   - Centralized configuration (config.py)
   - Proper error handling throughout
   - Comprehensive logging
   - Database migrations tracked
   - Type hints in Python

4. **Scalable Architecture**
   - Clear separation of concerns (routers, services, models)
   - Modular RAG pipeline (easy to swap components)
   - Lazy initialization (fast startup)
   - Cascading deletes (data integrity)

5. **Comprehensive Documentation**
   - 8 learning guide files
   - Code comments explain "why" not just "what"
   - Migration history shows project evolution

### **Technical Sophistication**

- **Smart OCR Detection**: Automatically detects scanned PDFs
- **Sentence-Based Chunking**: Preserves semantic meaning
- **Vector Search**: Semantic similarity, not keyword matching
- **Workflow Builder**: Visual tool for non-technical users
- **Nested FAQs**: Multi-level question hierarchy

### **Honest About Scope**

- Redis, Hasura, Celery not implemented (planned for scaling phase)
- Focused on core functionality first
- Ready to scale when needed

---

## 📧 Quick Reference

### **Environment Variables** (backend/.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
GROQ_API_KEY=your_groq_api_key
MILVUS_HOST=localhost
MILVUS_PORT=19530
LOG_LEVEL=INFO
```

### **Important Ports**
- Frontend: 3000
- Backend: 8000
- PostgreSQL: 5432
- Milvus: 19530
- Attu (Milvus UI): 8000

### **Key Configuration** (backend/app/config.py)
```python
# Embedding
EMBEDDING_MODEL = "all-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384

# RAG
RAG_DEFAULT_TOP_K = 3
RAG_DEFAULT_MIN_SCORE = 0.3
RAG_DEFAULT_TEMPERATURE = 0.0

# LLM
LLM_MODEL = "llama3-8b-8192"
LLM_MAX_TOKENS = 1024

# Chunking
max_chars = 2000  # In chunker.py
overlap_sentences = 2
```

---

## 🎯 Demo Script

**When demonstrating to your senior:**

1. Show chatbot creation in UI
2. Build a simple workflow with drag-drop
3. Add a few FAQs
4. Upload a PDF (show it processing)
5. Start a chat and show the waterfall:
   - First message matches workflow → workflow response
   - Second message matches FAQ → FAQ response  
   - Third message about PDF content → RAG response
   - Fourth message gibberish → default response
6. Show conversation history in database
7. Show vectors in Milvus (via Attu UI if available)
8. Show API documentation at /docs

---

**This README covers the complete project flow. Use it as your reference guide when explaining to your senior!**
