# 🔐 JWT Authentication Implementation - Complete Guide

This document provides a comprehensive explanation of the JWT (JSON Web Token) authentication system implemented in this FastAPI + Next.js chatbot application.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [What is JWT?](#what-is-jwt)
3. [Files Added & Modified](#files-added--modified)
4. [Architecture Overview](#architecture-overview)
5. [Backend Implementation Deep Dive](#backend-implementation-deep-dive)
6. [Frontend Implementation Deep Dive](#frontend-implementation-deep-dive)
7. [Complete Authentication Flow](#complete-authentication-flow)
8. [Function-by-Function Breakdown](#function-by-function-breakdown)
9. [Database Schema](#database-schema)
10. [Security Considerations](#security-considerations)
11. [Testing Guide](#testing-guide)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### What Was Implemented?

A complete JWT-based authentication and authorization system with:

- ✅ **User Registration** - Create new accounts with email/password
- ✅ **User Login** - Authenticate and receive JWT token
- ✅ **Password Security** - Bcrypt hashing with salt
- ✅ **Token-Based Auth** - Stateless authentication using JWT
- ✅ **Role-Based Access** - User and Admin roles
- ✅ **Protected Routes** - Backend and frontend route protection
- ✅ **Token Validation** - Automatic token verification on requests
- ✅ **Auto-Logout** - On token expiration (30 minutes)
- ✅ **Global State** - React Context API for auth state
- ✅ **No Redux** - Simple state management
- ✅ **Local Storage** - Token persistence across sessions

### Key Characteristics

- **Stateless**: Server doesn't store session data
- **Access Token Only**: No refresh token (simpler, less secure)
- **30-Minute Expiration**: Automatic logout after inactivity
- **Role-Based**: User vs Admin access levels
- **Database-Backed**: PostgreSQL for user storage
- **Production-Ready**: Follows security best practices

---

## 🔑 What is JWT?

### JWT Structure

A JWT token consists of three parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEyMywiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIiwicm9sZSI6InVzZXIiLCJleHAiOjE3MDgyOTEyMDB9.signature_hash_here
```

**Part 1: Header** (Base64 encoded)
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```
- `alg`: Algorithm used for signing (HMAC SHA-256)
- `typ`: Token type (JWT)

**Part 2: Payload** (Base64 encoded)
```json
{
  "sub": 123,                    // Subject (user ID)
  "email": "user@example.com",
  "role": "user",
  "exp": 1708291200,            // Expiration timestamp
  "iat": 1708289400             // Issued at timestamp
}
```

**Part 3: Signature** (Cryptographic hash)
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  SECRET_KEY
)
```

### How JWT Works

1. **Server generates JWT** by encoding header + payload + signing with secret key
2. **Client stores JWT** in localStorage
3. **Client sends JWT** in Authorization header with each request
4. **Server verifies JWT** by checking signature and expiration
5. **Server extracts user info** from payload without database query

### Why JWT?

- ✅ **Stateless**: No server-side session storage needed
- ✅ **Scalable**: Easy to scale horizontally
- ✅ **Cross-Domain**: Works across different domains
- ✅ **Self-Contained**: Carries all user info in token
- ✅ **Fast**: No database lookup for every request

---

## 📁 Files Added & Modified

### Backend Files Created ✨

#### 1. **Core Authentication Files**

**`backend/requirements.txt`** - NEW
```
Dependencies added:
- python-jose[cryptography]==3.3.0  → JWT encoding/decoding
- passlib[bcrypt]==1.7.4           → Password hashing
- email-validator==2.3.0           → Email validation
- bcrypt==4.0.1                    → Bcrypt algorithm
```

**`backend/app/models/user.py`** - NEW
```
Purpose: User model for database
Defines: users table schema with email, password_hash, role, etc.
```

**`backend/app/schemas/auth.py`** - NEW
```
Purpose: Pydantic schemas for request/response validation
Defines: UserRegister, UserLogin, TokenResponse, UserMe
```

**`backend/app/services/auth_service.py`** - NEW
```
Purpose: Core authentication utilities
Functions:
  - hash_password()        → Hash password with bcrypt
  - verify_password()      → Verify password against hash
  - create_access_token()  → Generate JWT token
  - decode_access_token()  → Decode and validate JWT
```

**`backend/app/dependencies/auth.py`** - NEW
```
Purpose: FastAPI dependency injection for route protection
Functions:
  - get_current_user()       → Validate JWT and return User
  - get_current_admin_user() → Check admin role
```

**`backend/app/routers/auth.py`** - NEW
```
Purpose: Authentication API endpoints
Routes:
  - POST /auth/register  → Create new user account
  - POST /auth/login     → Authenticate and get token
  - GET /auth/me         → Get current user info
```

#### 2. **Configuration & Migration Files**

**`backend/migrations/008_add_users_table.sql`** - NEW
```sql
Purpose: Database migration for auth tables
Creates:
  - users table
  - user_id foreign key in chatbots table
  - user_id foreign key in chat_sessions table
  - Indexes for performance
```

**`backend/run_auth_migration.py`** - NEW
```python
Purpose: Script to run authentication migration
Usage: python run_auth_migration.py
```

**`backend/create_admin.py`** - NEW
```python
Purpose: Create first admin user
Creates: admin@example.com with admin123 password
```

**`backend/test_auth.py`** - NEW
```python
Purpose: Test authentication system
Tests: Registration, login, protected routes, invalid tokens
```

#### 3. **Modified Backend Files**

**`backend/app/config.py`** - MODIFIED
```python
Added:
  - SECRET_KEY configuration
  - ALGORITHM = "HS256"
  - ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

**`backend/app/main.py`** - MODIFIED
```python
Added:
  - Import auth router
  - Register auth router: app.include_router(auth.router)
```

**`backend/app/models/__init__.py`** - MODIFIED
```python
Added:
  - from .user import User
  - Export User in __all__
```

---

### Frontend Files Created ✨

#### 1. **State Management**

**`frontend/contexts/AuthContext.tsx`** - NEW
```typescript
Purpose: Global authentication state with Context API
Exports:
  - AuthProvider component  → Wraps entire app
  - useAuth() hook         → Access auth state anywhere

State:
  - isAuthenticated: boolean
  - user: User | null
  - token: string | null
  - role: string | null
  - loading: boolean

Methods:
  - login(email, password)    → Authenticate user
  - logout()                  → Clear auth state
  - register(userData)        → Create account

Features:
  - Auto-loads token from localStorage on mount
  - Validates token by calling /auth/me
  - Listens for 'auth:logout' events from API
  - Persists token across page refreshes
```

#### 2. **UI Components**

**`frontend/components/NavBar.tsx`** - NEW
```typescript
Purpose: Navigation bar with auth UI
Shows:
  - Login/Register links (if not authenticated)
  - Username + Logout button (if authenticated)
  - Admin badge (if role === 'admin')
```

**`frontend/components/withAuth.tsx`** - NEW
```typescript
Purpose: Higher-Order Component for route protection
Exports:
  - withAuth(Component, roles?)  → HOC wrapper
  - useProtectedRoute(roles?)    → Hook alternative

Features:
  - Auto-redirects to /login if not authenticated
  - Checks role-based authorization
  - Shows loading state during auth check
```

**`frontend/app/login/page.tsx`** - NEW
```typescript
Purpose: Login page UI
Features:
  - Email + password form
  - Error handling
  - Auto-redirect if already authenticated
  - Link to registration page
```

**`frontend/app/register/page.tsx`** - NEW
```typescript
Purpose: Registration page UI
Features:
  - Email, username, password, full_name fields
  - Password confirmation validation
  - Min 8 characters requirement
  - Auto-redirect if already authenticated
```

**`frontend/app/unauthorized/page.tsx`** - NEW
```typescript
Purpose: 403 error page
Shows: Access denied message when role check fails
```

#### 3. **Modified Frontend Files**

**`frontend/services/api.ts`** - MODIFIED
```typescript
Added:
  - Read token from localStorage
  - Attach Authorization header to all requests
  - Handle 401 responses → trigger logout
  - Fire 'auth:logout' event on token expiration

Before:
  headers: { "Content-Type": "application/json" }

After:
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`  // Added
  }
  
  // Added 401 handling:
  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.dispatchEvent(new Event('auth:logout'));
    throw new Error('Session expired');
  }
```

**`frontend/app/layout.tsx`** - MODIFIED
```typescript
Added:
  - Import AuthProvider
  - Wrap app in <AuthProvider>

Before:
  <body>{children}</body>

After:
  <body>
    <AuthProvider>
      {children}
    </AuthProvider>
  </body>
```

**`frontend/app/page.tsx`** - MODIFIED
```typescript
Added:
  - Import useAuth hook
  - Import NavBar component
  - Auth check with redirect to /login
  - Loading state during auth check
  - NavBar at top of page

Before:
  useEffect(() => { loadChatbots(); }, []);

After:
  const { isAuthenticated, loading } = useAuth();
  
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading]);
  
  useEffect(() => {
    if (isAuthenticated) { loadChatbots(); }
  }, [isAuthenticated]);
```

**`frontend/components/Dashboard/Layout.tsx`** - MODIFIED
```typescript
Added:
  - Auth protection
  - NavBar component
  - Auto-redirect to /login if not authenticated
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Browser (localhost:3000)                             │       │
│  │                                                        │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Pages:                                         │  │       │
│  │  │  - /login                                       │  │       │
│  │  │  - /register                                    │  │       │
│  │  │  - / (home - protected)                         │  │       │
│  │  │  - /dashboard/[id] (protected)                  │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  AuthContext (Global State)                    │  │       │
│  │  │  - isAuthenticated                             │  │       │
│  │  │  - user, role, token                           │  │       │
│  │  │  - login(), logout(), register()               │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  localStorage                                   │  │       │
│  │  │  Key: 'access_token'                           │  │       │
│  │  │  Value: JWT token string                       │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  API Client (services/api.ts)                  │  │       │
│  │  │  - Adds Authorization header                   │  │       │
│  │  │  - Handles 401 responses                       │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTP Requests with JWT
                    Authorization: Bearer <token>
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  FastAPI Server (127.0.0.1:8000)                      │       │
│  │                                                        │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Public Routes (No Auth)                        │  │       │
│  │  │  POST /auth/register                            │  │       │
│  │  │  POST /auth/login                               │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                                                        │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Protected Routes (Auth Required)               │  │       │
│  │  │  GET /auth/me                                   │  │       │
│  │  │  GET /chatbots                                  │  │       │
│  │  │  POST /chat/start                               │  │       │
│  │  │  ... (all other routes)                         │  │       │
│  │  │                                                  │  │       │
│  │  │  Dependency: get_current_user()                 │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Auth Dependencies                              │  │       │
│  │  │  (app/dependencies/auth.py)                     │  │       │
│  │  │                                                  │  │       │
│  │  │  get_current_user():                            │  │       │
│  │  │    1. Extract token from Authorization header   │  │       │
│  │  │    2. Decode JWT with SECRET_KEY                │  │       │
│  │  │    3. Verify signature & expiration             │  │       │
│  │  │    4. Query user from database                  │  │       │
│  │  │    5. Check is_active status                    │  │       │
│  │  │    6. Return User object                        │  │       │
│  │  │                                                  │  │       │
│  │  │  get_current_admin_user():                      │  │       │
│  │  │    1. Call get_current_user()                   │  │       │
│  │  │    2. Check if user.role == "admin"             │  │       │
│  │  │    3. Return User or raise 403                  │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Auth Service (app/services/auth_service.py)   │  │       │
│  │  │                                                  │  │       │
│  │  │  hash_password(password):                       │  │       │
│  │  │    → bcrypt.hash(password)                      │  │       │
│  │  │                                                  │  │       │
│  │  │  verify_password(plain, hashed):                │  │       │
│  │  │    → bcrypt.verify(plain, hashed)               │  │       │
│  │  │                                                  │  │       │
│  │  │  create_access_token(data):                     │  │       │
│  │  │    → jwt.encode(data, SECRET_KEY, HS256)        │  │       │
│  │  │                                                  │  │       │
│  │  │  decode_access_token(token):                    │  │       │
│  │  │    → jwt.decode(token, SECRET_KEY, HS256)       │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  │                          ↕                            │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │  Auth Router (app/routers/auth.py)             │  │       │
│  │  │                                                  │  │       │
│  │  │  POST /auth/register:                           │  │       │
│  │  │    1. Validate email/username unique            │  │       │
│  │  │    2. Hash password                             │  │       │
│  │  │    3. Create User in database                   │  │       │
│  │  │    4. Return user info                          │  │       │
│  │  │                                                  │  │       │
│  │  │  POST /auth/login:                              │  │       │
│  │  │    1. Find user by email                        │  │       │
│  │  │    2. Verify password                           │  │       │
│  │  │    3. Generate JWT token                        │  │       │
│  │  │    4. Return token + user info                  │  │       │
│  │  │                                                  │  │       │
│  │  │  GET /auth/me:                                  │  │       │
│  │  │    1. Dependency: get_current_user()            │  │       │
│  │  │    2. Return current user info                  │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  DATABASE (PostgreSQL)                           │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  users table:                                          │       │
│  │    - id (primary key)                                  │       │
│  │    - email (unique, indexed)                           │       │
│  │    - username (unique, indexed)                        │       │
│  │    - password_hash (bcrypt)                            │       │
│  │    - full_name                                         │       │
│  │    - role ('user' | 'admin')                           │       │
│  │    - is_active (boolean)                               │       │
│  │    - created_at (timestamp)                            │       │
│  │                                                          │       │
│  │  chatbots table:                                        │       │
│  │    - ... existing columns ...                           │       │
│  │    - user_id (foreign key → users.id) **NEW**          │       │
│  │                                                          │       │
│  │  chat_sessions table:                                   │       │
│  │    - ... existing columns ...                           │       │
│  │    - user_id (foreign key → users.id) **NEW**          │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Backend Implementation Deep Dive

### 1. User Model (`backend/app/models/user.py`)

**Purpose**: Defines the database schema for user accounts.

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base

class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Unique identifiers
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    
    # Security
    password_hash = Column(String(255), nullable=False)  # Bcrypt hash
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Authorization
    role = Column(String(50), nullable=False, default="user")  # "user" or "admin"
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Key Points**:
- `password_hash` stores bcrypt hash, **NEVER** plain password
- `email` and `username` are unique and indexed for fast lookups
- `role` determines authorization level
- `is_active` allows soft deletion (ban users without deleting)
- All timestamps use timezone-aware datetime

---

### 2. Auth Schemas (`backend/app/schemas/auth.py`)

**Purpose**: Pydantic models for request/response validation.

#### 2.1 UserRegister (Request Schema)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr                                    # Auto-validates email format
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
```

**Validation**:
- `EmailStr` → Validates email format (requires `email-validator` package)
- `min_length=3` → Username must be at least 3 characters
- `min_length=8` → Password must be at least 8 characters
- `Optional[str]` → full_name is not required

#### 2.2 UserLogin (Request Schema)

```python
class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
```

**Simple validation** - just email and password required.

#### 2.3 TokenResponse (Response Schema)

```python
class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str              # JWT token
    token_type: str = "bearer"     # Always "bearer"
    user: UserResponse             # User info
```

**Example Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "role": "user"
  }
}
```

#### 2.4 UserResponse (Response Schema)

```python
class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allows creating from SQLAlchemy models
```

**Security Note**: `password_hash` is **NOT** included in response schema.

---

### 3. Auth Service (`backend/app/services/auth_service.py`)

**Purpose**: Core cryptographic and JWT functions.

#### 3.1 Password Hashing

```python
from passlib.context import CryptContext

# Configure bcrypt with default rounds (12)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Process:
      1. Generate random salt (automatic)
      2. Hash password with salt
      3. Return hash (includes salt)
    
    Example:
      hash_password("mypassword123")
      → "$2b$12$abcdef...xyz"  (60 chars)
    """
    return pwd_context.hash(password)
```

**Bcrypt Details**:
- **Algorithm**: Bcrypt (based on Blowfish cipher)
- **Cost Factor**: 12 (2^12 = 4096 iterations)
- **Salt**: Automatically generated, embedded in hash
- **Output Format**: `$2b$12$<salt><hash>`
- **Length**: 60 characters
- **Time**: ~0.3 seconds per hash (intentionally slow)

#### 3.2 Password Verification

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Process:
      1. Extract salt from hashed_password
      2. Hash plain_password with same salt
      3. Compare hashes using constant-time comparison
    
    Returns:
      True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
```

**Security Features**:
- **Constant-time comparison**: Prevents timing attacks
- **Salt extracted from hash**: No need to store salt separately
- **Multiple rounds**: Protects against brute force

#### 3.3 JWT Token Creation

```python
from datetime import datetime, timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
      data: Dictionary of claims (user_id, email, role)
      expires_delta: Optional custom expiration time
    
    Returns:
      Encoded JWT token string
    
    Process:
      1. Copy input data
      2. Calculate expiration time (now + 30 minutes)
      3. Add 'exp' (expiration) and 'iat' (issued at) claims
      4. Encode with SECRET_KEY using HS256 algorithm
      5. Return token string
    """
    to_encode = data.copy()
    
    # Calculate expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add timestamps
    to_encode.update({
        "exp": expire,                    # Expiration time (Unix timestamp)
        "iat": datetime.utcnow()          # Issued at time (Unix timestamp)
    })
    
    # Encode JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

**Example Usage**:
```python
token = create_access_token(
    data={
        "sub": 123,                    # User ID
        "email": "user@example.com",
        "role": "user"
    }
)
# Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**JWT Claims**:
- `sub` (Subject): User ID (standard claim)
- `email`: User's email address
- `role`: User's role ("user" or "admin")
- `exp` (Expiration): Unix timestamp when token expires
- `iat` (Issued At): Unix timestamp when token was created

#### 3.4 JWT Token Decoding

```python
from jose import JWTError

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token.
    
    Args:
      token: JWT token string
    
    Returns:
      Decoded token payload if valid, None if invalid
    
    Process:
      1. Decode token with SECRET_KEY
      2. Verify signature matches
      3. Verify token not expired (exp claim)
      4. Return payload dictionary
    
    Raises:
      JWTError if token invalid, expired, or tampered
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None  # Invalid token
```

**Validation Checks** (automatic):
- ✅ Signature verification (prevents tampering)
- ✅ Expiration check (exp claim)
- ✅ Algorithm verification (prevents algorithm confusion attacks)

---

### 4. Auth Dependencies (`backend/app/dependencies/auth.py`)

**Purpose**: FastAPI dependency injection for route protection.

#### 4.1 get_current_user()

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

# Define security scheme (extracts token from Authorization header)
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    
    FastAPI will automatically:
      1. Extract Authorization header
      2. Parse "Bearer <token>" format
      3. Pass token to this function
      4. Inject database session
    
    Process:
      1. Extract token from credentials
      2. Decode JWT token
      3. Extract user_id from payload
      4. Query user from database
      5. Verify user exists and is active
      6. Return User object
    
    Raises:
      401 Unauthorized if token invalid, expired, or user not found
      403 Forbidden if user account is inactive
    """
    # Step 1: Extract token
    token = credentials.credentials
    
    # Step 2: Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3: Extract user_id from payload
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 4: Query user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 5: Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Step 6: Return User object
    return user
```

**Usage in Routes**:
```python
@router.get("/chatbots")
def get_chatbots(
    current_user: User = Depends(get_current_user),  # Auto-injected
    db: Session = Depends(get_db)
):
    # current_user is now available
    chatbots = db.query(Chatbot).filter(Chatbot.user_id == current_user.id).all()
    return chatbots
```

**What FastAPI Does Automatically**:
1. Checks `Authorization` header exists
2. Validates format: `Bearer <token>`
3. Extracts token
4. Calls `get_current_user()` with token
5. If exception raised → returns error response
6. If successful → injects User into route handler

#### 4.2 get_current_admin_user()

```python
def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current user and verify admin role.
    
    This is a "chained dependency":
      1. Calls get_current_user() first (gets user from token)
      2. Then checks if user.role == "admin"
      3. Raises 403 if not admin
    
    Raises:
      403 Forbidden if user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
```

**Usage in Routes**:
```python
@router.get("/admin/users")
def get_all_users(
    current_user: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    # Only admins can reach this code
    users = db.query(User).all()
    return users
```

---

### 5. Auth Router (`backend/app/routers/auth.py`)

**Purpose**: API endpoints for authentication.

#### 5.1 POST /auth/register

```python
@router.post("/register", response_model=UserMe, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Request Body (JSON):
      {
        "email": "user@example.com",
        "username": "johndoe",
        "password": "password123",
        "full_name": "John Doe"  // optional
      }
    
    Process:
      1. Validate request data (Pydantic automatic)
      2. Check email not already registered
      3. Check username not already taken
      4. Hash password with bcrypt
      5. Create User record in database
      6. Return user info (without password_hash)
    
    Returns:
      201 Created with user info
    
    Raises:
      400 Bad Request if email/username already exists
    """
    # Step 1: Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Step 2: Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Step 3: Hash password
    password_hash = hash_password(user_data.password)
    
    # Step 4: Create user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash,
        full_name=user_data.full_name,
        role="user"  # Default role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Reload to get auto-generated fields
    
    # Step 5: Return user info
    return db_user
```

**Example Request**:
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
```

**Example Response** (201 Created):
```json
{
  "id": 2,
  "email": "test@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "role": "user"
}
```

#### 5.2 POST /auth/login

```python
@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    Request Body (JSON):
      {
        "email": "user@example.com",
        "password": "password123"
      }
    
    Process:
      1. Find user by email
      2. Verify password matches hash
      3. Check user is active
      4. Generate JWT token with user claims
      5. Return token + user info
    
    Returns:
      200 OK with access_token and user info
    
    Raises:
      401 Unauthorized if email/password incorrect
      403 Forbidden if account inactive
    """
    # Step 1: Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Step 2: Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Step 3: Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Step 4: Create access token
    access_token = create_access_token(
        data={
            "sub": user.id,        # Subject (user ID)
            "email": user.email,
            "role": user.role
        }
    )
    
    # Step 5: Return token and user info
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )
```

**Example Request**:
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

**Example Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzA4MjkxMjAwLCJpYXQiOjE3MDgyODk0MDB9.signature",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "email": "test@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "role": "user",
    "is_active": true,
    "created_at": "2024-02-18T10:30:00Z"
  }
}
```

#### 5.3 GET /auth/me

```python
@router.get("/me", response_model=UserMe)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Headers Required:
      Authorization: Bearer <token>
    
    Process:
      1. FastAPI extracts token from header
      2. get_current_user() dependency validates token
      3. Returns validated User object
    
    Returns:
      200 OK with current user info
    
    Raises:
      401 Unauthorized if token invalid/expired
    """
    return current_user
```

**Example Request**:
```bash
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example Response** (200 OK):
```json
{
  "id": 2,
  "email": "test@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "role": "user"
}
```

---

## 🎨 Frontend Implementation Deep Dive

### 1. AuthContext (`frontend/contexts/AuthContext.tsx`)

**Purpose**: Global authentication state management using React Context API.

#### 1.1 Types Definition

```typescript
interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  role: string;
}

interface AuthContextType {
  isAuthenticated: boolean;        // Is user logged in?
  user: User | null;               // User object (null if not logged in)
  token: string | null;            // JWT token (null if not logged in)
  role: string | null;             // User role (null if not logged in)
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (userData: RegisterData) => Promise<void>;
  loading: boolean;                // Is auth state being initialized?
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
```

#### 1.2 Context Creation

```typescript
// Create context with undefined default
const AuthContext = createContext<AuthContextType | undefined>(undefined);
```

#### 1.3 AuthProvider Component

```typescript
export function AuthProvider({ children }: { children: ReactNode }) {
  // State variables
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
```

**State Variables Explained**:
- `isAuthenticated`: Boolean flag for quick auth checks
- `user`: Full user object with all profile data
- `token`: JWT token string (for API requests)
- `role`: User's role (for UI conditional rendering)
- `loading`: True during initial token validation

#### 1.4 Initialize Auth on Mount

```typescript
  useEffect(() => {
    const initializeAuth = async () => {
      // Step 1: Read token from localStorage
      const storedToken = localStorage.getItem('access_token');
      
      if (storedToken) {
        try {
          // Step 2: Validate token by calling backend
          const response = await fetch('http://127.0.0.1:8000/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });

          if (response.ok) {
            // Step 3: Token is valid, restore auth state
            const userData = await response.json();
            setUser(userData);
            setRole(userData.role);
            setToken(storedToken);
            setIsAuthenticated(true);
          } else {
            // Step 4: Token expired or invalid, clear it
            localStorage.removeItem('access_token');
          }
        } catch (error) {
          console.error('Failed to validate token:', error);
          localStorage.removeItem('access_token');
        }
      }
      
      // Step 5: Finished loading
      setLoading(false);
    };

    initializeAuth();
  }, []);
```

**Why This Matters**:
- ✅ Restores auth state on page refresh
- ✅ Validates token with backend (could be expired)
- ✅ Handles token expiration gracefully
- ✅ Prevents flash of login screen for authenticated users

#### 1.5 Listen for Logout Events

```typescript
  useEffect(() => {
    const handleLogoutEvent = () => {
      // Triggered by 401 responses from API client
      setIsAuthenticated(false);
      setUser(null);
      setRole(null);
      setToken(null);
    };

    window.addEventListener('auth:logout', handleLogoutEvent);
    return () => window.removeEventListener('auth:logout', handleLogoutEvent);
  }, []);
```

**How It Works**:
- API client fires `auth:logout` event on 401 response
- AuthContext listens and clears state
- User gets logged out across all components

#### 1.6 Login Method

```typescript
  const login = async (email: string, password: string) => {
    // Step 1: Call login API
    const response = await fetch('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Login failed');
    }

    // Step 2: Parse response
    const data: LoginResponse = await response.json();
    
    // Step 3: Store token in localStorage
    localStorage.setItem('access_token', data.access_token);
    
    // Step 4: Update state
    setToken(data.access_token);
    setUser(data.user);
    setRole(data.user.role);
    setIsAuthenticated(true);
  };
```

**Usage in Components**:
```typescript
const { login } = useAuth();

const handleSubmit = async (e) => {
  e.preventDefault();
  try {
    await login(email, password);
    router.push('/');  // Redirect on success
  } catch (error) {
    setError(error.message);
  }
};
```

#### 1.7 Logout Method

```typescript
  const logout = () => {
    // Step 1: Clear localStorage
    localStorage.removeItem('access_token');
    
    // Step 2: Clear state
    setIsAuthenticated(false);
    setUser(null);
    setRole(null);
    setToken(null);
  };
```

**Simple but Effective**:
- Clears token from localStorage
- Resets all auth state to null/false
- No backend call needed (JWT is stateless)

#### 1.8 Register Method

```typescript
  const register = async (userData: RegisterData) => {
    const response = await fetch('http://127.0.0.1:8000/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Registration failed');
    }

    // Registration successful - user must login manually
    // Not auto-logging in for security
  };
```

#### 1.9 Provide Context Value

```typescript
  const value: AuthContextType = {
    isAuthenticated,
    user,
    token,
    role,
    login,
    logout,
    register,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
```

#### 1.10 useAuth Hook

```typescript
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  
  return context;
}
```

**Usage**:
```typescript
// In any component:
const { isAuthenticated, user, role, login, logout } = useAuth();
```

---

### 2. API Client (`frontend/services/api.ts`)

**Purpose**: Centralized HTTP client with JWT support.

#### Before (No Auth):
```typescript
async function request<T>(path: string, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return await response.json();
}
```

#### After (With Auth):
```typescript
async function request<T>(path: string, options = {}) {
  const { method = "GET", body } = options;

  // Build headers
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // **NEW**: Add Authorization header if token exists
  const token = typeof window !== 'undefined' 
    ? localStorage.getItem('access_token') 
    : null;
    
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Make request
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // **NEW**: Handle token expiration
  if (response.status === 401) {
    // Token expired or invalid
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      window.dispatchEvent(new Event('auth:logout'));
    }
    throw new Error('Session expired. Please login again.');
  }

  // Handle other errors
  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  // Handle empty responses
  if (response.status === 204) {
    return undefined as T;
  }

  return await response.json() as T;
}
```

**Key Changes**:
1. ✅ Reads token from localStorage
2. ✅ Adds `Authorization: Bearer <token>` header automatically
3. ✅ Handles 401 responses by clearing token and triggering logout
4. ✅ Fires `auth:logout` event for AuthContext to catch
5. ✅ Works server-side (Next.js) with `typeof window` check

---

### 3. Protected Routes

#### 3.1 withAuth Higher-Order Component

```typescript
export function withAuth<P extends object>(
  Component: ComponentType<P>,
  allowedRoles?: string[]
) {
  return function ProtectedRoute(props: P) {
    const { isAuthenticated, role, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading) {
        // Redirect to login if not authenticated
        if (!isAuthenticated) {
          router.push('/login');
          return;
        }

        // Check role-based authorization
        if (allowedRoles && role && !allowedRoles.includes(role)) {
          router.push('/unauthorized');
        }
      }
    }, [isAuthenticated, role, loading, router]);

    // Show loading state
    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-lg">Loading...</div>
        </div>
      );
    }

    // Don't render if not authenticated
    if (!isAuthenticated) {
      return null;
    }

    // Don't render if role check fails
    if (allowedRoles && role && !allowedRoles.includes(role)) {
      return null;
    }

    // User is authenticated and authorized
    return <Component {...props} />;
  };
}
```

**Usage Examples**:
```typescript
// Protect for all authenticated users
export default withAuth(DashboardPage);

// Protect for admin only
export default withAuth(AdminPage, ['admin']);

// Protect for specific roles
export default withAuth(ModeratorPage, ['admin', 'moderator']);
```

#### 3.2 useProtectedRoute Hook (Alternative)

```typescript
export function useProtectedRoute(allowedRoles?: string[]) {
  const { isAuthenticated, role, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push('/login');
        return;
      }

      if (allowedRoles && role && !allowedRoles.includes(role)) {
        router.push('/unauthorized');
      }
    }
  }, [isAuthenticated, role, loading, allowedRoles, router]);

  return { isAuthenticated, role, loading };
}
```

**Usage**:
```typescript
function DashboardPage() {
  const { isAuthenticated, loading } = useProtectedRoute();
  
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return null;
  
  return <div>Dashboard content</div>;
}
```

---

## 🔄 Complete Authentication Flow

### Flow 1: Registration

```
┌──────────────┐
│  User visits │
│  /register   │
└──────┬───────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Register Page                        │
│ - User fills form (email, username, password)  │
│ - Validates password length (min 8 chars)      │
│ - Validates password confirmation matches      │
└──────┬─────────────────────────────────────────┘
       │
       │ POST /auth/register
       │ { email, username, password, full_name }
       ↓
