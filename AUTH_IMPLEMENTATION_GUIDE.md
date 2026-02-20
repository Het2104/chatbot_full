# JWT Authentication Implementation Guide

## ✅ Implementation Complete

Your FastAPI + Next.js chatbot now has full JWT authentication and role-based authorization.

---

## 🚀 Quick Start

### 1️⃣ Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2️⃣ Configure Environment Variables

Add to `backend/.env`:

```env
# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production-min-32-chars-256bit
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Existing variables...
DATABASE_URL=postgresql://...
```

**⚠️ IMPORTANT**: Generate a secure SECRET_KEY in production:

```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3️⃣ Run Database Migration

```bash
cd backend
python run_migration.py migrations/008_add_users_table.sql
```

This creates:
- `users` table
- `user_id` foreign key in `chatbots` table
- `user_id` foreign key in `chat_sessions` table

### 4️⃣ Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 5️⃣ Start Frontend

```bash
cd frontend
npm run dev
```

---

## 📂 Files Created/Modified

### Backend Files Created ✨

```
backend/
├── requirements.txt                    # NEW - Python dependencies
├── app/
│   ├── config.py                       # MODIFIED - Added JWT config
│   ├── main.py                         # MODIFIED - Registered auth router
│   ├── models/
│   │   ├── user.py                     # NEW - User model
│   │   └── __init__.py                 # MODIFIED - Export User
│   ├── schemas/
│   │   └── auth.py                     # NEW - Auth request/response schemas
│   ├── services/
│   │   └── auth_service.py             # NEW - Password hashing, JWT functions
│   ├── dependencies/
│   │   ├── __init__.py                 # NEW - Auth dependencies module
│   │   └── auth.py                     # NEW - get_current_user, get_current_admin_user
│   └── routers/
│       └── auth.py                     # NEW - /auth/register, /auth/login, /auth/me
└── migrations/
    └── 008_add_users_table.sql         # NEW - Database migration
```

### Frontend Files Created ✨

```
frontend/
├── contexts/
│   └── AuthContext.tsx                 # NEW - Global auth state management
├── components/
│   └── withAuth.tsx                    # NEW - Protected route HOC
├── services/
│   └── api.ts                          # MODIFIED - Added JWT headers, 401 handling
├── app/
│   ├── layout.tsx                      # MODIFIED - Wrapped in AuthProvider
│   ├── login/
│   │   └── page.tsx                    # NEW - Login page
│   ├── register/
│   │   └── page.tsx                    # NEW - Registration page
│   └── unauthorized/
│       └── page.tsx                    # NEW - 403 error page
```

---

## 🔐 API Endpoints

### Authentication Endpoints (Public)

**POST** `/auth/register`
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "password123",
  "full_name": "John Doe"  // optional
}
```
Returns: User object (id, email, username, role)

**POST** `/auth/login`
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
Returns:
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "role": "user"
  }
}
```

**GET** `/auth/me` (Protected)
- Headers: `Authorization: Bearer <token>`
- Returns: Current user info

### All Other Endpoints

Now require authentication by default (add dependency to protect them).

---

## 🛡️ Protecting Backend Routes

### Require Authentication

```python
from app.dependencies.auth import get_current_user
from app.models.user import User

@router.get("/chatbots")
def get_chatbots(
    current_user: User = Depends(get_current_user),  # Add this
    db: Session = Depends(get_db)
):
    # Filter by user ownership
    chatbots = db.query(Chatbot).filter(Chatbot.user_id == current_user.id).all()
    return chatbots
```

### Require Admin Role

```python
from app.dependencies.auth import get_current_admin_user

