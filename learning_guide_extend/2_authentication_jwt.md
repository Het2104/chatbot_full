# 2. JWT Authentication — Deep Technical Learning

---

## 2.1 Concept Introduction

**JWT (JSON Web Token)** is an open standard (RFC 7519) for securely transmitting information between parties as a JSON object. The information is digitally signed, so it can be verified and trusted.

JWT is **stateless** — the server does not store session data in a database. All identity information lives inside the token itself. The server only needs its secret key to verify any token.

**Compare with session-based auth:**

```
Session-Based (Stateful):
  Login → Server creates session → Stores in DB → Returns session_id cookie
  Request → Server looks up session_id in DB → Validates → Serves request
  Problem: Every request hits the database even for auth check

JWT-Based (Stateless):
  Login → Server creates JWT → Signs with secret → Returns token to client
  Request → Server reads JWT → Verifies signature → No DB lookup needed
  Benefit: Auth check is CPU-only (cryptographic verification), not I/O
```

---

## 2.2 Why JWT is Used in This Project

In a distributed system, multiple services (API server, worker, future microservices) need to verify user identity. With session-based auth, every service would need access to the session database. With JWT, any service that has the `SECRET_KEY` can independently verify the token.

**Specific reasons in this system:**

1. **Stateless scaling** — when you run multiple FastAPI instances behind a load balancer, no shared session store is needed. Each instance independently verifies the JWT.
2. **Performance** — no database query on every authenticated request
3. **Simplicity** — frontend just sends `Authorization: Bearer <token>` header
4. **Standard** — every language and framework has JWT libraries

---

## 2.3 JWT Structure — Internal Anatomy

A JWT consists of exactly three parts separated by dots (`.`):

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNjk5OTk5OTk5fQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
└─────────────────────────┘ └──────────────────────────────────────────┘ └──────────────────────────────────────┘
         Header                              Payload                                  Signature
    (Base64URL encoded)               (Base64URL encoded)                      (HMAC-SHA256 hash)
```

### Part 1: Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg`: The signing algorithm. Your project uses `HS256` (HMAC with SHA-256).
- `typ`: Always "JWT"

### Part 2: Payload (Claims)

```json
{
  "sub": "user123",
  "exp": 1699999999,
  "iat": 1699996399
}
```

Standard claims used in your `auth_service.py`:

| Claim | Name | Meaning |
|---|---|---|
| `sub` | Subject | The user identifier (username or user ID) |
| `exp` | Expiration | Unix timestamp when token expires |
| `iat` | Issued At | Unix timestamp when token was created |

Your `create_access_token()` function in `services/auth_service.py` sets these automatically:

```python
to_encode.update({
    "exp": expire,
    "iat": datetime.utcnow()
})
encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Part 3: Signature

The signature is computed as:

```
HMAC-SHA256(
    base64url(header) + "." + base64url(payload),
    SECRET_KEY
)
```

**The critical property:** If anyone modifies the payload (e.g., changes `sub` from `user123` to `admin`), the signature becomes invalid. The server detects the tampering and rejects the token.

---

## 2.4 Token Creation Flow (Step-by-Step)

```
User POSTs credentials to POST /auth/login
         │
         ▼
FastAPI router (routers/auth.py) receives request
         │
         ▼
Queries PostgreSQL for user by username
         │
         ▼
verify_password(plain_password, hashed_password)
  → Uses bcrypt to compare stored hash with input
         │
         ├── FAIL → Return 401 Unauthorized
         │
         └── PASS ──►
                    │
                    ▼
         create_access_token({"sub": username})
           → Builds payload with exp and iat
           → Signs with SECRET_KEY using HS256
           → Returns JWT string
                    │
                    ▼
         Return {"access_token": jwt_string, "token_type": "bearer"}
                    │
                    ▼
         Frontend stores token
```

---

## 2.5 Token Verification Flow (Step-by-Step)

```
Client sends: Authorization: Bearer eyJhbGci...
         │
         ▼
FastAPI dependency: get_current_user() in dependencies/auth.py
         │
         ▼
