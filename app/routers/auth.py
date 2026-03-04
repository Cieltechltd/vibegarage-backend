from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.deps import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from app.core.deps import get_current_user
from datetime import datetime, timedelta
import secrets
import uuid
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        id=str(uuid.uuid4()),
        email=user.email,
        username=getattr(user, 'username', None),
        password_hash=hash_password(user.password),
        role="LISTENER"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Retrieve user by email
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Verify password using security logic
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate JWT token using user UUID
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        # Security: don’t reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)

    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(minutes=30)

    db.commit()

    # MVP: return token (later we send email)
    return {
        "message": "Password reset token generated",
        "reset_token": token
    }

@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    # Retrieve user by the unique reset token
    user = db.query(User).filter(User.reset_token == data.token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Check if the token has expired
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    
    user.password_hash = hash_password(data.new_password)
    
   
    user.reset_token = None
    user.reset_token_expires = None

    db.commit()

    return {"message": "Password reset successful"}