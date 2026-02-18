# Code Flow Guide - User Interactions

## 📋 Purpose
This guide explains the complete code execution flow for every user interaction in the chatbot system. It shows which files are called, which functions execute, and how data flows from frontend to backend and back.

**Target Audience**: For explaining to seniors/reviewers how the code works step-by-step.

---

## Table of Contents
1. [User Sends a Chat Message](#1-user-sends-a-chat-message)
2. [User Uploads a PDF](#2-user-uploads-a-pdf)
3. [User Creates a New Chatbot](#3-user-creates-a-new-chatbot)
4. [User Creates a Workflow](#4-user-creates-a-workflow)
5. [User Creates Nodes in Workflow](#5-user-creates-nodes-in-workflow)
6. [User Creates Edges in Workflow](#6-user-creates-edges-in-workflow)
7. [User Adds FAQ](#7-user-adds-faq)
8. [System Startup Flow](#8-system-startup-flow)

---

## 1. User Sends a Chat Message

**Scenario**: User types "What is Theory X?" in the chat interface and presses send.

### Frontend Flow

#### Step 1: User Interface Component
**File**: `frontend/components/Dashboard/ChatInterface.tsx`

**What Happens**:
- User types message in the input field
- Component maintains local state for the current message text
- When user clicks send button or presses Enter, the component calls the message sending function

**State Management**:
- Component stores all previous messages in local state array
- Each message has structure: `{ sender: 'user' | 'bot', text: string, timestamp: Date }`

#### Step 2: API Call to Backend
**File**: `frontend/services/api.ts`

**Function**: `sendMessage(sessionId, messageText)`

**What It Does**:
- Takes the session ID and user's message text
- Constructs HTTP POST request to backend endpoint
- URL: `http://localhost:8000/chat/message`
- Request body: `{ session_id: number, message: string }`
- Uses axios library to make the HTTP request
- Handles response and error states

**Why This File**:
- Centralizes all API communication logic
- Makes backend URL changes easier (change in one place)
- Provides consistent error handling across all API calls

### Backend Flow

#### Step 3: API Router Receives Request
**File**: `backend/app/routers/chat.py`

**Endpoint**: `POST /chat/message`

**Function**: `send_message(request: ChatRequest, db: Session)`

**What It Does**:
- FastAPI receives the HTTP POST request
- Validates the request body using Pydantic schema (ChatRequest)
- Extracts session_id and message from request
- Gets database session from dependency injection
- Calls the chat service to process the message
- Returns the bot's response as JSON

**Input Validation**:
- Pydantic schema ensures session_id is an integer
- Ensures message is a non-empty string
- Returns 422 error if validation fails

#### Step 4: Chat Service - Main Business Logic
**File**: `backend/app/services/chat_service.py`

**Function**: `process_message(session_id, user_message, db)`

**What It Does**:
This is the CORE FUNCTION that implements the waterfall decision logic. Here's the detailed flow:

**Step 4.1: Retrieve Session Information**
- Queries the database to get the chat session by session_id
- Gets the chatbot_id associated with this session
- Validates that the session exists (returns error if not found)

**Step 4.2: Priority 1 - Check Workflow Match**
- Calls internal function `_find_workflow_response(chatbot_id, user_message, db)`
- This function:
  - Queries database for the ACTIVE workflow for this chatbot
  - Gets all nodes where node_type = 'trigger' from this workflow
  - Compares user message with each trigger node's text (exact match, case-sensitive)
  - If match found: Looks up connected response node via edges table
  - Returns the response node's text
- If workflow match found: STOPS here, returns response immediately
- If no match: Continues to next priority

**Step 4.3: Priority 2 - Check FAQ Match**
- Calls internal function `_find_faq_response(chatbot_id, user_message, db)`
- This function:
  - Queries database for all active FAQs for this chatbot
  - Compares user message with each FAQ question (exact match)
  - If match found: Gets the FAQ answer
  - Also queries for child FAQs (where parent_id = matched FAQ id)
  - Returns both the answer and list of child questions as options
- If FAQ match found: STOPS here, returns response with options
- If no match: Continues to next priority

**Step 4.4: Priority 3 - Check RAG (Document Search)**
- Calls `_find_rag_response(user_message)`
- This function:
  - Imports and calls RAGService singleton
  - Passes user message to RAG service
  - RAG service performs semantic search in PDF documents
  - Returns AI-generated answer or None if RAG unavailable
- If RAG returns an answer: STOPS here, returns response
- If RAG returns "I don't know" or None: Continues to fallback

**Step 4.5: Priority 4 - Default Response**
- If none of the above matched, returns default message
- Default message from config: "I didn't understand"

**Step 4.6: Save Conversation to Database**
- Calls internal function `_save_chat_messages(session_id, user_message, bot_response, db)`
- This function:
  - Creates two new records in chat_messages table
  - First record: sender='user', message_text=user_message, timestamp=now
  - Second record: sender='bot', message_text=bot_response, timestamp=now
  - Both linked to the session_id
  - Commits transaction to database

**Step 4.7: Return Response**
- Returns dictionary with response text and options (if any)
- Format: `{ "response": "answer text", "options": ["option1", "option2"] }`

#### Step 5: RAG Service (If RAG Path is Taken)
**File**: `backend/app/services/rag_service.py`

**Function**: `get_rag_response(user_question)`

**What It Does**:
- This is the RAG pipeline orchestrator
- Coordinates all RAG components to generate an answer

**Detailed RAG Flow**:

**Step 5.1: Lazy Initialization**
- Function `_initialize()` is called first
- Checks if RAG components are already loaded
- If not loaded:
  - Loads query embedder (sentence-transformers model)
  - Connects to Milvus vector database
  - Initializes Groq LLM generator
  - Sets initialization flag to True
- If initialization fails: Returns None (graceful degradation)

**Step 5.2: Query Embedding**
- Calls query embedder component
- **File**: `backend/app/rag/online/query_embedder.py`
- **Function**: `embed_query(user_question)`
- **What It Does**:
  - Takes the user's question as plain text
  - Loads the same embedding model used offline (all-MiniLM-L12-v2)
  - Converts text to 384-dimensional vector representation
  - Normalizes the vector for cosine similarity calculation
  - Returns numpy array of shape (384,)
- **Why Same Model**: Query and document embeddings MUST be in the same vector space

**Step 5.3: Vector Similarity Search**
- Calls retriever component
- **File**: `backend/app/rag/online/retriever.py`
- **Function**: `retrieve(query_embedding, top_k=3, min_score=0.3)`
- **What It Does**:
  - Takes the query vector from Step 5.2
  - Connects to Milvus vector database
  - Performs similarity search in 'rag_chunks' collection
  - Uses Inner Product metric (equivalent to cosine similarity for normalized vectors)
  - Retrieves top 3 most similar chunks
  - Filters results by minimum similarity score of 0.3
  - Returns list of matching chunks with metadata (text, score, source_file, chunk_index)
- **If No Results**: Returns empty list (triggers "I don't know" response)
- **Threshold 0.3**: Balanced - not too strict, not too loose

**Step 5.4: Check if Results Found**
- If retriever returns empty list: Return "I don't know based on available information"
- If results found: Continue to context assembly

**Step 5.5: Context Assembly**
- Calls context builder component
- **File**: `backend/app/rag/online/context_builder.py`
- **Function**: `assemble_context(retrieved_chunks, include_sources=True)`
- **What It Does**:
  - Takes the list of retrieved chunks from Step 5.3
  - Formats each chunk with a header and source reference
  - Combines all chunks into a single formatted string
  - Format: "Context 1 (from file.pdf): [text]\n\nContext 2 (from file.pdf): [text]"
  - Returns the complete context string

**Step 5.6: Prompt Construction**
- Calls prompt builder component
- **File**: `backend/app/rag/online/prompt_builder.py`
- **Function**: `build_prompt(question, context, prompt_type='strict')`
- **What It Does**:
  - Takes user question and assembled context
  - Inserts them into a strict RAG prompt template
  - Template includes critical rules: "Answer ONLY from context", "Say I don't know if not in context"
  - Returns complete prompt string ready for LLM
- **Why Strict Template**: Prevents hallucination - forces LLM to stay grounded in documents

**Step 5.7: LLM Generation**
- Calls generator component
- **File**: `backend/app/rag/online/generator.py`
- **Function**: `generate(prompt, max_tokens=500, temperature=0.0)`
- **What It Does**:
  - Takes the complete prompt from Step 5.6
  - Sends HTTP request to Groq API
  - Uses model: llama-3.1-8b-instant
  - Temperature set to 0.0 (completely deterministic, no randomness)
  - Max tokens set to 500 (concise answers)
  - Waits for API response
  - Returns the LLM's generated text
- **Why Temperature 0.0**: Ensures same question always gets same answer, no creative hallucinations

**Step 5.8: Response Formatting**
- Calls response formatter component
- **File**: `backend/app/rag/online/response_formatter.py`
- **Function**: `format_response_simple(llm_answer)`
- **What It Does**:
  - Takes raw LLM output
  - Strips extra whitespace
  - Returns clean answer text
- **Simple Version Used**: Just returns cleaned text (no metadata)

**Step 5.9: Return to Chat Service**
- RAG service returns the final answer
- If any step failed: Returns None
- Chat service receives the answer and proceeds

#### Step 6: Database Operations
**File**: `backend/database.py` and model files

**What Happens**:
- SQLAlchemy ORM handles all database queries
- No raw SQL - uses Python objects and methods
- Queries are built using filter(), join(), etc.
- Transactions ensure data consistency

**Tables Accessed**:
- `chat_sessions` - Read to validate session
- `chatbots` - Read to get chatbot info
- `workflows` - Read to find active workflow
- `nodes` - Read to match triggers and get responses
- `edges` - Read to find connections between nodes
- `faqs` - Read to match questions
- `chat_messages` - Write to save conversation
- Milvus `rag_chunks` - Read for semantic search

### Response Flow Back to Frontend

#### Step 7: Backend Returns JSON Response
**File**: `backend/app/routers/chat.py`

**What Happens**:
- FastAPI serializes the response dictionary to JSON
- Sets HTTP status code 200 (success)
- Adds CORS headers (allows localhost:3000 to receive response)
- Sends response back through HTTP

#### Step 8: Frontend Receives Response
**File**: `frontend/services/api.ts`

**What Happens**:
- Axios receives the HTTP response
- Parses JSON body to JavaScript object
- Returns the response data to the calling component
- If error occurred: Catches and returns error object

#### Step 9: UI Updates
**File**: `frontend/components/Dashboard/ChatInterface.tsx`

**What Happens**:
- Component receives the response from API call
- Updates local state by adding bot message to messages array
- React automatically re-renders the component
- New message appears in the chat interface
- If options provided: Displays them as clickable buttons
- Scrolls chat window to bottom to show new message

**State Update**:
- Adds message object: `{ sender: 'bot', text: response.response, timestamp: new Date() }`
- If options exist: Stores them for rendering as quick reply buttons

---

## 2. User Uploads a PDF

**Scenario**: User clicks PDF upload button and selects a PDF file.

### Frontend Flow

#### Step 1: File Selection
**File**: `frontend/components/PdfUploadButton.tsx`

**What Happens**:
- Component renders a file input element (hidden)
- Button click triggers the file input
- User selects PDF from file system
- onChange event fires when file is selected
- Component validates file type (must be .pdf)
- Component checks file size (max 10MB)

#### Step 2: Form Data Preparation
**File**: `frontend/components/PdfUploadButton.tsx`

**What Happens**:
- Creates new FormData object
- Appends the file to FormData with key 'file'
- FormData handles multipart/form-data encoding automatically

#### Step 3: API Call
**File**: `frontend/services/api.ts`

**Function**: `uploadPdf(formData)`

**What It Does**:
- Makes POST request to backend endpoint
- URL: `http://localhost:8000/api/upload/pdf`
- Content-Type: multipart/form-data (set automatically by axios)
- Includes file in request body
- Can track upload progress via axios onUploadProgress callback

### Backend Flow

#### Step 4: Upload Router Receives File
**File**: `backend/app/routers/upload.py`

**Endpoint**: `POST /api/upload/pdf`

**Function**: `upload_pdf(file: UploadFile)`

**What It Does**:
- FastAPI receives the multipart form data
- UploadFile object provides access to file metadata and content
- Validates file extension (must be .pdf)
- Validates file size (must be < 10MB)
- Generates safe filename or uses original

**Step 4.1: Check for Existing File**
- Constructs file path: `data/raw_pdfs/{filename}`
- Checks if file already exists at this path
- If exists: Deletes old file first
- If deletion fails: Appends timestamp to filename to avoid collision

**Step 4.2: Save File to Disk**
- Creates directory if doesn't exist
- Opens new file in write-binary mode
- Reads uploaded file content in chunks (8KB at a time)
- Writes chunks to disk
- Closes file handle

#### Step 5: Trigger RAG Indexing
**File**: `backend/app/routers/upload.py` continues...

**What Happens**:
- Calls PDF processing service to index the document
- This triggers the entire offline RAG pipeline

**Detailed Offline RAG Pipeline**:

**Step 5.1: Text Extraction**
- **File**: `backend/app/rag/offline/text_extractor.py`
- **Function**: `extract_text_with_ocr(pdf_path)`
- **What It Does**:
  - Opens the PDF file using PyPDF2 library
  - Attempts to extract text from all pages
  - Checks if extracted text is "sparse" (< 100 characters or < 5 readable words)
  - If sparse: This is likely a scanned PDF, triggers OCR
  - **OCR Process** (function `extract_with_ocr`):
    - Uses pdf2image library to convert PDF pages to images at 300 DPI
    - Uses pytesseract library to perform OCR on each image
    - Extracts text from images
    - Combines text from all pages
  - Returns the complete extracted text as a string

**Step 5.2: Text Cleaning**
- **File**: `backend/app/rag/offline/text_cleaner.py`
- **Function**: `clean_text(raw_text, preserve_structure=True)`
- **What It Does**:
  - Takes the raw extracted text
  - **Normalize Whitespace**: Replaces multiple spaces with single space
  - **Fix Line Breaks**: Converts multiple newlines to paragraph breaks
  - **Fix PDF Artifacts**: Removes common PDF extraction issues (broken words, weird characters)
  - **Clean Punctuation**: Removes excessive dots, dashes, special characters
  - **Preserve Paragraphs**: Keeps double newlines to maintain document structure
  - Returns cleaned text

**Step 5.3: Text Chunking**
- **File**: `backend/app/rag/offline/chunker.py`
- **Function**: `chunk_text(text, max_chars=2000, overlap_sentences=2)`
- **What It Does**:
  - Takes cleaned text as input
  - **Split into Sentences**: Uses regex to split text at sentence boundaries (. ! ?)
  - **Group Sentences**: Accumulates sentences until reaching max_chars limit (2000)
  - **Create Chunk**: When limit reached, creates a TextChunk object
  - **Add Overlap**: Includes last 2 sentences from previous chunk in next chunk (context continuity)
  - **Filter Small Chunks**: Removes chunks smaller than 100 characters
  - Returns list of TextChunk objects
- **Each Chunk Contains**:
  - chunk_id: Sequential number
  - text: The actual chunk text
  - source_file: PDF filename
  - chunk_index: Position in document
  - char_count: Number of characters
  - word_count: Number of words

**Step 5.4: Embedding Generation**
- **File**: `backend/app/rag/offline/embedder.py`
- **Function**: `embed_texts(chunk_texts, show_progress=True)`
- **What It Does**:
  - Takes list of chunk texts
  - **Load Model**: Uses sentence-transformers library with all-MiniLM-L12-v2 model
  - **First Time**: Downloads model from HuggingFace (120MB, cached locally)
  - **Subsequent Times**: Loads from cache instantly
  - **Encode Texts**: Converts each text chunk to 384-dimensional vector
  - **Normalization**: Normalizes vectors to unit length (for cosine similarity)
  - Returns numpy array of shape (num_chunks, 384)
- **Why This Model**: Good balance of speed, size, and accuracy

**Step 5.5: Store in Milvus**
- **File**: `backend/app/rag/storage/milvus_store.py`
- **Function**: `insert_chunks(chunks, embeddings, source_file)`
- **What It Does**:
  - Connects to Milvus database (localhost:19530)
  - **Check Collection**: If 'rag_chunks' collection doesn't exist, creates it
  - **Collection Schema**:
    - chunk_id: INT64 (auto-increment primary key)
    - embedding: FLOAT_VECTOR[384]
    - text: VARCHAR[65535]
    - source_file: VARCHAR[512]
    - chunk_index: INT64
  - **Prepare Data**: Converts chunks and embeddings to Milvus format
  - **Insert**: Batch inserts all chunks with embeddings
  - **Build Index**: Creates IVF_FLAT index for fast similarity search
  - **Load Collection**: Loads collection into memory for querying
  - Returns number of entities inserted

**Step 5.6: Save Metadata**
- Updates internal tracking (if implemented)
- Records PDF as indexed and ready for queries

#### Step 6: Return Success Response
**File**: `backend/app/routers/upload.py`

**What Happens**:
- Returns JSON response with success status
- Includes filename and number of chunks indexed
- Response format: `{ "status": "success", "filename": "doc.pdf", "chunks": 42 }`

### Frontend Response

#### Step 7: Update UI
**File**: `frontend/components/PdfUploadButton.tsx`

**What Happens**:
- Receives success response from API
- Shows success message to user
- Updates PDF list (if displayed)
- Resets file input for next upload
- Shows number of chunks indexed

---

## 3. User Creates a New Chatbot

**Scenario**: User fills in chatbot name and description, clicks create button.

### Frontend Flow

#### Step 1: Form Component
**File**: `frontend/app/page.tsx` or chatbot creation form component

**What Happens**:
- Form has input fields for name and description
- Component maintains local state for form values
- onChange handlers update state as user types
- Form validation checks if name is not empty
- onSubmit handler is called when user submits

#### Step 2: API Call
**File**: `frontend/services/api.ts`

**Function**: `createChatbot(name, description)`

**What It Does**:
- Makes POST request to `http://localhost:8000/chatbots`
- Request body: `{ "name": "My Bot", "description": "A helpful bot" }`
- Sets Content-Type: application/json
- Returns created chatbot object with generated ID

### Backend Flow

#### Step 3: Chatbot Router
**File**: `backend/app/routers/chatbots.py`

**Endpoint**: `POST /chatbots`

**Function**: `create_chatbot(chatbot: ChatbotCreate, db: Session)`

**What It Does**:
- Receives request with chatbot data
- Pydantic schema validates the input (name required, description optional)
- Creates new Chatbot model instance
- Sets name and description from request
- Sets created_at to current timestamp (automatic)

#### Step 4: Database Insert
**File**: Database interaction via SQLAlchemy

**What Happens**:
- SQLAlchemy ORM creates INSERT SQL statement
- Executes: `INSERT INTO chatbots (name, description, created_at) VALUES (?, ?, ?)`
- Database generates primary key ID automatically
- Returns the created record with ID

#### Step 5: Return Response
**File**: `backend/app/routers/chatbots.py`

**What Happens**:
- Converts Chatbot model to JSON
- Returns with HTTP 201 (Created) status
- Response includes the generated ID and all fields

### Frontend Response

#### Step 6: Update UI
**File**: Frontend component

**What Happens**:
- Receives chatbot object with new ID
- Adds chatbot to list in state
- React re-renders to show new chatbot
- May redirect to chatbot detail page using the new ID
- Shows success notification

---

## 4. User Creates a Workflow

**Scenario**: User clicks "New Workflow" for a chatbot.

### Frontend Flow

#### Step 1: Workflow Form
**File**: Workflow creation component

**What Happens**:
- User selects a chatbot (if not already selected)
- Enters workflow name
- Submits form

#### Step 2: API Call
**File**: `frontend/services/api.ts`

**Function**: `createWorkflow(chatbotId, workflowName)`

**What It Does**:
- POST to `http://localhost:8000/chatbots/{chatbotId}/workflows`
- Request body: `{ "name": "Customer Support Flow" }`

### Backend Flow

#### Step 3: Workflow Router
**File**: `backend/app/routers/workflows.py`

**Endpoint**: `POST /chatbots/{chatbot_id}/workflows`

**Function**: `create_workflow(chatbot_id: int, workflow: WorkflowCreate, db: Session)`

**What It Does**:
- Validates chatbot_id exists in database
- Creates new Workflow model instance
- Sets chatbot_id (foreign key relationship)
- Sets name from request
- Sets is_active to False (not active initially)
- Sets created_at timestamp

#### Step 4: Database Operations
**File**: Database via SQLAlchemy

**What Happens**:
- Inserts into workflows table
- Foreign key constraint ensures chatbot_id is valid
- If chatbot doesn't exist: Returns 404 error
- Returns created workflow with ID

#### Step 5: Return Response
**File**: `backend/app/routers/workflows.py`

**What Happens**:
- Returns workflow object as JSON
- Includes ID, name, is_active status

### Frontend Response

#### Step 6: Navigate to Workflow Builder
**File**: Frontend routing

**What Happens**:
- Redirects to `/workflows/{workflow_id}` page
- Opens the visual workflow builder
- User can now add nodes and edges

---

## 5. User Creates Nodes in Workflow

**Scenario**: User drags a new node onto the workflow canvas.

### Frontend Flow

#### Step 1: ReactFlow Component
**File**: `frontend/app/workflows/[id]/page.tsx`

**What Happens**:
- Uses @xyflow/react library for drag-drop
- User drags node from palette onto canvas
- ReactFlow fires onNodesChange event
- Component captures new node position and type
- Opens modal/form to enter node details

#### Step 2: Node Details Form
**File**: Custom node component or modal

**What Happens**:
- User selects node type (trigger or response)
- Enters text for the node
- Clicks save

#### Step 3: API Call
**File**: `frontend/services/api.ts`

**Function**: `createNode(workflowId, nodeType, text)`

**What It Does**:
- POST to `http://localhost:8000/workflows/{workflowId}/nodes`
- Request body: `{ "node_type": "trigger", "text": "Hello" }`

### Backend Flow

#### Step 4: Node Router
**File**: `backend/app/routers/nodes.py`

**Endpoint**: `POST /workflows/{workflow_id}/nodes`

**Function**: `create_node(workflow_id: int, node: NodeCreate, db: Session)`

**What It Does**:
- Validates workflow_id exists
- Validates node_type is either 'trigger' or 'response'
- Creates new Node model instance
- Sets workflow_id (foreign key)
- Sets node_type and text from request

#### Step 5: Database Insert
**File**: Database via SQLAlchemy

**What Happens**:
- Inserts into nodes table
- Foreign key links to workflow
- Returns created node with ID

#### Step 6: Return Response
**File**: `backend/app/routers/nodes.py`

**What Happens**:
- Returns node object with generated ID

### Frontend Response

#### Step 7: Update Canvas
**File**: `frontend/app/workflows/[id]/page.tsx`

**What Happens**:
- Receives node with backend-generated ID
- Updates ReactFlow nodes state
- ReactFlow re-renders to show node with correct ID
- Node is now draggable and connectable

---

## 6. User Creates Edges in Workflow

**Scenario**: User drags from one node to another to create a connection.

### Frontend Flow

#### Step 1: Node Connection
**File**: `frontend/app/workflows/[id]/page.tsx`

**What Happens**:
- User clicks and drags from a node's handle
- Drags to another node's handle
- ReactFlow fires onConnect event
- Component receives connection data: source node ID, target node ID

#### Step 2: Validation
**File**: Frontend component

**What Happens**:
- Checks connection is valid (e.g., trigger can only connect to response)
- Prevents duplicate connections
- If valid, proceeds to create edge

#### Step 3: API Call
**File**: `frontend/services/api.ts`

**Function**: `createEdge(workflowId, fromNodeId, toNodeId)`

**What It Does**:
- POST to `http://localhost:8000/workflows/{workflowId}/edges`
- Request body: `{ "from_node_id": 1, "to_node_id": 2 }`

### Backend Flow

#### Step 4: Edge Router
**File**: `backend/app/routers/edges.py`

**Endpoint**: `POST /workflows/{workflow_id}/edges`

**Function**: `create_edge(workflow_id: int, edge: EdgeCreate, db: Session)`

**What It Does**:
- Validates workflow_id exists
- Validates from_node_id and to_node_id exist
- Validates both nodes belong to this workflow
- Checks unique constraint (no duplicate edges)
- Creates new Edge model instance

#### Step 5: Database Insert
**File**: Database via SQLAlchemy

**What Happens**:
- Inserts into edges table
- Unique constraint prevents duplicates: (workflow_id, from_node_id, to_node_id)
- If duplicate: Returns 409 Conflict error
- Foreign keys ensure referential integrity

#### Step 6: Return Response
**File**: `backend/app/routers/edges.py`

**What Happens**:
- Returns edge object with generated ID

### Frontend Response

#### Step 7: Update Canvas
**File**: `frontend/app/workflows/[id]/page.tsx`

**What Happens**:
- Receives edge with backend ID
- Updates ReactFlow edges state
- ReactFlow draws connection line between nodes
- Edge is now visible and selectable

---

## 7. User Adds FAQ

**Scenario**: User creates a new FAQ for their chatbot.

### Frontend Flow

#### Step 1: FAQ Form
**File**: `frontend/components/Dashboard/FAQManager.tsx`

**What Happens**:
- User enters question text
- User enters answer text
- Optionally selects parent FAQ (for nested FAQs)
- Sets display order and active status
- Submits form

#### Step 2: API Call
**File**: `frontend/services/api.ts`

**Function**: `createFaq(chatbotId, question, answer, parentId, displayOrder, isActive)`

**What It Does**:
- POST to `http://localhost:8000/chatbots/{chatbotId}/faqs`
- Request body contains all FAQ fields

### Backend Flow

#### Step 3: FAQ Router
**File**: `backend/app/routers/faqs.py`

**Endpoint**: `POST /chatbots/{chatbot_id}/faqs`

**Function**: `create_faq(chatbot_id: int, faq: FaqCreate, db: Session)`

**What It Does**:
- Validates chatbot_id exists
- Validates parent_id if provided (must be valid FAQ ID)
- Creates new Faq model instance
- Sets all fields from request
- Handles unique constraint validation

#### Step 4: Database Insert
**File**: Database via SQLAlchemy

**What Happens**:
- Inserts into faqs table
- Unique constraint enforced: (chatbot_id, question)
- If duplicate question for this chatbot: Returns 409 error
- Foreign key to chatbot validated
- If parent_id provided: Foreign key to faqs table (self-reference)

#### Step 5: Return Response
**File**: `backend/app/routers/faqs.py`

**What Happens**:
- Returns created FAQ with generated ID
- Includes all fields including relationships

### Frontend Response

#### Step 6: Update UI
**File**: `frontend/components/Dashboard/FAQManager.tsx`

**What Happens**:
- Adds new FAQ to list in state
- React re-renders FAQ list
- New FAQ appears in the interface
- If nested: Shows under parent FAQ
- Form is reset for next FAQ

---

## 8. System Startup Flow

**Scenario**: Developer starts the application.

### Backend Startup

#### Step 1: Main Entry Point
**File**: `backend/app/main.py`

**What Happens When Running**: `uvicorn app.main:app --reload`

**Initialization Sequence**:

**Step 1.1: Import Phase**
- Python imports all modules
- Loads environment variables from .env file
- **File**: `backend/app/config.py` is imported
- Config validates required environment variables (DATABASE_URL, GROQ_API_KEY)
- Creates necessary directories (data/raw_pdfs, data/processed, logs)

**Step 1.2: Database Connection**
- **File**: `backend/database.py` is imported
- Creates SQLAlchemy engine with DATABASE_URL
- Establishes connection pool to PostgreSQL
- Does NOT create tables (must run migrations separately)

**Step 1.3: Create FastAPI App**
- FastAPI() instance is created
- CORS middleware is added (allows localhost:3000)
- Request logging middleware may be added

**Step 1.4: Register Routers**
- All routers are imported and included:
  - chat router → `/chat/*`
  - chatbots router → `/chatbots/*`
  - workflows router → `/workflows/*`
  - nodes router → `/nodes/*`
  - edges router → `/edges/*`
  - faqs router → `/faqs/*`
  - upload router → `/api/upload/*`

**Step 1.5: Startup Events**
- FastAPI fires @app.on_event("startup") if defined
- May check database connection
- May log startup message

**Step 1.6: Ready to Serve**
- Uvicorn starts listening on port 8000
- Accepts incoming HTTP requests
- Console shows: "Application startup complete"

### Frontend Startup

#### Step 2: Next.js Development Server
**File**: Multiple files involved

**What Happens When Running**: `npm run dev`

**Initialization Sequence**:

**Step 2.1: Next.js Initialization**
- Reads `next.config.ts` for configuration
- Sets up Turbopack for fast compilation
- Prepares React 19 runtime

**Step 2.2: Root Layout**
- **File**: `frontend/app/layout.tsx`
- This is the root layout wrapper for all pages
- Loads global styles from `globals.css`
- Sets up TailwindCSS
- Defines HTML structure (head, body)

**Step 2.3: Home Page Load**
- **File**: `frontend/app/page.tsx`
- Default route (/) renders this component
- Component may load initial data (list of chatbots)
- Makes API call to backend to fetch data

**Step 2.4: API Client Setup**
- **File**: `frontend/services/api.ts`
- Axios instance is created with base URL
- Default configuration set (timeout, headers)

**Step 2.5: Ready to Serve**
- Next.js listens on port 3000
- Hot reload enabled (watches for file changes)
- Console shows: "Ready in XXXms"

### RAG Components (Lazy Loading)

#### Step 3: RAG Initialization (On First Query)
**When**: First time user asks a question that reaches RAG

**What Happens**:

**Step 3.1: RAG Service Initialization**
- **File**: `backend/app/services/rag_service.py`
- Function `_initialize()` is called
- Only happens once per application lifetime

**Step 3.2: Load Embedding Model**
- **File**: `backend/app/rag/offline/embedder.py`
- Downloads all-MiniLM-L12-v2 model from HuggingFace (if not cached)
- Model file: 120MB
- Cached in: `~/.cache/torch/sentence_transformers/`
- Loads model into memory
- Takes 2-5 seconds on first load, instant on subsequent loads

**Step 3.3: Connect to Milvus**
- **File**: `backend/app/rag/storage/milvus_store.py`
- Connects to Milvus server (localhost:19530)
- Checks if 'rag_chunks' collection exists
- Loads collection into memory if exists
- If connection fails: RAG is disabled, returns None

**Step 3.4: Initialize Groq Client**
- **File**: `backend/app/rag/online/generator.py`
- Creates Groq API client with API key
- Validates API key format
- Does NOT make API call yet (just initialization)

**Step 3.5: Set Initialization Flag**
- RAG service sets `_initialized = True`
- Subsequent queries skip initialization
- All components are now ready

---

## Key Concepts Explained

### Waterfall Decision Logic
**Why This Pattern**:
- Provides predictable, controlled responses (workflows)
- Falls back to FAQs for common questions
- Uses AI (RAG) only when needed
- Always has a default response

**Order Matters**:
- Workflows checked first: Most controlled, designed conversations
- FAQs checked second: Known questions with fixed answers
- RAG checked third: Flexible but requires documents
- Default last: Ensures user always gets a response

### Lazy Initialization
**Why Used**:
- FastAPI starts quickly (2-3 seconds)
- Heavy ML models loaded only when needed
- If Milvus is down, backend still starts
- System is more resilient to component failures

**Trade-off**:
- First RAG query is slower (3-5 seconds)
- Subsequent queries are fast (0.5-1 second)

### Database Relationships
**How They Work**:
- Foreign keys enforce referential integrity
- Can't create workflow without chatbot
- Can't create node without workflow
- Can't create edge without two nodes

**Cascading Deletes**:
- Delete chatbot → all workflows, FAQs, sessions are deleted
- Delete workflow → all nodes and edges are deleted
- Delete node → all edges connected to it are deleted
- Keeps database clean and consistent

### Session Management
**Purpose**:
- Tracks individual conversations
- Links messages to specific user interactions
- Can have multiple sessions per chatbot
- Allows conversation history and analytics

---

## Common Execution Paths

### Path 1: Workflow Match
```
User message → Chat router → Chat service
→ Check workflows → Match found
→ Get response from edges/nodes
→ Save to database → Return response
```
**Time**: 50-100ms
**Database queries**: 3-4 queries

### Path 2: FAQ Match
```
User message → Chat router → Chat service
→ Check workflows → No match
→ Check FAQs → Match found
→ Get answer and child FAQs
→ Save to database → Return response
```
**Time**: 50-150ms
**Database queries**: 4-5 queries

### Path 3: RAG Match
```
User message → Chat router → Chat service
→ Check workflows → No match
→ Check FAQs → No match
→ Check RAG → RAG service
→ Query embedding (50ms)
→ Vector search (100ms)
→ Context assembly (20ms)
→ Prompt building (10ms)
→ LLM generation (300-700ms)
→ Format response
→ Save to database → Return response
```
**Time**: 500-1000ms
**Database queries**: 3-4 queries
**External APIs**: 1 Groq call

### Path 4: Default Response
```
User message → Chat router → Chat service
→ Check workflows → No match
→ Check FAQs → No match
→ Check RAG → No relevant documents
→ Return default "I didn't understand"
→ Save to database → Return response
```
**Time**: 200-300ms
**Database queries**: 5-6 queries

---

## Tips for Explaining to Your Senior

### Focus on These Key Points:

1. **Waterfall Logic**: Explain why the order matters (controlled → flexible)

2. **Lazy Loading**: Show how it makes the system resilient

3. **Database Relationships**: Demonstrate cascading deletes and referential integrity

4. **RAG Pipeline**: Walk through both offline (PDF upload) and online (query) flows

5. **Separation of Concerns**: Show how routers, services, and models have clear responsibilities

6. **Error Handling**: Mention how the system gracefully handles failures

### Demonstration Flow:

1. Start with simple workflow match (fast, predictable)
2. Show FAQ match with nested options
3. Upload a PDF and explain offline pipeline
4. Ask question about PDF content (show RAG in action)
5. Show database state after each operation
6. Show how deleting chatbot cascades to all related data

### Code Navigation:

- Start at: `chat.py` (entry point)
- Go to: `chat_service.py` (main logic)
- Branch to: `rag_service.py` (if RAG path)
- Show: Database models (understand relationships)
- End at: Frontend component (user sees result)

**This flow guide should help you explain the complete execution path to your senior!**