Extract token from Authorization header
         │
         ▼
jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
  → Verifies signature (cryptographic check)
  → Checks exp claim (not expired)
  → Returns payload dict
         │
         ├── JWTError / signature mismatch → 401 Unauthorized
         ├── Token expired                 → 401 Unauthorized
         │
         └── VALID ──►
                    │
                    ▼
         Extract "sub" claim → username
                    │
                    ▼
         Query DB for user (only to confirm user still exists and is active)
                    │
                    ▼
         Inject User object into route handler
```

---

## 2.6 Password Hashing with bcrypt

Passwords are **never** stored in plain text. Your project uses bcrypt via `passlib`:

```python
# In auth_service.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Why bcrypt?**

1. **Slow by design** — bcrypt has a configurable work factor that makes brute-force attacks computationally expensive. MD5 and SHA-256 are too fast for password hashing.
2. **Salted** — bcrypt automatically generates a random salt for each password. Two users with the same password get different hashes. Rainbow table attacks are useless.
3. **Standard** — industry-accepted since 1999, still considered secure.

**bcrypt hash structure:**
```
$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/VcSFpXWCC
└──┘└──┘└──────────────────────────────────────────────────────┘
  │   │                      hash+salt
  │  cost factor (12 = 2^12 iterations)
 version
```

---

## 2.7 Middleware Usage

FastAPI uses **dependency injection** for auth. Routes that require authentication declare a dependency:

```python
# In a router
@router.get("/protected-route")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"user": current_user.username}
```

The `Depends(get_current_user)` tells FastAPI: "before executing this route, run `get_current_user()`. If it raises an exception, return the error. If it succeeds, pass the result as `current_user`."

**This is not a global middleware** — it is applied per-route. This is intentional: public routes (like `/auth/login`) do not need authentication.

---

## 2.8 Token Expiration Handling

Your `config.py` sets `ACCESS_TOKEN_EXPIRE_MINUTES`. When a token expires:

1. Client sends request with expired token
2. `jwt.decode()` checks the `exp` claim against current time
3. Raises `jose.ExpiredSignatureError` (subclass of `JWTError`)
4. Your code catches `JWTError` and returns `401 Unauthorized`
5. Frontend must re-authenticate (POST /auth/login again)

**Production improvement:** Implement refresh tokens. A short-lived access token (15 min) paired with a long-lived refresh token (7 days) stored in an HttpOnly cookie. The frontend uses the refresh token to silently get a new access token without re-login.

---

## 2.9 Security Risks and Mitigations

| Risk | Explanation | Mitigation |
|---|---|---|
| Token theft (XSS) | JS can read token from localStorage | Store in HttpOnly cookie (JS cannot read it) |
| Token theft (network) | Token intercepted in transit | HTTPS only — TLS encrypts all traffic |
| Weak secret key | Short secret = brute-forceable | Use 256-bit random key: `openssl rand -hex 32` |
| Long expiration | Stolen token valid for a long time | Short expiration (15-30 min) + refresh tokens |
| Algorithm confusion | Attacker sets `alg: none` | Always specify `algorithms=["HS256"]` explicitly in `jwt.decode()` |
| Token not invalidated on logout | Cannot revoke a JWT | Maintain a token blacklist in Redis if logout-before-expiry matters |

---

## 2.10 ASCII: JWT Lifecycle

```
                    ┌──────────────┐
                    │   Client     │
                    └──────┬───────┘
                           │  POST /auth/login
                           │  {username, password}
                           ▼
                    ┌──────────────┐
                    │  FastAPI     │
                    │  auth router │
                    └──────┬───────┘
                           │  verify_password()
                           │  hash stored in PostgreSQL
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │  users table │
                    └──────┬───────┘
                           │  user record
                           ▼
                    ┌──────────────┐
                    │ create_      │
                    │ access_token │
                    │ (HS256 sign) │
                    └──────┬───────┘
                           │  JWT token
                           ▼
                    ┌──────────────┐
                    │   Client     │  ◄─────── Stores token
                    └──────┬───────┘
                           │  GET /protected-route
                           │  Authorization: Bearer <token>
                           ▼
                    ┌──────────────┐
                    │  FastAPI     │
                    │ get_current_ │
                    │   user()     │
                    └──────┬───────┘
                           │  jwt.decode() — verify sig + expiry
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼──────┐           ┌──────▼─────┐
        │  VALID     │           │  INVALID   │
        │  → proceed │           │  → 401     │
        └────────────┘           └────────────┘
```