┌────────────────────────────────────────────────┐
│ Backend: POST /auth/register                   │
│ 1. Pydantic validates request data             │
│ 2. Check email unique in database              │
│ 3. Check username unique in database           │
│ 4. Hash password with bcrypt                   │
│    password123 → $2b$12$abcd...xyz             │
│ 5. Create User record:                         │
│    - email, username, password_hash            │
│    - role = "user" (default)                   │
│    - is_active = true                          │
│ 6. Save to database                            │
│ 7. Return user info (without password_hash)    │
└──────┬─────────────────────────────────────────┘
       │
       │ 201 Created
       │ { id, email, username, role }
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Success                              │
│ - Show success message                         │
│ - Redirect to /login page                      │
│ - User must login manually                     │
└────────────────────────────────────────────────┘
```

### Flow 2: Login

```
┌──────────────┐
│  User visits │
│    /login    │
└──────┬───────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Login Page                           │
│ - User enters email and password               │
│ - Submits form                                 │
└──────┬─────────────────────────────────────────┘
       │
       │ POST /auth/login
       │ { email: "user@example.com", password: "password123" }
       ↓
┌────────────────────────────────────────────────┐
│ Backend: POST /auth/login                      │
│ 1. Find user by email in database              │
│ 2. Verify password:                            │
│    bcrypt.verify("password123", user.password_hash)
│    → True (password correct)                   │
│ 3. Check user.is_active = True                 │
│ 4. Generate JWT token:                         │
│    payload = {                                 │
│      "sub": user.id,                           │
│      "email": user.email,                      │
│      "role": user.role,                        │
│      "exp": now + 30 minutes,                  │
│      "iat": now                                │
│    }                                           │
│    token = jwt.encode(payload, SECRET_KEY, HS256)
│ 5. Return token + user info                    │
└──────┬─────────────────────────────────────────┘
       │
       │ 200 OK
       │ {
       │   "access_token": "eyJhbGci...",
       │   "token_type": "bearer",
       │   "user": { id, email, username, role }
       │ }
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: AuthContext.login()                  │
│ 1. Receive token and user info                 │
│ 2. Store token in localStorage:                │
│    localStorage.setItem('access_token', token) │
│ 3. Update state:                               │
│    - setToken(token)                           │
│    - setUser(user)                             │
│    - setRole(user.role)                        │
│    - setIsAuthenticated(true)                  │
│ 4. Redirect to home page (/)                   │
└────────────────────────────────────────────────┘
```

### Flow 3: Authenticated Request

```
┌──────────────┐
│ User clicks  │
│ "Get Chatbots"│
└──────┬───────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: services/api.ts                      │
│ 1. Read token from localStorage                │
│    token = localStorage.getItem('access_token')│
│ 2. Build request with Authorization header:    │
│    headers = {                                 │
│      "Content-Type": "application/json",       │
│      "Authorization": "Bearer eyJhbGci..."     │
│    }                                           │
│ 3. Send GET request to /chatbots               │
└──────┬─────────────────────────────────────────┘
       │
       │ GET /chatbots
       │ Authorization: Bearer eyJhbGci...
       ↓
