from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
import re

# Base Schema
class UserBase(BaseModel):
    email: EmailStr
    username: str

# Schema for Registration (Input)
class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one number')
        return v

# Schema for Login (Input)
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema for Updating Profile (Input)
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

# Schema for Responses (Output - Excludes Password)
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for JWT Token
class Token(BaseModel):
    access_token: str
    token_type: str
