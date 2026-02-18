# 📚 Part 4: Database Models (app/models/)

## 🎯 What Database Models Are

Database models are **Python classes that represent your database tables**. Each class defines:
1. Table name
2. Columns (fields)
3. Relationships to other tables
4. Constraints (unique, nullable, etc.)

Think of them as **blueprints for your data structure**.

---

## 🏗️ Your Database Structure

### **1. Base Model (app/models/base.py)**

```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()
```

**What this does:**
- Creates the base class that ALL models inherit from
- Gives models the ability to create tables in the database
- All your models extend this base: `class Chatbot(Base)`

---

### **2. Chatbot Model (app/models/chatbot.py)**

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Chatbot(Base):
    __tablename__ = "chatbots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workflows = relationship("Workflow", back_populates="chatbot", 
                           cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="chatbot", 
                               cascade="all, delete-orphan")
    faqs = relationship("FAQ", back_populates="chatbot", 
                       cascade="all, delete-orphan")
```

**Column Explanations:**

| Column | Type | Explanation |
|--------|------|-------------|
| `id` | Integer | Unique identifier, auto-increments |
| `name` | String | Chatbot name (required) |
| `description` | String | Optional description |
| `created_at` | DateTime | Auto-set when created |

**Column Modifiers:**
- `primary_key=True`: This is the unique ID
- `index=True`: Create database index for faster searches
- `nullable=False`: This field is required (can't be empty)
- `server_default=func.now()`: Database sets this automatically

**Relationships Explained:**
```python
workflows = relationship("Workflow", back_populates="chatbot", 
                       cascade="all, delete-orphan")
```
- Each chatbot can have multiple workflows
- `back_populates="chatbot"`: Two-way relationship
- `cascade="all, delete-orphan"`: When chatbot is deleted, delete all its workflows too

**Cascade Options:**
- `all`: Propagate all operations (delete, update, etc.)
- `delete-orphan`: Delete child if removed from parent's collection

---

### **3. Workflow Model**

```python
class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chatbot = relationship("Chatbot", back_populates="workflows")
    nodes = relationship("Node", back_populates="workflow", 
                        cascade="all, delete-orphan")
```

**New Concept: Foreign Key**
```python
chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
```
- Links this workflow to a specific chatbot
- `ForeignKey("chatbots.id")`: References the `id` column in `chatbots` table
- This creates a **parent-child relationship**

**Example in database:**
```
Chatbot ID=1: "Customer Support Bot"
  └── Workflow ID=1: "Main Flow" (chatbot_id=1)
  └── Workflow ID=2: "FAQ Flow" (chatbot_id=1)
  
Chatbot ID=2: "Sales Bot"  
  └── Workflow ID=3: "Sales Flow" (chatbot_id=2)
```

---

### **4. Node Model**

```python
class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    node_type = Column(String, nullable=False)  # "input" or "output"
    text = Column(String, nullable=False)
    x_position = Column(Float, default=0)
    y_position = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")
    outgoing_edges = relationship("Edge", foreign_keys="Edge.from_node_id",
                                 cascade="all, delete-orphan")
    incoming_edges = relationship("Edge", foreign_keys="Edge.to_node_id",
                                 cascade="all, delete-orphan")
```

**Node Types:**
- `"input"`: User message that triggers a response
- `"output"`: Bot response to show

**Position Fields:**
- `x_position`, `y_position`: For visual workflow builder
- Stores where node appears on canvas

**Complex Relationships:**
```python
outgoing_edges = relationship("Edge", foreign_keys="Edge.from_node_id")
incoming_edges = relationship("Edge", foreign_keys="Edge.to_node_id")
```
- A node can have edges going OUT (outgoing) and edges coming IN (incoming)
- Needs `foreign_keys` parameter because Edge has TWO foreign keys to Node

---

### **5. Edge Model**

```python
class Edge(Base):
    __tablename__ = "edges"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    from_node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    workflow = relationship("Workflow")
    from_node = relationship("Node", foreign_keys=[from_node_id])
    to_node = relationship("Node", foreign_keys=[to_node_id])