┌────────────────────────────────────────────────┐
│ Backend: FastAPI Middleware                    │
│ 1. FastAPI extracts Authorization header       │
│ 2. Parses "Bearer <token>" format              │
│ 3. Calls get_current_user() dependency         │
└──────┬─────────────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Backend: get_current_user() Dependency         │
│ 1. Extract token from header                   │
│ 2. Decode JWT:                                 │
│    payload = jwt.decode(token, SECRET_KEY, HS256)
│ 3. Verify signature matches                    │
│ 4. Check expiration (exp claim)                │
│    if expired → raise 401 Unauthorized         │
│ 5. Extract user_id from payload.sub            │
│ 6. Query user from database:                   │
│    user = db.query(User).filter(id == user_id).first()
│ 7. Check user exists                           │
│ 8. Check user.is_active = True                 │
│ 9. Return User object                          │
└──────┬─────────────────────────────────────────┘
       │
       │ User object injected into route handler
       ↓
┌────────────────────────────────────────────────┐
│ Backend: GET /chatbots Route Handler           │
│ def get_chatbots(                              │
│     current_user: User = Depends(get_current_user),
│     db: Session = Depends(get_db)              │
│ ):                                             │
│     # current_user is authenticated User       │
│     chatbots = db.query(Chatbot)               │
│                  .filter(user_id == current_user.id)
│                  .all()                         │
│     return chatbots                            │
└──────┬─────────────────────────────────────────┘
       │
       │ 200 OK
       │ [ { id: 1, name: "Bot 1" }, ... ]
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Receive Response                     │
│ - Update UI with chatbots list                 │
└────────────────────────────────────────────────┘
```

### Flow 4: Token Expiration

```
┌──────────────┐
│ User logged  │
│ in 30 mins   │
│ ago          │
└──────┬───────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: User makes API request               │
│ - Token is still in localStorage               │
│ - Request sent with expired token              │
└──────┬─────────────────────────────────────────┘
       │
       │ GET /chatbots
       │ Authorization: Bearer <expired_token>
       ↓
