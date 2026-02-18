# 📚 Part 1: Database Foundation (database.py)

## 🎯 What This File Does

The `database.py` file is the **foundation of your entire backend**. It sets up:
1. Connection to PostgreSQL database
2. Session management (how we talk to the database)
3. Functions to create/drop tables

---

## 📋 Complete Code Walkthrough

### **1. Import Required Libraries**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.config import DATABASE_URL
```

**What each import does:**
- `create_engine`: Creates a connection to the database
- `sessionmaker`: Factory that creates database sessions
- `Base`: Base class for all your models (Chatbot, Workflow, Node, etc.)
- `DATABASE_URL`: Your database connection string from `.env` file

---

### **2. Create Database Engine**

```python
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)
```

**Explanation:**
- `DATABASE_URL`: Connection string like `postgresql://user:password@localhost/chatbot_db`
- `echo=False`: Don't print all SQL queries (set to `True` for debugging)
- `pool_pre_ping=True`: Check connection is alive before using it (prevents stale connections)

**🔍 What's an Engine?**
Think of it as a **factory that creates connections** to your database. It manages:
- Connection pooling (reusing connections)
- Connection recycling (closing old connections)
- Thread safety

---

### **3. Create Session Factory**

```python
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

**Explanation:**
- `autocommit=False`: Changes are NOT saved automatically (you must call `db.commit()`)
- `autoflush=False`: Changes are NOT sent to DB automatically before queries
- `bind=engine`: Connect this session factory to our database engine

**🔍 What's a Session?**
A session is like a **shopping cart** for database operations:
- You add items (create records)
- You modify items (update records)
- You remove items (delete records)
- You checkout (commit) to save all changes at once

---

### **4. Get Database Session (Dependency Injection)**

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Explanation:**
This function is used in FastAPI routes with `Depends(get_db)`.

**How it works:**
1. Creates a new database session
2. `yield db` - Gives the session to your route function
3. After route finishes, `finally` runs and closes the session
4. This ensures connections are ALWAYS closed (even if errors occur)

**Example usage in a route:**
```python
@router.get("/chatbots")
def list_chatbots(db: Session = Depends(get_db)):
    # db is automatically created and will auto-close when done
    chatbots = db.query(Chatbot).all()
    return chatbots
```

---

### **5. Create All Tables**

```python
def create_tables():
    Base.metadata.create_all(bind=engine)
```

**What this does:**
- Reads all your model classes (Chatbot, Workflow, Node, Edge, etc.)
- Creates corresponding tables in PostgreSQL
- Only creates tables that don't exist yet (safe to run multiple times)

**When it runs:**
- Called automatically when your FastAPI app starts (in `app/main.py`)

---

### **6. Drop All Tables**

```python
def drop_tables():
    Base.metadata.drop_all(bind=engine)
```

**What this does:**
- **DANGEROUS**: Deletes ALL tables and data
- Used in migration scripts to reset the database
- Never call this in production!

---

## 🏗️ How Database Models Connect

All your models inherit from `Base`:

```python
# In app/models/chatbot.py
class Chatbot(Base):
    __tablename__ = "chatbots"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # ...
```

When you call `Base.metadata.create_all()`, SQLAlchemy:
1. Finds all classes that inherit from `Base`
2. Reads their `__tablename__` and `Column` definitions
3. Generates SQL `CREATE TABLE` statements
4. Executes them in PostgreSQL

---

## 🔄 Typical Database Workflow

### **1. Create a Record**
```python
# In a route
def create_chatbot(chatbot: ChatbotCreate, db: Session = Depends(get_db)):
    # Create new chatbot instance
    db_chatbot = Chatbot(name=chatbot.name, description=chatbot.description)
    
    # Add to session (shopping cart)
    db.add(db_chatbot)
    
    # Save to database
    db.commit()
    
    # Refresh to get auto-generated ID
    db.refresh(db_chatbot)
    
    return db_chatbot
```

### **2. Query Records**
```python
# Get all chatbots
chatbots = db.query(Chatbot).all()

# Get one chatbot by ID
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()

# Get with condition
active_workflows = db.query(Workflow).filter(Workflow.is_active == True).all()
```

### **3. Update a Record**
```python
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()
chatbot.name = "New Name"
db.commit()
```

### **4. Delete a Record**
```python
chatbot = db.query(Chatbot).filter(Chatbot.id == 1).first()
db.delete(chatbot)
db.commit()
```

---

## 🎓 Key Concepts to Remember

| Concept | Explanation |
|---------|-------------|
| **Engine** | Factory that creates database connections |
| **Session** | Shopping cart for database operations |
| **Base** | Parent class for all models |
| **commit()** | Save all changes to database |
| **rollback()** | Undo all changes since last commit |
| **close()** | Close the database connection |

---

## 🔗 What's Next?

Now that you understand the database foundation, the next step is to see:
- **Part 2**: How the main application (`app/main.py`) starts up and connects everything
- **Part 4**: What database models (tables) you have and their relationships

---

## 💡 Common Questions

**Q: When is the database connection created?**
A: When you call `SessionLocal()` in `get_db()`

**Q: Do I need to manually close connections?**
A: No! The `finally` block in `get_db()` does it automatically

**Q: What happens if I don't call `commit()`?**
A: Changes are lost. They stay in the session but never reach the database.

**Q: Can I run multiple operations in one session?**
A: Yes! That's the point. Add, update, delete multiple records, then `commit()` once.

