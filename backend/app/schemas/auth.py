"""
Authentication and user-related Pydantic schemas.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ============================================================================
# Request Schemas
# ============================================================================

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


# ============================================================================
# Response Schemas
# ============================================================================

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
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserMe(BaseModel):
    """Schema for current user info."""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    
    class Config:
        from_attributes = True
