import secrets
import uuid
import pyotp
import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, logger, status, Header, BackgroundTasks 
from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.db.deps import get_db
from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    generate_vg_id,
    generate_verification_code,
    send_welcome_verification_email  
) 
from app.schemas.user import UserCreate, UserResponse, LoginRequest, TokenResponse
from app.core.deps import get_current_user
from datetime import datetime, timedelta
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.monetization import check_and_update_eligibility
from app.routers.admin import is_feature_enabled

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
   
    if is_feature_enabled(db, "maintenance_mode"):
        raise HTTPException(
            status_code=503, 
            detail="Vibe Garage is currently under maintenance. Please try again later."
        )
    
    if is_feature_enabled(db, "disable_signups"):
        raise HTTPException(
            status_code=403, 
            detail="New registrations are temporarily closed."
        )
    
    
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    
    v_code = generate_verification_code()
    requested_name = getattr(user, 'full_name', None)
    requested_username = getattr(user, 'username', None)
    fallback_name = requested_name or requested_username or "Viber"

   
    new_user = User(
        id=generate_vg_id("VG-U"), 
        email=user.email,
        full_name=fallback_name, 
        username=requested_username,
        password_hash=hash_password(user.password),
        dob=user.dob,
        role=user.role.value if hasattr(user, 'role') else "LISTENER",
        verification_code=v_code,
        is_active=False 
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
   
    background_tasks.add_task(
        send_welcome_verification_email, 
        new_user.email, 
        new_user.username or fallback_name, 
        v_code
    )

    return new_user

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(
            status_code=403, 
            detail="Account inactive. Please verify your email or contact support."
        )
    
   
    if user.role == "ARTIST":
        check_and_update_eligibility(user.id, db)

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(minutes=30)
    db.commit()

    return {
        "message": "Password reset token generated",
        "reset_token": token
    }

@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    x_2fa_code: Optional[str] = Header(None, alias="X-2FA-Code"),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.reset_token == data.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

   
    if getattr(user, 'two_factor_enabled', False):
        if not x_2fa_code:
            raise HTTPException(status_code=403, detail="2FA code required for password reset")
        
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(x_2fa_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    user.password_hash = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password reset successful"}

@router.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user.is_active = True 
    user.verification_code = None
    db.commit()
    return {"message": "Account activated successfully"}

@router.get("/2fa/setup")
def setup_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    if not current_user.two_factor_secret:
        current_user.two_factor_secret = pyotp.random_base32()
        db.add(current_user) 
        db.commit()
        db.refresh(current_user) 

    totp = pyotp.TOTP(current_user.two_factor_secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email, 
        issuer_name="Vibe Garage"
    )

    
    img = qrcode.make(provisioning_uri)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    
    return StreamingResponse(
        buf, 
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@router.post("/2fa/enable")
def enable_2fa(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    db.refresh(current_user)
    
    if not current_user.two_factor_secret:
        logger.error(f"2FA Enable failed: No secret for user {current_user.id}")
        raise HTTPException(
            status_code=400, 
            detail="2FA setup has not been initiated. Please visit /auth/2fa/setup first."
        )
    
    totp = pyotp.TOTP(current_user.two_factor_secret)
    
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    
    current_user.two_factor_enabled = True 
    db.commit()
    return {"message": "2FA enabled successfully"}