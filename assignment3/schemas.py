from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str

# --- Comment Schemas ---
class CommentCreate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    author_id: int
    post_id: int
    created_at: datetime

# --- Post Schemas ---
class PostCreate(BaseModel):
    title: str
    content: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: datetime

class PostWithComments(PostResponse):
    comments: List[CommentResponse] = []

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
