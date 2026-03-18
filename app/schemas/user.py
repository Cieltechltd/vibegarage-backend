from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    LISTENER = "LISTENER"
    ARTIST = "ARTIST"
    
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None
    stage_name: str | None = None
    dob: date = Field(..., description="User's date of birth in YYYY-MM-DD format")
    role: UserRole = UserRole.LISTENER # Default to LISTENER, can be overridden to ARTIST during registration

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: Optional[str] = None
    is_verified_artist: bool
    role: str

    class Config:
        from_attributes = True

class UserPublic(BaseModel):
    id: str  
    email: str
    username: str
    stage_name: Optional[str] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
