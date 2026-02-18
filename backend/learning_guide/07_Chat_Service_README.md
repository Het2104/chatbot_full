# 📚 Part 7: Chat Service - Conversation Logic (app/services/chat_service.py)

## 🎯 What This Service Does

The Chat Service is the **brain of your chatbot**. It:
1. Starts new chat sessions
2. Processes user messages
3. Decides how to respond (Workflow, FAQ, RAG, or Default)
4. Saves all messages to the database

---

## 🔄 Complete Message Processing Flow

```
User sends message
        ↓
1. Find chat session
        ↓
2. Try Workflow match (exact match)
   ├─ Found? → Return workflow response ✅
   └─ Not found? ↓
3. Try FAQ match (exact match)
   ├─ Found? → Return FAQ answer + child options ✅
   └─ Not found? ↓
4. Try RAG (semantic search in PDFs)
   ├─ Found? → Return RAG answer ✅
   └─ Not found? ↓
5. Return default response ("I don't understand...")
        ↓
6. Save user message + bot response to database
        ↓
Done!
```

---

## 📋 Complete Code Walkthrough

### **1. Start Chat Session**

```python
def start_chat_session(chatbot_id: int, db: Session) -> ChatSession:
    """
    Start a new chat session with the active workflow of a chatbot.
    """
```

**What this does:**

#### **Step 1: Find the Chatbot**
```python
chatbot = db.query(Chatbot).filter(Chatbot.id == chatbot_id).first()
if not chatbot:
    raise ValueError(entity_not_found_error("Chatbot", chatbot_id))
```

**Example:**
```python
# User wants to chat with "Support Bot" (id=1)
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()
# Returns: Chatbot(id=1, name="Support Bot")
```

#### **Step 2: Find Active Workflow**
```python
active_workflow = db.query(Workflow).filter(
    Workflow.chatbot_id == chatbot_id,
    Workflow.is_active == True
).first()

if not active_workflow:
    raise ValueError(no_active_workflow_error(chatbot_id))
```

**What's an "Active Workflow"?**
- Each chatbot can have multiple workflows
- But only ONE can be active at a time
- Active workflow = the one currently being used for conversations

**Example:**
```python
Chatbot "Support Bot" has:
- Workflow 1: "Main Flow" (is_active=True) ← Will be used
- Workflow 2: "Old Flow" (is_active=False)
- Workflow 3: "Test Flow" (is_active=False)
```

#### **Step 3: Create Chat Session**
```python
session = ChatSession(
    chatbot_id=chatbot_id,
    workflow_id=active_workflow.id
)
db.add(session)
db.commit()
db.refresh(session)
```

**What this creates:**
```python
ChatSession(
    id=42,  # Auto-generated
    chatbot_id=1,
    workflow_id=5,
    started_at="2026-02-11 10:30:00"
)
```

**Why we need sessions:**
- Track conversation history
- Link messages together
- Know which workflow to use
- Support multiple simultaneous conversations

---

### **2. Process Message - Main Logic**

```python
def process_message(session_id: int, user_message: str, db: Session) 
    -> Tuple[str, List[str], ChatSession]:
    """
    Process a user message and return bot response with optional contextual options.
    """
```

**Return values explained:**
- `bot_response` (str): The bot's reply
- `options` (List[str]): Optional follow-up questions (from FAQs)
- `session` (ChatSession): The session object

---

#### **Step 1: Find Chat Session**
```python
session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
if not session:
    raise ValueError(entity_not_found_error("Chat session", session_id))
```

---

#### **Step 2: Try Workflow Match (Highest Priority)**

```python
workflow_response = _find_workflow_response(session, user_message, db)
if workflow_response is not None:
    bot_response = workflow_response
    logger.info("Response generated from workflow")
```

**What `_find_workflow_response()` does:**

```python
def _find_workflow_response(session, user_message, db):
    # Find input node with EXACT text match
    matching_input = db.query(Node).filter(
        Node.workflow_id == session.workflow_id,
        Node.node_type == "input",
        Node.text == user_message  # EXACT match!
    ).first()
    
    if not matching_input:
        return None  # No match
    
    # Find edge from this input
    edge = db.query(Edge).filter(
        Edge.from_node_id == matching_input.id
    ).first()
    
    if not edge:
        return None
    
    # Find output node
    output_node = db.query(Node).filter(
        Node.id == edge.to_node_id,
        Node.node_type == "output"
    ).first()
    
    return output_node.text if output_node else None
```