┌────────────────────────────────────────────────┐
│ Backend: get_current_user() Dependency         │
│ 1. Extract token                               │
│ 2. Decode JWT:                                 │
│    payload = jwt.decode(token, SECRET_KEY)     │
│ 3. Check expiration:                           │
│    now = 1708291300                            │
│    exp = 1708291200                            │
│    now > exp → Token expired!                  │
│ 4. Raise JWTError (ExpiredSignatureError)      │
│ 5. FastAPI converts to 401 Unauthorized        │
└──────┬─────────────────────────────────────────┘
       │
       │ 401 Unauthorized
       │ { "detail": "Invalid or expired token" }
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: services/api.ts (401 Handler)        │
│ 1. Detect response.status === 401              │
│ 2. Clear token:                                │
│    localStorage.removeItem('access_token')     │
│ 3. Fire logout event:                          │
│    window.dispatchEvent(new Event('auth:logout'))
│ 4. Throw error with user message               │
└──────┬─────────────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: AuthContext (Event Listener)         │
│ 1. Catches 'auth:logout' event                 │
│ 2. Clears state:                               │
│    - setIsAuthenticated(false)                 │
│    - setUser(null)                             │
│    - setRole(null)                             │
│    - setToken(null)                            │
└──────┬─────────────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Page Component Re-renders            │
│ - isAuthenticated is now false                 │
│ - useEffect detects change                     │
│ - Redirects to /login                          │
│ - Shows "Session expired, please login again"  │
└────────────────────────────────────────────────┘
```

### Flow 5: Logout

```
┌──────────────┐
│ User clicks  │
│ "Logout"     │
│ button       │
└──────┬───────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: NavBar Component                     │
│ const { logout } = useAuth();                  │
│ const handleLogout = () => {                   │
│   logout();                                    │
│   router.push('/login');                       │
│ };                                             │
└──────┬─────────────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: AuthContext.logout()                 │
│ 1. Clear localStorage:                         │
│    localStorage.removeItem('access_token')     │
│ 2. Clear state:                                │
│    - setIsAuthenticated(false)                 │
│    - setUser(null)                             │
│    - setRole(null)                             │
│    - setToken(null)                            │
│ 3. No backend call needed (JWT is stateless)   │
└──────┬─────────────────────────────────────────┘
       │
       ↓
