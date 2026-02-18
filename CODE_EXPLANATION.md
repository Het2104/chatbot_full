# Chatbot System - Complete Code Explanation

## Table of Contents
1. [System Overview](#system-overview)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Data Flow Walkthrough](#data-flow-walkthrough)
5. [Key Features Explained](#key-features-explained)

---

## System Overview

This is a **FastAPI backend + Next.js frontend** chatbot system that supports:
- Multiple chatbots
- Workflow-based conversations (trigger → response nodes connected by edges)
- FAQ system with parent-child relationships
- RAG (Retrieval Augmented Generation) for PDF document Q&A
- Chat sessions with message history

### Technology Stack
- **Backend**: FastAPI (Python), SQLAlchemy, PostgreSQL, Milvus (vector DB)
- **Frontend**: Next.js 14+, TypeScript, React, TailwindCSS
- **AI/ML**: Sentence Transformers (embeddings), OpenAI/LLM integration

---

## Backend Architecture

### 1. Entry Point (`main.py`)
**What it does:**
- Creates the FastAPI app
- Configures CORS (Cross-Origin Resource Sharing) to allow frontend (localhost:3000) to call backend APIs
- Registers all routers (endpoints) for chatbots, workflows, nodes, edges, chat, FAQs, and uploads
- On startup: creates database tables if they don't exist
- Validates configuration (checks environment variables)

### 2. Configuration (`config.py`)
**What it does:**
- Centralizes all "magic numbers" and settings in one place
- Loads environment variables from `.env` file (like DATABASE_URL)
- Defines file upload limits (10MB max for PDFs)
- Sets OCR configuration (DPI, tesseract paths, poppler paths)
- Sets RAG configuration (embedding model, similarity thresholds)
- Makes the codebase easier to maintain (change settings in one place)

### 3. Database Models (`app/models/`)
**Database tables:**

#### `Chatbot`
- Represents a chatbot instance
- Fields: `id`, `name`, `description`, `created_at`
- One chatbot can have many workflows, FAQs, and chat sessions

#### `Workflow`
- A conversation workflow (collection of nodes and edges)
- Fields: `id`, `chatbot_id`, `name`, `is_active`
- Each workflow belongs to one chatbot
- Contains trigger and response nodes

#### `Node`
- A node in a workflow (can be "trigger" or "response")
- Fields: `id`, `workflow_id`, `node_type`, `text`
- **Trigger nodes**: Start a conversation (e.g., "Check Order Status")
- **Response nodes**: Bot responses (e.g., "Please provide your order number")
- Nodes are connected by edges

#### `Edge`
- Connects two nodes (defines conversation flow)
- Fields: `id`, `workflow_id`, `from_node_id`, `to_node_id`
- Creates a directed graph: Node A → Node B

#### `FAQ`
- Frequently Asked Questions with parent-child hierarchy
- Fields: `id`, `chatbot_id`, `question`, `answer`, `parent_id`, `is_active`, `display_order`
- Parent FAQs: shown as initial options (parent_id is NULL)
- Child FAQs: follow-up questions (parent_id points to parent FAQ)

#### `ChatSession`
- A conversation session between user and bot
- Fields: `id`, `chatbot_id`, `workflow_id`, `started_at`
- Tracks which chatbot is being used

#### `ChatMessage`
- Individual messages in a chat session
- Fields: `id`, `session_id`, `sender` (user/bot), `message_text`, `timestamp`
- Stores complete conversation history

### 4. API Routers (`app/routers/`)

#### `chatbots.py` - Chatbot Management
**Endpoints:**
- `POST /chatbots` - Create a new chatbot
- `GET /chatbots` - List all chatbots
- `GET /chatbots/{id}` - Get single chatbot
- `DELETE /chatbots/{id}` - Delete chatbot (cascades to workflows, nodes, edges)

#### `workflows.py` - Workflow Management
**Endpoints:**
- `POST /chatbots/{id}/workflows` - Create workflow for a chatbot
- `GET /chatbots/{id}/workflows` - List all workflows for a chatbot
- `PUT /workflows/{id}/activate` - Activate workflow (deactivates others)
- `DELETE /workflows/{id}` - Delete workflow

**Key behavior:**
- Only one workflow can be "active" per chatbot at a time
- Activating a workflow automatically deactivates all others for that chatbot

#### `nodes.py` - Node Management
**Endpoints:**
- `POST /workflows/{id}/nodes` - Create node in workflow
- `GET /workflows/{id}/nodes` - List all nodes in workflow
- `DELETE /nodes/{id}` - Delete node

**Validation:**
- Prevents duplicate trigger nodes with same text in same workflow
- Only allows node_type of "trigger" or "response"

#### `edges.py` - Edge Management
**Endpoints:**
- `POST /workflows/{id}/edges` - Create edge (connect two nodes)
- `GET /workflows/{id}/edges` - List all edges in workflow
- `DELETE /edges/{id}` - Delete edge

**Validation:**
- Ensures both nodes exist and belong to same workflow
- Prevents connecting nodes from different workflows

#### `faqs.py` - FAQ Management
**Endpoints:**
- `POST /chatbots/{id}/faqs` - Create FAQ for chatbot
- `GET /chatbots/{id}/faqs` - List FAQs (with filters: active_only, parent_only)
- `GET /faqs/{id}` - Get single FAQ
- `PATCH /faqs/{id}` - Update FAQ
- `DELETE /faqs/{id}` - Delete FAQ

**Key behavior:**
- Questions must be unique per chatbot
- Parent-child hierarchy allows nested FAQs
- `display_order` controls the order FAQs are shown

#### `chat.py` - Chat Conversation
**Endpoints:**
- `POST /chat/start` - Start new chat session
  - Creates ChatSession
  - Returns all trigger nodes from all workflows
  - Client displays these as initial conversation starters
  
- `POST /chat/message` - Send message and get response
  - Processes user message through multiple fallback layers
  - Returns bot response + optional next options
  - Saves both user and bot messages to database

#### `upload.py` - PDF Upload & Processing
**Endpoints:**
- `POST /api/upload/pdf` - Upload and process PDF
  - Validates file type and size
  - Extracts text (with OCR fallback for scanned PDFs)
  - Splits text into chunks
  - Generates embeddings
  - Stores in Milvus vector database
  - Returns processing statistics
  
- `GET /api/upload/pdfs` - List all indexed PDFs
- `DELETE /api/upload/pdf/{filename}` - Delete PDF file (not vectors)

### 5. Services (`app/services/`)

#### `chat_service.py` - Core Chat Logic
**Main functions:**

##### `start_chat_session(chatbot_id, db)`
1. Validates chatbot exists
2. Creates new ChatSession (workflow_id is now nullable)
3. Gets all trigger nodes from all workflows for this chatbot
4. Returns session + trigger nodes list

##### `process_message(session_id, user_message, db)`
**Message Processing Flow (Waterfall Pattern):**

1. **Try to find Node by text** (trigger or response node)
   - Search all nodes in chatbot's workflows where `node.text == user_message`
   - If found and has children:
     - Return "Please choose:" + child node options
   - If found and is leaf node:
     - Return the node's text as final response

2. **If no node match, try FAQ exact match**
   - Search FAQs where `question == user_message` and `is_active == True`
   - If found:
     - Return FAQ answer
     - Get child FAQs (if any) as next options

3. **If no FAQ match, try RAG (PDF documents)**
   - Query vector database for relevant document chunks
   - Use LLM to generate answer from retrieved context
   - If successful, return RAG-generated answer

4. **If all fail, return default response**
   - "I don't have information about that. Please rephrase or contact support."

5. **Save messages to database**
   - Save user message
   - Save bot response
   - Commit to ChatMessage table

**Helper functions:**
- `_get_all_trigger_nodes()` - Get all trigger nodes for a chatbot
- `_get_node_children()` - Get child nodes connected by edges
- `_find_node_by_text()` - Search for node by exact text match
- `_find_faq_response()` - Search for FAQ match and get child FAQs
- `_find_rag_response()` - Query RAG system for PDF-based answer
- `_save_chat_messages()` - Persist user + bot messages

#### `pdf_processing_service.py` - PDF Processing
**Main class: `PDFProcessingService`**

**`process_pdf(file_path, filename)`:**
1. **Text Extraction**
   - Try PyPDF2 first (for regular PDFs)
   - If text is sparse/unreadable, use OCR
   - OCR converts PDF pages to images, then uses Tesseract
   
2. **Text Cleaning**
   - Remove excess whitespace, special characters
   - Normalize line breaks
   
3. **Chunking**
   - Split text into overlapping chunks (for better context)
   - Used by RAG to find relevant passages
   
4. **Embedding & Storage**
   - Generate vector embeddings using sentence transformers
   - Store in Milvus vector database with metadata (filename, chunk_id)
   
5. **Return statistics**
   - Number of chunks created
   - Processing time
   - Text lengths (original vs cleaned)

**`get_indexed_pdfs()`:**
- Lists all PDF files in `data/raw_pdfs/`
- Returns filename, size, upload date

#### `rag_service.py` - Retrieval Augmented Generation
**Main class: `RAGService` (Singleton pattern)**

**`get_rag_response(query)`:**
1. **Query Embedding**
   - Convert user question to vector embedding
   
2. **Vector Search**
   - Search Milvus for top-k most similar document chunks
   - Use similarity threshold to filter irrelevant results
   
3. **Context Building**
   - Combine retrieved chunks into context
   
4. **LLM Generation**
   - Send context + query to LLM (OpenAI/other)
   - LLM generates answer based on retrieved documents
   
5. **Fallback**
   - If no relevant docs found: return "I don't know" message
   - If error: return None (triggers fallback to default response)

### 6. Utilities (`app/utils/`)

#### `common.py`
- `sanitize_filename()` - Remove special chars from filenames
- `add_timestamp_to_filename()` - Add timestamp to avoid conflicts
- `validate_file_extension()` - Check if file type is allowed
- `ensure_file_deleted()` - Safely delete files
- `count_readable_words()` - Count real words (filters gibberish)

#### `errors.py`
- Centralizes all error messages
- Functions return formatted error strings
- Makes error messages consistent across app

---

## Frontend Architecture

### 1. API Service (`services/api.ts`)
**Purpose:** Centralize all backend API calls

**Pattern used:**
- `request<T>(path, options)` - Generic HTTP request function
- Type-safe API functions for each endpoint
- Handles JSON serialization/deserialization
- Proper error handling and status code checking

**API Functions:**
- **Chatbots**: `getChatbots()`, `createChatbot()`, `deleteChatbot()`
- **Workflows**: `getWorkflows()`, `createWorkflow()`, `activateWorkflow()`, `deleteWorkflow()`
- **Nodes**: `getNodes()`, `createNode()`, `deleteNode()`
- **Edges**: `getEdges()`, `createEdge()`, `deleteEdge()`
- **FAQs**: `getFAQs()`, `createFAQ()`, `updateFAQ()`, `deleteFAQ()`, `getParentFAQs()`
- **Chat**: `startChat()`, `sendMessage()`
- **Upload**: `uploadPdf()`, `getIndexedPdfs()`, `deletePdf()`

### 2. Chat Interface (`components/Dashboard/ChatInterface.tsx`)
**Main Component for Chat UI**

**State Management:**
- `sessionId` - Current chat session ID
- `messages` - Array of user/bot messages
- `inputValue` - Current input text
- `triggerNodes` - Initial workflow triggers
- `faqs` - Parent FAQs for quick access
- `loading`, `sending` - UI states

**Lifecycle:**

#### `useEffect` (on mount/chatbot change):
1. Fetch chatbot details (get name)
2. Call `startChat(chatbotId)` - creates session, gets trigger nodes
3. Call `getParentFAQs(chatbotId)` - gets FAQ suggestions
4. Display initial greeting message

#### `handleSendMessage(text)`:
1. Add user message to UI immediately (optimistic update)
2. Call `sendMessage(sessionId, text)` API
3. Add bot response to UI with options (if any)
4. Display options as clickable buttons

**UI Features:**
- **Message bubbles**: Different styles for user vs bot
- **Options**: Clickable buttons for trigger nodes, child nodes, child FAQs
- **FAQs**: Quick-access buttons at bottom
- **Auto-scroll**: Scrolls to bottom on new messages
- **Loading states**: Shows when connecting or sending

---

## Data Flow Walkthrough

### Scenario 1: Starting a Chat

**Frontend:**
1. User opens chat page with `chatbotId=1`
2. `ChatInterface` calls `startChat(1)`

**Backend:**
```
POST /chat/start { chatbot_id: 1 }
↓
chat_service.start_chat_session(1, db)
↓
1. Find chatbot (validate exists)
2. Create ChatSession (chatbot_id=1, workflow_id=null)
3. Query all trigger nodes for this chatbot
4. Return { session_id: 123, trigger_nodes: [...] }
```

**Frontend:**
3. Receives `session_id=123` and trigger nodes
4. Stores sessionId in state
5. Displays trigger nodes as clickable buttons
6. Also fetches and displays parent FAQs

### Scenario 2: User Clicks Trigger Node

**Frontend:**
1. User clicks trigger button with text "Check Order Status"
2. `handleSendMessage("Check Order Status")` called

**Backend:**
```
POST /chat/message { session_id: 123, message: "Check Order Status" }
↓
chat_service.process_message(123, "Check Order Status", db)
↓
1. Find node where text = "Check Order Status"
   - Found: trigger node (id=5) in workflow
   
2. Get children of node 5
   - Edge: node 5 → node 6
   - Node 6 text: "Please provide your order number"
   
3. Save messages:
   - User: "Check Order Status"
   - Bot: "Please choose:"
   
4. Return { 
     bot_response: "Please choose:",
     options: [{ id: 6, text: "Please provide your order number" }]
   }
```

**Frontend:**
3. Displays bot response with option button
4. User can click "Please provide your order number" to continue

### Scenario 3: User Asks FAQ Question

**Frontend:**
1. User clicks FAQ button "What are your business hours?"

**Backend:**
```
POST /chat/message { session_id: 123, message: "What are your business hours?" }
↓
process_message()
↓
1. Try to find node - NOT FOUND
2. Try to find FAQ:
   - Found FAQ (id=10): 
     question: "What are your business hours?"
     answer: "We're open Monday-Friday 9am-5pm EST"
   - FAQ has child FAQs: ["Holiday hours", "Support hours"]
   
3. Save messages
4. Return {
     bot_response: "We're open Monday-Friday 9am-5pm EST",
     options: [
       { text: "Holiday hours" },
       { text: "Support hours" }
     ]
   }
```

**Frontend:**
3. Displays answer with follow-up options

### Scenario 4: User Asks About PDF Content

**Frontend:**
1. User types: "What is the refund policy?" (from uploaded PDF)

**Backend:**
```
POST /chat/message { session_id: 123, message: "What is the refund policy?" }
↓
process_message()
↓
1. Try to find node - NOT FOUND
2. Try to find FAQ - NOT FOUND
3. Try RAG:
   
   rag_service.get_rag_response("What is the refund policy?")
   ↓
   a. Generate embedding for query
   b. Search Milvus vector DB for similar chunks
   c. Found relevant chunks from "policy.pdf"
   d. Send chunks + query to LLM
   e. LLM generates: "According to our policy, you can request a full refund within 30 days..."
   
4. Save messages
5. Return {
     bot_response: "According to our policy, you can request a full refund within 30 days...",
     options: []
   }
```

**Frontend:**
3. Displays RAG-generated answer

### Scenario 5: Uploading a PDF

**Frontend:**
1. User selects PDF file (e.g., "policy.pdf")
2. Calls `uploadPdf(file)`

**Backend:**
```
POST /api/upload/pdf (multipart/form-data)
↓
upload.py: upload_pdf()
↓
1. Validate file type (.pdf) and size (<10MB)
2. Save to data/raw_pdfs/policy.pdf
3. Call pdf_processing_service.process_pdf()
   
   PDFProcessingService.process_pdf()
   ↓
   a. Extract text (PyPDF2 or OCR)
   b. Clean text (remove extra whitespace)
   c. Chunk text (overlapping chunks)
   d. Generate embeddings (sentence-transformers)
   e. Store in Milvus (vectors + metadata)
   
4. Return {
     success: true,
     filename: "policy.pdf",
     stats: { num_chunks: 42, processing_time: 3.2 }
   }
```

**Frontend:**
3. Displays success message with statistics

---

## Key Features Explained

### 1. Workflow System (Node-Edge Graph)
**How it works:**
- Trigger nodes are conversation starters
- Response nodes are bot replies
- Edges connect nodes (define conversation flow)
- When user message matches a node, bot follows edges to get next options
- Allows building complex conversation trees

**Example:**
```
Trigger: "Book a room"
  ↓ (edge)
Response: "What type of room?"
  ↓ (edge)         ↓ (edge)
"Single"        "Double"
```

### 2. FAQ System (Parent-Child Hierarchy)
**How it works:**
- Parent FAQs: Top-level questions (parent_id = NULL)
- Child FAQs: Follow-up questions (parent_id points to parent)
- When parent FAQ is matched, children are shown as options
- Allows drilling down into topics

**Example:**
```
Parent FAQ: "Pricing"
  → Answer: "We have three plans..."
  → Children:
     - "What's included in Basic?"
     - "What's included in Pro?"
```

### 3. RAG (Retrieval Augmented Generation)
**How it works:**
- PDFs are split into chunks and embedded (converted to vectors)
- User question is also embedded
- Vector similarity search finds relevant chunks
- Chunks are sent to LLM as context
- LLM generates answer grounded in documents
- Prevents hallucination (LLM can only use provided context)

**Why chunking?**
- LLMs have token limits
- Smaller chunks = more precise retrieval
- Overlapping chunks = better context preservation

### 4. Message Processing Waterfall
**Why this order?**
1. **Nodes first**: Specific workflow steps take priority
2. **FAQs second**: Predefined Q&A for common questions
3. **RAG third**: Flexible AI-powered answers for unknown questions
4. **Default last**: Graceful fallback when nothing matches

This ensures predictable behavior while allowing flexibility.

### 5. Singleton Pattern (RAG Service)
**Why?**
- RAG service loads heavy models (embeddings, vector DB connection)
- Loading on every request would be slow and wasteful
- Singleton ensures one instance shared across all requests
- Models stay in memory for fast inference

### 6. Session Management
**Why track sessions?**
- Associates messages with specific conversations
- Allows retrieving conversation history
- Enables context-aware responses (future enhancement)
- Tracks which chatbot is being used

---

## API Contracts (Request/Response Structures)

### Chat APIs

**POST /chat/start**
```json
Request:  { "chatbot_id": 1 }
Response: {
  "session_id": 123,
  "chatbot_id": 1,
  "trigger_nodes": [
    { "id": 5, "text": "Check Order", "workflow_id": 2 },
    { "id": 8, "text": "Track Shipment", "workflow_id": 3 }
  ],
  "started_at": "2026-02-17T10:30:00Z"
}
```

**POST /chat/message**
```json
Request:  { "session_id": 123, "message": "Check Order" }
Response: {
  "session_id": 123,
  "user_message": "Check Order",
  "bot_response": "Please choose:",
  "options": [
    { "id": 6, "text": "Enter order number" }
  ],
  "timestamp": "2026-02-17T10:31:00Z"
}
```

### Upload API

**POST /api/upload/pdf**
```json
Request:  multipart/form-data with file field
Response: {
  "success": true,
  "message": "Successfully processed 42 chunks from policy.pdf",
  "filename": "policy.pdf",
  "stats": {
    "text_length": 15234,
    "cleaned_length": 14890,
    "num_chunks": 42,
    "processing_time_seconds": 3.2
  }
}
```

---

## Summary

This chatbot system combines:
1. **Structured workflows** (predictable conversation paths)
2. **FAQs** (quick answers to common questions)
3. **RAG** (AI-powered answers from documents)
4. **Chat sessions** (conversation tracking)

The architecture is modular, maintainable, and allows easy extension. The waterfall message processing ensures users get the most relevant response type while maintaining predictability.