**Example:**
```
User types: "I want to buy"

Database has:
Input Node (id=10, text="I want to buy")
   ↓ Edge
Output Node (id=11, text="Great! What product are you interested in?")

Result: Returns "Great! What product are you interested in?"
```

**Key Point: EXACT MATCH ONLY**
```python
"I want to buy" == "I want to buy" ✅ Match!
"I want to buy" == "I want to purchase" ❌ No match
"I want to buy" == "i want to buy" ❌ No match (case-sensitive)
```

---

#### **Step 3: Try FAQ Match (Second Priority)**

```python
else:
    faq_response, faq_options = _find_faq_response(session, user_message, db)
    if faq_response is not None:
        bot_response = faq_response
        options = faq_options
        logger.info("Response generated from FAQ")
```

**What `_find_faq_response()` does:**

```python
def _find_faq_response(session, user_message, db):
    # Find FAQ with EXACT question match
    matching_faq = db.query(FAQ).filter(
        FAQ.chatbot_id == session.chatbot_id,
        FAQ.question == user_message,  # EXACT match!
        FAQ.is_active == True
    ).first()
    
    if not matching_faq:
        return None, []
    
    # Find child FAQs (follow-up questions)
    child_faqs = db.query(FAQ).filter(
        FAQ.parent_id == matching_faq.id,
        FAQ.is_active == True
    ).order_by(FAQ.display_order, FAQ.created_at).all()
    
    options = [child.question for child in child_faqs]
    
    return matching_faq.answer, options
```

**Example:**
```
User types: "How do I reset my password?"

Database has:
FAQ(id=5, question="How do I reset my password?", 
    answer="Click 'Forgot Password' on the login page.")

Child FAQs:
- FAQ(id=10, question="I didn't receive the reset email", parent_id=5)
- FAQ(id=11, question="My reset link expired", parent_id=5)

Result: 
bot_response = "Click 'Forgot Password' on the login page."
options = ["I didn't receive the reset email", "My reset link expired"]
```

**Why options are useful:**
- Guides user to follow-up questions
- Creates a conversation tree
- Better user experience

---

#### **Step 4: Try RAG (Third Priority)**

```python
else:
    rag_response = _find_rag_response(user_message, db)
    if rag_response is not None:
        bot_response = rag_response
        logger.info("Response generated from RAG")
```

**What `_find_rag_response()` does:**

```python
def _find_rag_response(user_message, db):
    try:
        from app.services.rag_service import get_rag_service
        
        # Get RAG service
        rag_service = get_rag_service()
        
        # Check if RAG is available
        if not rag_service.is_available():
            return None  # RAG not ready
        
        # Get answer from RAG
        answer = rag_service.get_rag_response(user_message)
        
        return answer
        
    except Exception as e:
        logger.error(f"RAG error: {e}")
        return None  # Don't break chat if RAG fails
```