┌────────────────────────────────────────────────┐
│ Frontend: Redirect to /login                   │
│ - All components re-render                     │
│ - Protected routes redirect to login           │
│ - NavBar shows Login/Register links            │
└────────────────────────────────────────────────┘
```

---

## 📖 Function-by-Function Breakdown

### Backend Functions

#### auth_service.py

| Function | Purpose | Input | Output | Notes |
|----------|---------|-------|--------|-------|
| `hash_password()` | Hash password with bcrypt | `password: str` | `str` (60 chars) | Cost factor: 12, includes salt |
| `verify_password()` | Check password against hash | `plain: str, hashed: str` | `bool` | Constant-time comparison |
| `create_access_token()` | Generate JWT token | `data: dict, expires_delta: Optional[timedelta]` | `str` | Default 30 min expiration |
| `decode_access_token()` | Decode & validate JWT | `token: str` | `Optional[dict]` | Returns None if invalid |

#### auth.py (dependencies)

| Function | Purpose | Input | Output | Raises |
|----------|---------|-------|--------|--------|
| `get_current_user()` | Extract & validate user from token | `credentials, db` | `User` | 401 if invalid, 403 if inactive |
| `get_current_admin_user()` | Verify admin role | `current_user` | `User` | 403 if not admin |

#### auth.py (routes)

| Endpoint | Method | Purpose | Auth Required | Input | Output |
|----------|--------|---------|---------------|-------|--------|
| `/auth/register` | POST | Create new account | No | `UserRegister` | `UserMe` (201) |
| `/auth/login` | POST | Authenticate user | No | `UserLogin` | `TokenResponse` (200) |
| `/auth/me` | GET | Get current user | Yes | - | `UserMe` (200) |

### Frontend Functions

#### AuthContext.tsx

| Function | Purpose | Input | Output | Notes |
|----------|---------|-------|--------|-------|
| `login()` | Authenticate user | `email: string, password: string` | `Promise<void>` | Stores token, updates state |
| `logout()` | Clear auth state | - | `void` | Clears localStorage |
| `register()` | Create account | `userData: RegisterData` | `Promise<void>` | Does not auto-login |
| `useAuth()` | Access auth context | - | `AuthContextType` | Custom hook |

#### withAuth.tsx

| Function | Purpose | Input | Output | Notes |
|----------|---------|-------|--------|-------|
| `withAuth()` | HOC for route protection | `Component, allowedRoles?` | `Component` | Auto-redirects |
| `useProtectedRoute()` | Hook for route protection | `allowedRoles?` | `{ isAuthenticated, role, loading }` | Alternative to HOC |

#### api.ts

| Function | Purpose | Changes Made | Notes |
|----------|---------|--------------|-------|
| `request()` | HTTP client | Added Authorization header, 401 handling | Reads token from localStorage |

---

## 🗄️ Database Schema

### users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

**Columns Explained**:
- `id`: Auto-incrementing primary key
- `email`: Unique email (used for login)
- `username`: Unique display name
- `password_hash`: Bcrypt hash (60 chars, starts with `$2b$12$`)
- `full_name`: Optional full name
- `role`: `"user"` or `"admin"` (extendable)
- `is_active`: Soft delete flag (ban without deleting)
- `created_at`: Account creation timestamp

### Modified Tables

#### chatbots Table
```sql
ALTER TABLE chatbots 
ADD COLUMN user_id INTEGER REFERENCES users(id);