---

## 2.11 Interview Questions and Answers

**Q: What are the three parts of a JWT?**

A: Header (algorithm and token type), Payload (claims: subject, expiration, issued-at, plus any custom data), and Signature (HMAC or RSA hash of header+payload using the secret key). Each part is Base64URL-encoded and separated by dots.

**Q: Why is JWT stateless and why does that matter?**

A: Because all user identity information is embedded in the token itself. The server does not store sessions in a database. This means any server instance can verify any token using only the shared secret key, which is essential for horizontal scaling.

**Q: If a JWT is stolen, can you immediately invalidate it?**

A: Not by default — JWT is inherently stateless and cannot be revoked. Solutions: (1) use short expiration times so stolen tokens expire quickly, (2) maintain a token blacklist in Redis where you store revoked tokens until their expiry, (3) rotate the `SECRET_KEY` which invalidates all tokens but logs everyone out.

**Q: What is the difference between HS256 and RS256?**

A: HS256 uses a single shared secret key for both signing and verification (symmetric). All services must share the same secret. RS256 uses a private key for signing and a public key for verification (asymmetric). The public key can be shared safely, making RS256 better for multi-service architectures where you don't want every service to have signing capability.

**Q: Why use bcrypt for passwords instead of SHA-256?**

A: SHA-256 is a fast hash function — it can compute billions of hashes per second on modern hardware, making brute-force attacks trivial. bcrypt is intentionally slow (configurable iterations) and includes a salt, making it orders of magnitude harder to crack. Passwords need slow hashing; data integrity needs fast hashing.

---

## 2.12 Common Mistakes

1. **Storing tokens in localStorage** — vulnerable to XSS attacks. Use HttpOnly cookies for production.
2. **Using a weak/predictable SECRET_KEY** — use cryptographically random 256-bit key.
3. **Not checking `exp` claim** — always pass `options={"verify_exp": True}` (default in `python-jose`).
4. **Storing sensitive data in payload** — JWT payload is Base64 encoded, NOT encrypted. Anyone can decode it. Never put passwords, credit cards, or secrets in payload.
5. **Algorithm confusion attack** — if you accept multiple algorithms, an attacker may craft a token with `alg: none`. Always pin to exactly one algorithm.
6. **Not hashing passwords with bcrypt** — never store plain text or MD5/SHA passwords.

---

## 2.13 Production Considerations

- Always use HTTPS — JWT tokens in HTTP are exposed to network interception
- Rotate `SECRET_KEY` periodically (requires all users to re-login)
- Set short `ACCESS_TOKEN_EXPIRE_MINUTES` (15-30 minutes) and implement refresh token flow
- Log all authentication events (logins, failures, token rejections) for security auditing
- Implement rate limiting on `/auth/login` to prevent credential stuffing attacks (max 5 attempts per IP per minute)
- Consider JWT blacklisting in Redis for logout-before-expiry use cases
- In production multi-service environment, consider RS256 with centralized auth service

---

## 2.14 Key Files Reference

| File | Purpose |
|---|---|
| `backend/app/services/auth_service.py` | `create_access_token()`, `decode_access_token()`, `hash_password()`, `verify_password()` |
| `backend/app/routers/auth.py` | `POST /auth/login` and `POST /auth/register` endpoints |
| `backend/app/schemas/auth.py` | Pydantic schemas for login/register request/response |
| `backend/app/dependencies/` | `get_current_user()` dependency |
| `backend/app/config.py` | `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| `backend/app/models/` | SQLAlchemy `User` model |