**Key Points:**
- Uses semantic search (doesn't need exact match)
- Searches uploaded PDF documents
- Returns None if no relevant documents found
- Returns None if Milvus/Groq not available

**Example:**
```
User types: "What are the features of PyPDF2?"

RAG searches PDFs and finds relevant sections:
Result: "PyPDF2 is a Python library that can extract text, merge PDFs..."
```

---

#### **Step 5: Default Response (Fallback)**

```python
else:
    logger.warning("No matching response found, using default")
    # bot_response already set to DEFAULT_BOT_RESPONSE
```

**When this happens:**
- No workflow match
- No FAQ match
- RAG doesn't find relevant documents OR RAG not available

**Default response:**
```python
bot_response = DEFAULT_BOT_RESPONSE  # "I don't understand. Can you rephrase?"
```

---

#### **Step 6: Save Messages to Database**

```python
_save_chat_messages(session_id, user_message, bot_response, db)
```

**What this does:**
```python
def _save_chat_messages(session_id, user_message, bot_response, db):
    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        sender="user",
        message_text=user_message
    )
    db.add(user_msg)
    
    # Save bot message
    bot_msg = ChatMessage(
        session_id=session_id,
        sender="bot",
        message_text=bot_response
    )
    db.add(bot_msg)
    
    db.commit()
```

**Result in database:**
```
chat_messages table:
id  session_id  sender  message_text                  timestamp
1   42          user    "Hello"                       10:30:00
2   42          bot     "Hi! How can I help you?"     10:30:01
3   42          user    "What is PyPDF2?"             10:30:15
4   42          bot     "PyPDF2 is a Python library..." 10:30:16
```

---

## 🎓 Complete Example: User Conversation

### **Scenario: User Chats with Support Bot**

**1. Start Chat Session**
```http
POST /chat/start
{ "chatbot_id": 1 }

Response:
{
  "session_id": 42,
  "chatbot_id": 1,
  "workflow_id": 5,
  "started_at": "2026-02-11T10:30:00Z"
}
```

**2. User says: "I want to buy"** (Workflow match)
```http
POST /chat/message
{ "session_id": 42, "message": "I want to buy" }

Processing:
1. Check workflow → MATCH! (Input node: "I want to buy")
2. Find output node → "Great! What product are you interested in?"
3. Save messages
4. Return response

Response:
{
  "bot_response": "Great! What product are you interested in?",
  "options": []
}
```

**3. User says: "How do I reset my password?"** (FAQ match)
```http
POST /chat/message
{ "session_id": 42, "message": "How do I reset my password?" }

Processing:
1. Check workflow → No match
2. Check FAQ → MATCH! (FAQ: "How do I reset my password?")
3. Find child FAQs → 2 follow-up questions
4. Save messages
5. Return response

Response:
{
  "bot_response": "Click 'Forgot Password' on the login page.",
  "options": [
    "I didn't receive the reset email",
    "My reset link expired"
  ]
}
```

**4. User says: "What are the features of PyPDF2?"** (RAG)
```http
POST /chat/message
{ "session_id": 42, "message": "What are the features of PyPDF2?" }

Processing:
1. Check workflow → No match
2. Check FAQ → No match
3. Check RAG → Search PDFs → FOUND!
4. Save messages
5. Return response

Response:
{
  "bot_response": "PyPDF2 is a Python library with several key features: 1. Extract text from PDFs, 2. Merge PDFs, 3. Split PDFs...",
  "options": []
}
```

**5. User says: "asdflkjh"** (No match - Default)
```http
POST /chat/message
{ "session_id": 42, "message": "asdflkjh" }

Processing:
1. Check workflow → No match
2. Check FAQ → No match
3. Check RAG → No relevant documents
4. Use default response
5. Save messages
6. Return response

Response:
{
  "bot_response": "I don't understand. Can you rephrase?",
  "options": []
}
```

---

## 🔗 Response Priority Order

```
1. Workflow (exact match)     ← Highest priority
   ↓ (if no match)
2. FAQ (exact match)
   ↓ (if no match)
3. RAG (semantic search)
   ↓ (if not available or no match)
4. Default response           ← Lowest priority (fallback)
```

**Why this order?**
- **Workflow**: Designed conversation flows (most controlled)
- **FAQ**: Pre-defined Q&A (controlled but flexible)
- **RAG**: AI-generated from documents (less controlled)
- **Default**: Last resort

---

## 💡 Key Design Decisions

### **1. Exact Match for Workflow/FAQ**
- Ensures predictable behavior
- Users know exactly what to type for specific responses
- Frontend can show buttons with exact text

### **2. Semantic Search for RAG**
- Handles variations in questions
- More flexible and natural
- Requires PDF documents

### **3. Graceful Degradation**
- If workflow doesn't match, try FAQ
- If FAQ doesn't match, try RAG
- If RAG unavailable, use default
- Chat NEVER breaks

### **4. Message History**
- Every message is saved
- Can review conversations later
- Can analyze chatbot performance
- Can train better responses

---

## 🔗 What's Next?

Now that you understand the chat logic:
- **Part 8**: API Routers (how frontend calls these functions)

---

## ❓ Quick Reference

**Functions:**
- `start_chat_session()` - Create new chat session
- `process_message()` - Handle user message
- `_find_workflow_response()` - Try workflow match
- `_find_faq_response()` - Try FAQ match
- `_find_rag_response()` - Try RAG search
- `_save_chat_messages()` - Save to database

**Priority Order:**
```
Workflow → FAQ → RAG → Default
```

**Response Types:**
- Workflow: Exact match, predefined flow
- FAQ: Exact match, Q&A with child options
- RAG: Semantic search, AI-generated from PDFs
- Default: Fallback when nothing matches

