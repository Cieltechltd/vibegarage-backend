from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
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
