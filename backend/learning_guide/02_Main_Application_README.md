# 📚 Part 2: Main Application Entry Point (app/main.py)

## 🎯 What This File Does

The `app/main.py` file is the **heart of your backend**. It:
1. Creates the FastAPI application
2. Sets up CORS (allows frontend to talk to backend)
3. Registers all API routes (chatbots, chat, upload, etc.)
4. Initializes the database on startup

---

## 📋 Complete Code Walkthrough

### **1. Import Everything Needed**

```python
from fastapi import FastAPI
from database import create_tables
from app.routers import chatbots, workflows, nodes, edges, chat, faqs, upload
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging, get_logger
from app.config import CORS_ALLOWED_ORIGINS, LOG_LEVEL, validate_config
```

**What each import does:**
- `FastAPI`: The web framework that powers your backend
- `create_tables`: Function from `database.py` to create database tables
- `app.routers`: All your API endpoint files (like different departments in a company)
- `CORSMiddleware`: Allows your React frontend to make requests to the backend
- `setup_logging`, `get_logger`: Logging configuration for debugging
- `CORS_ALLOWED_ORIGINS`, `LOG_LEVEL`, `validate_config`: Configuration from `config.py`

---

### **2. Setup Logging**

```python
setup_logging(log_level=LOG_LEVEL)
logger = get_logger(__name__)
```

**What this does:**
- Configures logging system (writes to files in `backend/logs/`)
- Creates a logger for this module
- Logs will show what's happening in your app (requests, errors, etc.)

---

### **3. Validate Configuration**

```python
if not validate_config():
    logger.warning("Configuration validation failed - check environment variables")
```