CREATE INDEX idx_chatbots_user_id ON chatbots(user_id);
```

**Purpose**: Track chatbot ownership

#### chat_sessions Table
```sql
ALTER TABLE chat_sessions 
ADD COLUMN user_id INTEGER REFERENCES users(id);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
```

**Purpose**: Track which user owns each chat session

---

## 🔒 Security Considerations

### 1. Password Security

**✅ What We Do Right**:
- Bcrypt hashing with salt (automatic)
- Cost factor 12 (4096 iterations)
- One-way encryption (irreversible)
- Constant-time password verification
- Never store plain text passwords
- Never return password_hash in API responses

**⚠️ Additional Recommendations**:
- Enforce password complexity (uppercase, lowercase, numbers, symbols)
- Implement password strength meter in UI
- Add password history (prevent reusing old passwords)
- Implement account lockout after failed login attempts
- Add CAPTCHA after 3 failed attempts

### 2. JWT Security

**✅ What We Do Right**:
- Short expiration (30 minutes)
- Signature verification on every request
- Algorithm pinning (only HS256 accepted)
- Validate token on every protected route
- Check user still exists and is active

**⚠️ Limitations & Mitigations**:

| Issue | Risk | Mitigation |
|-------|------|------------|
| Token in localStorage | Vulnerable to XSS | Sanitize all user inputs, use CSP headers |
| No token revocation | Cannot logout before expiration | Implement token blacklist in Redis |
| No refresh token | Poor UX (re-login every 30 min) | Add refresh token (future enhancement) |
| Single secret key | Key compromise = all tokens invalid | Rotate keys periodically |

### 3. HTTPS Requirement

**⚠️ CRITICAL**: Always use HTTPS in production!

**Why?**:
- Tokens sent in plain text over HTTP
- Man-in-the-middle attacks can steal tokens
- Passwords sent in plain text during login

**How to Enable**:
- Use reverse proxy (Nginx, Apache)
- Get SSL certificate (Let's Encrypt)
- Redirect HTTP to HTTPS
- Set Secure flag on cookies (if using cookies)

### 4. CORS Security

**Current Configuration**:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

**Production Configuration**:
```python
CORS_ALLOWED_ORIGINS = [
    "https://yourapp.com",
    "https://www.yourapp.com"
]
```

**Never use** `allow_origins=["*"]` in production!

### 5. Input Validation

**✅ Where We Validate**:
- Pydantic schemas validate request data
- Email format validation (email-validator)
- Password length (min 8 chars)
- Username length (min 3 chars)

**⚠️ Add Validation For**:
- SQL injection (SQLAlchemy protects, but verify)
- XSS attacks (sanitize HTML input)
- CSRF attacks (not applicable to JWT, but consider for cookies)

### 6. Rate Limiting

**⚠️ Not Implemented** - Add for production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
def login(...):
    ...
```

