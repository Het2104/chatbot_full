# 📚 Part 8: API Routers - Frontend Endpoints (app/routers/)

## 🎯 What API Routers Do

API Routers are the **interface between frontend and backend**. They:
1. Define HTTP endpoints (URLs)
2. Validate incoming requests
3. Call service functions (chat, PDF processing, etc.)
4. Return JSON responses to frontend

Think of routers as **restaurant waiters** that take orders (requests) and bring food (responses).

---

## 🌐 Complete API Structure

Your backend has 7 main routers:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `chatbots.py` | `/chatbots` | Manage chatbots |
| `workflows.py` | `/workflows` | Manage workflows |
| `nodes.py` | `/nodes` | Manage workflow nodes |
| `edges.py` | `/edges` | Manage workflow edges |
| `faqs.py` | `/faqs` | Manage FAQ Q&A |
| `chat.py` | `/chat` | Chat conversations |
| `upload.py` | `/api/upload` | Upload PDFs |

---

## 📋 Router Walkthroughs

### **1. Chatbots Router (app/routers/chatbots.py)**

#### **Create Chatbot**
```python
@router.post("", response_model=ChatbotResponse, status_code=201)
def create_chatbot(chatbot: ChatbotCreate, db: Session = Depends(get_db)):
    """Create a new chatbot"""
    db_chatbot = Chatbot(
        name=chatbot.name,
        description=chatbot.description
    )
    db.add(db_chatbot)
    db.commit()
    db.refresh(db_chatbot)
    return db_chatbot
```

**HTTP Request:**
```http
POST /chatbots
Content-Type: application/json

{
  "name": "Support Bot",
  "description": "Helps customers"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Support Bot",
  "description": "Helps customers",
  "created_at": "2026-02-11T10:30:00Z"
}
```

**What happens:**
1. FastAPI receives POST request to `/chatbots`
2. Validates JSON matches `ChatbotCreate` schema
3. Creates new `Chatbot` database record
4. Commits to database
5. Returns chatbot as JSON

---

#### **List All Chatbots**
```python
@router.get("", response_model=List[ChatbotResponse])
def list_chatbots(db: Session = Depends(get_db)):
    """List all chatbots"""
    chatbots = db.query(Chatbot).all()
    return chatbots
```

**HTTP Request:**
```http
GET /chatbots
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Support Bot",
    "description": "Helps customers",
    "created_at": "2026-02-11T10:30:00Z"
  },
  {
    "id": 2,
    "name": "Sales Bot",
    "description": "Helps with sales",
    "created_at": "2026-02-11T11:00:00Z"
  }
]
```

---

#### **Get Specific Chatbot**
```python
@router.get("/{chatbot_id}", response_model=ChatbotResponse)
def get_chatbot(chatbot_id: int, db: Session = Depends(get_db)):
    """Get a specific chatbot by ID"""
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    return chatbot
```

**HTTP Request:**
```http
GET /chatbots/1
```

**Response (Success):**
```json
{
  "id": 1,
  "name": "Support Bot",
  "description": "Helps customers",
  "created_at": "2026-02-11T10:30:00Z"
}
```

**Response (Not Found):**
```json
{
  "detail": "Chatbot with ID 1 not found."
}
```
Status: `404 Not Found`

---

#### **Delete Chatbot**
```python
@router.delete("/{chatbot_id}", status_code=204)
def delete_chatbot(chatbot_id: int, db: Session = Depends(get_db)):
    """Delete a chatbot and all related workflows and nodes"""
    chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=entity_not_found_error("Chatbot", chatbot_id)
        )
    
    db.delete(chatbot)
    db.commit()
    return None
```

**HTTP Request:**
```http
DELETE /chatbots/1
```

**Response:**
```
Status: 204 No Content
(No body)
```

**What gets deleted:**
Due to `cascade="all, delete-orphan"` in models:
- The chatbot
- All its workflows
- All nodes in those workflows
- All edges in those workflows
- All chat sessions
- All chat messages
- All FAQs

---

### **2. Chat Router (app/routers/chat.py)**

#### **Start Chat Session**
```python
@router.post("/start", response_model=ChatStartResponse, status_code=201)
def start_chat(request: ChatStartRequest, db: Session = Depends(get_db)):
    """Start a new chat session with a chatbot"""
    try:
        session = start_chat_session(request.chatbot_id, db)
        return ChatStartResponse(
            session_id=session.id,
            chatbot_id=session.chatbot_id,
            workflow_id=session.workflow_id,
            started_at=session.started_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**HTTP Request:**
```http
POST /chat/start
Content-Type: application/json