**What this does:**
- Checks if all required environment variables are set (DATABASE_URL, GROQ_API_KEY, etc.)
- Logs a warning if something is missing
- App continues to run (doesn't crash), but features might not work

---

### **4. Create FastAPI Application**

```python
app = FastAPI()
```

**What this does:**
- Creates the main FastAPI application instance
- This `app` object is what runs when you execute `uvicorn app.main:app`

**🔍 Think of FastAPI as a Restaurant:**
- The `app` is the restaurant building
- Routers are different sections (bar, dining room, takeout)
- Endpoints are menu items
- Middleware is the host at the entrance

---

### **5. Add CORS Middleware**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Explanation of each setting:**
- `allow_origins`: List of URLs that can access your API
  - Example: `["http://localhost:3000"]` (your React frontend)
- `allow_credentials`: Allow cookies and auth headers
- `allow_methods=["*"]`: Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
- `allow_headers=["*"]`: Allow all request headers

**🔍 Why CORS?**
Browsers block requests from `localhost:3000` (frontend) to `localhost:8000` (backend) by default for security. CORS middleware tells the browser: "It's okay, these sites can talk to each other."

**Without CORS:**
```
❌ Frontend: "Hey backend, give me chatbot list"
❌ Browser: "BLOCKED! Different origins!"
```

**With CORS:**
```
✅ Frontend: "Hey backend, give me chatbot list"
✅ Backend: "Sure! Access-Control-Allow-Origin: localhost:3000"
✅ Browser: "Okay, allowed!"
```

---

### **6. Register API Routers**

```python
app.include_router(chatbots.router, prefix="/chatbots", tags=["Chatbots"])
app.include_router(workflows.router, prefix="", tags=["Workflows"])
app.include_router(nodes.router, prefix="", tags=["Nodes"])
app.include_router(edges.router, prefix="", tags=["Edges"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(faqs.router, prefix="", tags=["FAQs"])
app.include_router(upload.router, prefix="", tags=["Upload"])
```

**What this does:**
Each `include_router` adds a group of related endpoints to your app.

**Breaking down the parameters:**
- `chatbots.router`: The router object from `app/routers/chatbots.py`
- `prefix="/chatbots"`: All routes in this router start with `/chatbots`
- `tags=["Chatbots"]`: Groups these routes in the documentation

**Example of how prefixes work:**
```python
# In app/routers/chatbots.py
@router.get("")  # This becomes: GET /chatbots
@router.post("")  # This becomes: POST /chatbots
@router.get("/{chatbot_id}")  # This becomes: GET /chatbots/123

# In app/routers/chat.py (prefix="/chat")
@router.post("/start")  # This becomes: POST /chat/start
@router.post("/message")  # This becomes: POST /chat/message
```

---

### **7. Startup Event (Database Initialization)**

```python
@app.on_event("startup")
def startup_event():
    logger.info("Application startup initiated")
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created successfully")
    logger.info("Application startup complete")
```

**What this does:**
- Runs automatically when the FastAPI app starts
- Creates all database tables (if they don't exist)
- Logs the startup process

**🔍 Startup Sequence:**
```
1. You run: uvicorn app.main:app --reload
2. FastAPI loads app/main.py
3. Executes all the code (imports, create app, add middleware, register routers)
4. Calls startup_event()
5. Creates database tables
6. Server is ready to accept requests
```

---

## 🌐 Complete API Structure

After all routers are registered, your API has these endpoints:

### **Chatbot Management**
```
GET    /chatbots           - List all chatbots
POST   /chatbots           - Create new chatbot
GET    /chatbots/{id}      - Get specific chatbot
DELETE /chatbots/{id}      - Delete chatbot
```

### **Workflow Management**
```
GET    /workflows/{chatbot_id}/workflows     - List workflows
POST   /workflows/{chatbot_id}/workflows     - Create workflow
PUT    /workflows/{workflow_id}/activate     - Set active workflow
DELETE /workflows/{workflow_id}             - Delete workflow
```

### **Node & Edge Management**
```
POST   /nodes              - Create node
PUT    /nodes/{node_id}    - Update node
DELETE /nodes/{node_id}    - Delete node
POST   /edges              - Create edge
DELETE /edges/{edge_id}    - Delete edge
```

### **Chat**
```
POST   /chat/start         - Start chat session
POST   /chat/message       - Send message and get response
```

### **FAQ Management**
```
GET    /faqs/{chatbot_id}/faqs    - List FAQs
POST   /faqs/{chatbot_id}/faqs    - Create FAQ
PUT    /faqs/{faq_id}             - Update FAQ
DELETE /faqs/{faq_id}             - Delete FAQ
```

### **PDF Upload**
```
POST   /api/upload/pdf     - Upload and process PDF
GET    /api/upload/pdfs    - List uploaded PDFs
DELETE /api/upload/pdf/{filename} - Delete PDF
```

---

## 🔄 Request Flow Example

**User uploads a PDF:**

```
1. Frontend sends POST request to /api/upload/pdf
   ↓
2. FastAPI receives request
   ↓
3. CORS middleware checks if origin is allowed
   ↓
4. FastAPI finds matching route in upload.router
   ↓
5. Calls upload_pdf() function in app/routers/upload.py
   ↓
6. Function gets database session from get_db()
   ↓
7. Processes PDF, saves to database
   ↓
8. Returns response to frontend
   ↓
9. Database session automatically closes (in finally block)
```

---

## 🎓 Key Concepts to Remember

| Concept | Explanation |
|---------|-------------|
| **FastAPI App** | Main application that handles HTTP requests |
| **Router** | Group of related endpoints (like modules) |
| **Middleware** | Code that runs before/after every request |
| **Prefix** | URL path added to all routes in a router |
| **Startup Event** | Code that runs once when server starts |
| **Tags** | Organize endpoints in the documentation |

---

## 🔗 What's Next?

Now that you understand how the app starts and routes are organized:
- **Part 3**: Configuration (environment variables, settings)
- **Part 8**: API Routers (detailed look at each endpoint)

---

## 💡 Testing Your Understanding

Try this: Look at your terminal when you start the backend. You'll see:
```
INFO:     Application startup initiated
INFO:     Creating database tables...
INFO:     Database tables created successfully
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

This output comes from the `startup_event()` function logging!

You can also visit: **http://localhost:8000/docs** to see all your API endpoints in interactive documentation (auto-generated by FastAPI)!