---

## 🧪 Testing Guide

### Backend Testing

#### 1. Test with cURL

**Register**:
```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
```

**Login**:
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

**Get Current User**:
```bash
# Save token from login response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

#### 2. Test with Python Script

Run the included test script:
```bash
cd backend
python test_auth.py
```

**Tests**:
- ✅ User registration
- ✅ User login
- ✅ Token validation (GET /auth/me)
- ✅ Invalid token rejection

#### 3. Test in API Documentation

Visit: http://127.0.0.1:8000/docs

1. Click "Authorize" button (top right)
2. No auth needed for register/login
3. After login, paste token in "Authorize" dialog
4. Test protected endpoints

### Frontend Testing

#### 1. Manual Testing Flow

**Registration**:
1. Visit http://localhost:3000/register
2. Fill form with valid data
3. Submit
4. Check redirect to /login
5. Check success message

**Login**:
1. Visit http://localhost:3000/login
2. Enter credentials
3. Submit
4. Check redirect to /
5. Check NavBar shows username
6. Check localStorage has token

**Protected Routes**:
1. While logged in, visit /
2. Create a chatbot
3. Open dashboard
4. Verify no 401 errors

**Token Expiration**:
1. Login
2. Wait 30 minutes (or modify token expiration to 1 minute for testing)
3. Make any API request
4. Should auto-logout and redirect to /login

**Logout**:
1. Click "Logout" in NavBar
2. Check redirect to /login
3. Check localStorage token removed
4. Try accessing / → should redirect to /login

#### 2. Browser DevTools

**Check localStorage**:
```javascript
// Open Console (F12)
localStorage.getItem('access_token')
```

**Check decoded token**:
```javascript
// Paste token (without "Bearer ")
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const payload = JSON.parse(atob(token.split('.')[1]));
console.log(payload);
```

**Force logout**:
```javascript
localStorage.removeItem('access_token');
window.location.reload();
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "Module 'jose' not found"