{
  "chatbot_id": 1
}
```

**Response:**
```json
{
  "session_id": 42,
  "chatbot_id": 1,
  "workflow_id": 5,
  "started_at": "2026-02-11T10:30:00Z"
}
```

**Frontend should:**
- Save `session_id` (needed for all future messages)
- Use it in all `/chat/message` requests

---

#### **Send Message**
```python
@router.post("/message", response_model=ChatMessageResponse)
def send_message(request: ChatMessageRequest, db: Session = Depends(get_db)):
    """Send a message to the chatbot and get a response with optional contextual FAQ options"""
    try:
        bot_response, options, session = process_message(
            request.session_id, 
            request.message, 
            db
        )
        return ChatMessageResponse(
            session_id=session.id,
            user_message=request.message,
            bot_response=bot_response,
            options=options,
            timestamp=datetime.utcnow()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**HTTP Request:**
```http
POST /chat/message
Content-Type: application/json

{
  "session_id": 42,
  "message": "What is PyPDF2?"
}
```

**Response:**
```json
{
  "session_id": 42,
  "user_message": "What is PyPDF2?",
  "bot_response": "PyPDF2 is a Python library that can extract text from PDFs, merge multiple PDFs, split PDFs...",
  "options": [],
  "timestamp": "2026-02-11T10:30:05Z"
}
```

**Response with FAQ Options:**
```json
{
  "session_id": 42,
  "user_message": "How do I reset my password?",
  "bot_response": "Click 'Forgot Password' on the login page.",
  "options": [
    "I didn't receive the reset email",
    "My reset link expired"
  ],
  "timestamp": "2026-02-11T10:30:05Z"
}
```

**Frontend can:**
- Display `bot_response` as bot message
- Show `options` as clickable buttons
- When user clicks option, send it as the next message

---

### **3. Upload Router (app/routers/upload.py)**

#### **Upload PDF**
```python
@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file
    - Accepts PDF files up to 10MB
    - Automatically processes and indexes the document
    - Returns processing statistics
    """
    # Validate file type
    if not validate_file_extension(file.filename, ALLOWED_FILE_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=invalid_file_type_error(file.filename, ALLOWED_FILE_EXTENSIONS)
        )
    
    # Save file
    file_path = os.path.join(RAW_PDFS_DIR, safe_filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=file_too_large_error(MAX_FILE_SIZE_MB)
            )
        f.write(content)
    
    # Process PDF
    service = PDFProcessingService()
    result = service.process_pdf(file_path, safe_filename)
    
    # Return result
    if result["success"]:
        return UploadResponse(
            success=True,
            message="PDF uploaded and processed successfully",
            filename=safe_filename,
            stats=result["stats"]
        )
    else:
        # Delete file if processing failed
        ensure_file_deleted(file_path)
        raise HTTPException(
            status_code=500,
            detail=upload_failed_error(result.get("error", "Unknown error"))
        )
```

**HTTP Request:**
```http
POST /api/upload/pdf
Content-Type: multipart/form-data

file: [company_handbook.pdf]
```

**Response (Success):**
```json
{
  "success": true,
  "message": "PDF uploaded and processed successfully",
  "filename": "company_handbook.pdf",
  "stats": {
    "text_length": 45230,
    "cleaned_length": 43180,
    "num_chunks": 87,
    "processing_time_seconds": 12.5
  }
}
```

**Response (Error - Invalid File Type):**
```json
{
  "detail": "Invalid file type. Allowed: .pdf"
}
```
Status: `400 Bad Request`

**Response (Error - File Too Large):**
```json
{
  "detail": "File too large. Maximum size: 10 MB"
}
```
Status: `413 Payload Too Large`

**Response (Error - Processing Failed):**
```json
{
  "detail": "Upload failed: No text extracted from PDF"
}
```
Status: `500 Internal Server Error`

---

#### **List Uploaded PDFs**
```python
@router.get("/pdfs", response_model=PDFListResponse)
async def list_pdfs():
    """List all uploaded and indexed PDF files"""
    result = get_indexed_pdfs()
    return PDFListResponse(
        pdfs=result["pdfs"],
        count=result["count"]
    )
```

**HTTP Request:**
```http
GET /api/upload/pdfs
```

**Response:**
```json
{
  "pdfs": [
    {
      "filename": "company_handbook.pdf",
      "size_bytes": 2403840,
      "size_mb": 2.29,
      "uploaded_at": 1707648600.0
    },
    {
      "filename": "pypdf2_docs.pdf",
      "size_bytes": 1048576,
      "size_mb": 1.0,
      "uploaded_at": 1707652200.0
    }
  ],
  "count": 2
}
```

---

#### **Delete PDF**
```python
@router.delete("/pdf/{filename}")
async def delete_pdf(filename: str):
    """Delete a PDF file"""
    file_path = os.path.join(RAW_PDFS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=file_not_found_error(filename)
        )
    
    if ensure_file_deleted(file_path):
        return {"success": True, "message": f"Deleted {filename}"}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete {filename}"
        )
```

**HTTP Request:**
```http
DELETE /api/upload/pdf/company_handbook.pdf
```

**Response:**
```json
{
  "success": true,
  "message": "Deleted company_handbook.pdf"
}
```

**Note:** This only deletes the file, not the chunks in Milvus. To fully remove a document from RAG, you'd need to also delete its chunks from Milvus.

---

## 🎓 Key Concepts

### **1. Path Parameters**
```python
@router.get("/{chatbot_id}")
def get_chatbot(chatbot_id: int, ...):
```
```http
GET /chatbots/1  → chatbot_id = 1
GET /chatbots/5  → chatbot_id = 5
```

### **2. Request Body**
```python
def create_chatbot(chatbot: ChatbotCreate, ...):
```
```http
POST /chatbots
{ "name": "Bot", "description": "..." }
```

### **3. Query Parameters**
```python
@router.get("/search")
def search(q: str, limit: int = 10):
```
```http
GET /search?q=hello&limit=20
```

### **4. Dependency Injection**
```python
db: Session = Depends(get_db)
```
- Automatically creates database session
- Passes it to function
- Closes it after function completes

### **5. Response Models**
```python
response_model=ChatbotResponse
```
- Validates response data
- Auto-generates JSON schema
- Shows in API documentation

### **6. Status Codes**
```python
status_code=201  # Created
status_code=204  # No Content
status_code=400  # Bad Request
status_code=404  # Not Found
status_code=500  # Internal Server Error
```

---

## 🔗 Frontend Integration Example

### **React Component Example:**

```javascript
// Start chat
const startChat = async (chatbotId) => {
  const response = await fetch('http://localhost:8000/chat/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chatbot_id: chatbotId })
  });
  const data = await response.json();
  return data.session_id;
};

// Send message
const sendMessage = async (sessionId, message) => {
  const response = await fetch('http://localhost:8000/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      session_id: sessionId, 
      message: message 
    })
  });
  const data = await response.json();
  return data;
};

// Upload PDF
const uploadPDF = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/api/upload/pdf', {
    method: 'POST',
    body: formData
  });
  const data = await response.json();
  return data;
};

// Usage
const chatbotId = 1;
const sessionId = await startChat(chatbotId);
const result = await sendMessage(sessionId, "Hello!");
console.log(result.bot_response);
```

---

## 💡 API Documentation

FastAPI auto-generates interactive documentation!

**Visit these URLs when your backend is running:**

1. **Swagger UI** (interactive):
   ```
   http://localhost:8000/docs
   ```
   - Try endpoints directly in browser
   - See request/response schemas
   - Test with real data

2. **ReDoc** (clean documentation):
   ```
   http://localhost:8000/redoc
   ```
   - Beautiful, readable documentation
   - Better for sharing with team

---

## 🎯 Complete API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| **Chatbots** | | |
| POST | `/chatbots` | Create chatbot |
| GET | `/chatbots` | List all chatbots |
| GET | `/chatbots/{id}` | Get chatbot details |
| DELETE | `/chatbots/{id}` | Delete chatbot |
| **Chat** | | |
| POST | `/chat/start` | Start chat session |
| POST | `/chat/message` | Send message, get response |
| **Upload** | | |
| POST | `/api/upload/pdf` | Upload & process PDF |
| GET | `/api/upload/pdfs` | List uploaded PDFs |
| DELETE | `/api/upload/pdf/{filename}` | Delete PDF file |
| **Workflows** | | |
| GET | `/workflows/{chatbot_id}/workflows` | List workflows |
| POST | `/workflows/{chatbot_id}/workflows` | Create workflow |
| PUT | `/workflows/{workflow_id}/activate` | Activate workflow |
| DELETE | `/workflows/{workflow_id}` | Delete workflow |
| **Nodes** | | |
| POST | `/nodes` | Create node |
| PUT | `/nodes/{node_id}` | Update node |
| DELETE | `/nodes/{node_id}` | Delete node |
| **Edges** | | |
| POST | `/edges` | Create edge |
| DELETE | `/edges/{edge_id}` | Delete edge |
| **FAQs** | | |
| GET | `/faqs/{chatbot_id}/faqs` | List FAQs |
| POST | `/faqs/{chatbot_id}/faqs` | Create FAQ |
| PUT | `/faqs/{faq_id}` | Update FAQ |
| DELETE | `/faqs/{faq_id}` | Delete FAQ |

---

## ✅ Congratulations!

You've now completed the full backend walkthrough! You understand:
1. ✅ Database structure and models
2. ✅ How the app starts and initializes
3. ✅ Configuration and environment variables
4. ✅ RAG system (answering from PDFs)
5. ✅ PDF processing pipeline
6. ✅ Chat logic and message handling
7. ✅ API endpoints and frontend integration

**Next steps:**
- Explore the frontend code
- Try modifying the API
- Add new features
- Build something amazing! 🚀