```

**What Edges Do:**
- Connect nodes together
- Define conversation flow: Input → Output

**Example:**
```
Input Node (id=1): "I want to buy"
     ↓ [Edge connects them]
Output Node (id=2): "Great! What product?"
```

---

### **6. FAQ Model**

```python
class FAQ(Base):
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("faqs.id"), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chatbot = relationship("Chatbot", back_populates="faqs")
    parent = relationship("FAQ", remote_side=[id], backref="children")
```

**Special Feature: Self-Referencing**
```python
parent_id = Column(Integer, ForeignKey("faqs.id"), nullable=True)
parent = relationship("FAQ", remote_side=[id], backref="children")
```
- An FAQ can have a parent FAQ
- Creates a tree structure (nested FAQs)

**Example FAQ Tree:**
```
FAQ 1: "I need help" (parent_id=NULL)
  ├── FAQ 2: "Technical support" (parent_id=1)
  │   ├── FAQ 4: "Can't login" (parent_id=2)
  │   └── FAQ 5: "Forgot password" (parent_id=2)
  └── FAQ 3: "Billing support" (parent_id=1)
      └── FAQ 6: "Refund request" (parent_id=3)
```

---

### **7. Chat Session & Message Models**

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    chatbot_id = Column(Integer, ForeignKey("chatbots.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chatbot = relationship("Chatbot", back_populates="chat_sessions")
    workflow = relationship("Workflow")
    messages = relationship("ChatMessage", back_populates="session", 
                          cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "bot"
    message_text = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
```

**How Chat Works:**
1. User starts chat → Create `ChatSession`
2. User sends message → Create `ChatMessage` (sender="user")
3. Bot responds → Create `ChatMessage` (sender="bot")
4. All messages linked to the same session

---

## 🔗 Complete Relationship Diagram

```
Chatbot (1)
  ├── has many Workflows (N)
  │     └── each Workflow has many Nodes (N)
  │           └── Nodes connected by Edges (N)
  ├── has many ChatSessions (N)
  │     └── each Session has many ChatMessages (N)
  └── has many FAQs (N)
        └── each FAQ can have child FAQs (N)
```

**Legend:**
- `(1)` = One
- `(N)` = Many

---

## 🎓 Common Database Operations

### **1. Create a Chatbot with Workflow**
```python
# Create chatbot
chatbot = Chatbot(name="Support Bot", description="Helps customers")
db.add(chatbot)
db.commit()
db.refresh(chatbot)  # Gets the auto-generated ID

# Create workflow for this chatbot
workflow = Workflow(
    chatbot_id=chatbot.id,
    name="Main Flow",
    is_active=True
)
db.add(workflow)
db.commit()
```

### **2. Query with Relationships**
```python
# Get chatbot with all its workflows
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()
print(chatbot.workflows)  # Access related workflows automatically!

# Get workflow with its nodes
workflow = db.query(Workflow).filter(Workflow.id == 1).first()
print(workflow.nodes)  # Access related nodes
print(workflow.chatbot.name)  # Access parent chatbot
```

### **3. Delete with Cascade**
```python
# Delete chatbot - automatically deletes all related data
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()
db.delete(chatbot)
db.commit()

# This also deletes:
# - All workflows of this chatbot
# - All nodes in those workflows
# - All edges in those workflows
# - All chat sessions
# - All chat messages in those sessions
# - All FAQs
```

---

## 🔗 What's Next?

Now that you understand the database structure:
- **Part 5**: RAG Service (how PDFs are queried)
- **Part 6**: PDF Processing (how PDFs are uploaded and indexed)
- **Part 7**: Chat Service (how conversations work)

---

## 💡 Quick Reference

**Key SQLAlchemy Concepts:**

| Concept | Purpose |
|---------|---------|
| `Column()` | Define a table column |
| `Integer, String, Boolean` | Column data types |
| `ForeignKey()` | Link to another table |
| `relationship()` | Access related objects |
| `back_populates` | Two-way relationship |
| `cascade` | Delete/update behavior |
| `nullable=False` | Required field |
| `default=value` | Default value |
| `index=True` | Speed up searches |