**Cause**: Missing python-jose dependency

**Fix**:
```bash
cd backend
pip install python-jose[cryptography]
```

#### 2. "Module 'email_validator' not found"

**Cause**: Missing email-validator dependency

**Fix**:
```bash
pip install email-validator
```

#### 3. "bcrypt version error" or "password too long"

**Cause**: Incompatible bcrypt version

**Fix**:
```bash
pip install --force-reinstall bcrypt==4.0.1
```

#### 4. 401 Unauthorized on every request

**Possible Causes**:

**a) Token not being sent**:
- Check localStorage has 'access_token'
- Check api.ts is reading from localStorage
- Check Authorization header is present (DevTools Network tab)

**b) SECRET_KEY mismatch**:
- Ensure SECRET_KEY in .env matches between environments
- Regenerate token after changing SECRET_KEY

**c) Token expired**:
- Check token exp claim
- Default is 30 minutes
- Login again to get fresh token

**d) Algorithm mismatch**:
- Ensure ALGORITHM = "HS256" in config
- Ensure jwt.decode(algorithms=["HS256"])

#### 5. CORS errors

**Cause**: Frontend domain not allowed

**Fix** in backend/app/config.py:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Add your frontend URL
]
```

#### 6. Database migration fails

**Cause**: Tables already exist or schema conflict

**Fix**:
```bash
# Check if users table exists
psql -U postgres -d chatbot_db -c "\dt users"

# If exists, skip migration
# If not, run migration again
python run_auth_migration.py
```

#### 7. "User not found" after login

**Cause**: Token has user_id that doesn't exist in database

**Possible Reasons**:
- Database was reset but old token still in localStorage
- User was deleted but token still valid

**Fix**:
```javascript
// Clear token in browser
localStorage.removeItem('access_token');
// Login again
```

#### 8. Infinite redirect loop (login → / → login → ...)

**Cause**: Auth check logic issue

**Debug**:
```typescript
// In protected component
const { isAuthenticated, loading } = useAuth();

console.log('isAuthenticated:', isAuthenticated);
console.log('loading:', loading);
console.log('token:', localStorage.getItem('access_token'));
```

**Common Fix**:
- Check loading state is properly set to false after init
- Ensure token validation in AuthContext completes
- Check /auth/me endpoint is accessible

---

## 📚 Additional Resources

### Documentation Links

- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **JWT.io**: https://jwt.io/ (Decode and inspect tokens)
- **Passlib**: https://passlib.readthedocs.io/
- **Python-JOSE**: https://python-jose.readthedocs.io/
- **Next.js Authentication**: https://nextjs.org/docs/authentication
- **React Context API**: https://react.dev/reference/react/useContext

### Security Best Practices

- **OWASP Authentication Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- **JWT Best Practices**: https://tools.ietf.org/html/rfc8725
- **Password Storage Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

---

## 🎯 Summary

### What You Now Have

✅ **Secure Authentication System**
- Bcrypt password hashing
- JWT token generation and validation
- 30-minute token expiration
- Automatic logout on expiration

✅ **Role-Based Authorization**
- User and Admin roles
- Backend route protection
- Frontend conditional rendering
- Scalable role system

✅ **Seamless User Experience**
- Persistent login across page refreshes
- Auto-redirect on authentication state changes
- Clear error messages
- Loading states

✅ **Production-Ready Security**
- Stateless authentication (scalable)
- Secure password storage
- Token signature verification
- Active user checks

✅ **Developer-Friendly**
- Type-safe with TypeScript
- Dependency injection in FastAPI
- Global state management
- Reusable components

### Next Steps for Production

1. **Generate secure SECRET_KEY**:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **Enable HTTPS**:
   - Get SSL certificate
   - Configure reverse proxy
   - Update CORS settings

3. **Add refresh tokens** (optional):
   - Longer-lived tokens for better UX
   - Separate endpoint for token refresh

4. **Implement rate limiting**:
   - Protect against brute force attacks
   - Limit login attempts

5. **Add logging and monitoring**:
   - Log failed login attempts
   - Monitor token usage
   - Alert on suspicious activity

6. **Password reset flow**:
   - Email verification
   - Reset token generation
   - Password reset page

---

## 📞 Support

For issues or questions about this implementation:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [Testing Guide](#testing-guide)
3. Inspect browser DevTools and server logs
4. Test with cURL to isolate frontend/backend issues

---

**End of JWT Implementation Guide**

*Last Updated: February 19, 2026*