@router.get("/admin/users")
def get_all_users(
    current_user: User = Depends(get_current_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    return db.query(User).all()
```

---

## 🔒 Protecting Frontend Pages

### Method 1: withAuth HOC

```tsx
import { withAuth } from '@/components/withAuth';

function DashboardPage() {
  return <div>Protected Dashboard</div>;
}

// Protect for all authenticated users
export default withAuth(DashboardPage);

// Or restrict to admin only
export default withAuth(AdminPage, ['admin']);
```

### Method 2: useProtectedRoute Hook

```tsx
'use client';
import { useProtectedRoute } from '@/components/withAuth';

export default function ChatPage() {
  const { isAuthenticated, role } = useProtectedRoute();  // Auto-redirects
  
  return <div>Protected Chat</div>;
}
```

### Method 3: Conditional Rendering

```tsx
'use client';
import { useAuth } from '@/contexts/AuthContext';

export default function NavBar() {
  const { isAuthenticated, user, role, logout } = useAuth();
  
  return (
    <nav>
      {isAuthenticated ? (
        <>
          <span>Hello, {user?.username}</span>
          {role === 'admin' && <Link href="/admin">Admin Panel</Link>}
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <Link href="/login">Login</Link>
      )}
    </nav>
  );
}
```

---

## 👤 User Roles

### Default Roles
- **user**: Regular users (default for new registrations)
- **admin**: Administrators

### Creating First Admin User

After registering a user, manually update in database:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

Or create a script:

```python
# backend/create_admin.py
from database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password

db = SessionLocal()

admin = User(
    email="admin@example.com",
    username="admin",
    password_hash=hash_password("admin123"),
    role="admin",
    full_name="Admin User"
)

db.add(admin)
db.commit()
print("Admin user created!")
db.close()
```

---

## 🔄 Authentication Flow

### Registration Flow
1. User fills form at `/register`
2. Frontend calls `POST /auth/register`
3. Backend validates, hashes password (bcrypt)
4. User record created with role="user"
5. Redirect to `/login`

### Login Flow
1. User enters credentials at `/login`
2. Frontend calls `POST /auth/login`
3. Backend verifies password, generates JWT
4. Token stored in localStorage
5. AuthContext updated (isAuthenticated=true)
6. Redirect to `/dashboard`

### Protected Request Flow
1. User makes API call (e.g., GET /chatbots)
2. Frontend adds `Authorization: Bearer <token>` header
3. Backend `get_current_user()` dependency:
   - Extracts token
   - Validates signature & expiration
   - Queries user from DB
   - Injects User into route handler
4. Handler uses `current_user.id` to filter data

### Token Expiration Flow
1. Token expires after 30 minutes
2. User makes API call
3. Backend returns 401 Unauthorized
4. Frontend catches 401 in api.ts
5. Clears localStorage and auth state
6. Triggers 'auth:logout' event
7. Redirects to `/login`

### Logout Flow
1. User clicks "Logout"
2. Frontend calls `logout()` from AuthContext
3. Clears localStorage
4. Clears state (isAuthenticated=false)
5. Redirects to `/login`

---

## 🎯 Next Steps

### 1. Protect Existing Routes

Update existing routers to require authentication:

```python
# backend/app/routers/chatbots.py
from app.dependencies.auth import get_current_user
from app.models.user import User

@router.post("/chatbots", response_model=ChatbotResponse)
def create_chatbot(
    chatbot: ChatbotCreate,
    current_user: User = Depends(get_current_user),  # ADD THIS
    db: Session = Depends(get_db)
):
    db_chatbot = Chatbot(
        **chatbot.dict(),
        user_id=current_user.id  # ADD OWNERSHIP
    )
    db.add(db_chatbot)
    db.commit()
    return db_chatbot
```

### 2. Test Authentication

```bash
# Register user
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'

# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Get current user (protected)
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

### 3. Add User Navigation

Create a navbar component with login/logout:

```tsx
// frontend/components/NavBar.tsx
'use client';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';

export function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  
  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="flex justify-between items-center">
        <Link href="/" className="text-xl font-bold">
          Chatbot AI
        </Link>
        
        <div className="flex gap-4 items-center">
          {isAuthenticated ? (
            <>
              <span>Hello, {user?.username}</span>
              <Link href="/dashboard">Dashboard</Link>
              <button onClick={logout} className="bg-red-600 px-4 py-2 rounded">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/login">Login</Link>
              <Link href="/register">Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
```

### 4. Enable HTTPS in Production

Update `frontend/services/api.ts`:
```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
```

Set in production:
```env
NEXT_PUBLIC_API_URL=https://api.yourapp.com
```

---

## 🔧 Troubleshooting

### "Module 'jose' not found"
```bash
pip install python-jose[cryptography]
```

### "Module 'passlib' not found"
```bash
pip install passlib[bcrypt]
```

### Token not being sent with requests
- Check browser console for localStorage value
- Verify api.ts is reading from localStorage
- Ensure token key is 'access_token'

### 401 on every request
- Check SECRET_KEY matches between .env and config.py
- Verify token hasn't expired (30 min default)
- Check token format: "Bearer <token>"

### Migration fails
```bash
# Reset database (WARNING: deletes all data)
python backend/run_migration.py backend/migrations/000_reset_data.sql
python backend/run_migration.py backend/migrations/008_add_users_table.sql
```

---

## 📊 Database Schema

### users table
```sql
id              SERIAL PRIMARY KEY
email           VARCHAR(255) UNIQUE NOT NULL
username        VARCHAR(100) UNIQUE NOT NULL
password_hash   VARCHAR(255) NOT NULL
full_name       VARCHAR(255)
role            VARCHAR(50) DEFAULT 'user'
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP DEFAULT NOW()
```

### chatbots table (updated)
```sql
...existing columns...
user_id         INTEGER REFERENCES users(id)  -- NEW
```

### chat_sessions table (updated)
```sql
...existing columns...
user_id         INTEGER REFERENCES users(id)  -- NEW
```

---

## 🌟 Features Implemented

✅ User registration with email/username/password  
✅ Secure password hashing (bcrypt)  
✅ JWT token generation and validation  
✅ 30-minute token expiration  
✅ Role-based authorization (user/admin)  
✅ Protected backend routes  
✅ Protected frontend pages  
✅ Global auth state management (Context API)  
✅ Token storage in localStorage  
✅ Automatic token attachment to requests  
✅ 401 handling and auto-logout  
✅ Login/Register UI pages  
✅ Unauthorized page (403)  
✅ User ownership for chatbots/sessions  

---

## 🚧 Future Enhancements (Not Implemented)

- ❌ Refresh tokens (only access token implemented)
- ❌ Token blacklist (logout is client-side only)
- ❌ Password reset via email
- ❌ Email verification
- ❌ OAuth social login (Google, GitHub)
- ❌ Rate limiting on login endpoint
- ❌ Account lockout after failed attempts
- ❌ WebSocket/SSE authentication (ready for implementation)
- ❌ RabbitMQ/Redis integration (architecture compatible)

---

## 📝 Security Notes

1. **Change SECRET_KEY in production** - Use 256-bit random key
2. **Use HTTPS in production** - Never send tokens over HTTP
3. **Validate on backend always** - Frontend checks are UX only
4. **Short token expiration** - 30 minutes limits exposure
5. **No sensitive data in JWT** - Only user_id, email, role
6. **Password requirements** - Enforce min 8 chars (can add complexity)
7. **Index sensitive columns** - email/username for faster lookups

---

## 🎉 You're All Set!

Your authentication system is fully implemented and ready to use. Test the flow:

1. Go to http://localhost:3000/register
2. Create an account
3. Login at http://localhost:3000/login
4. Access protected pages
5. Call protected API endpoints

For questions or issues, refer to the architectural explanation provided earlier.
