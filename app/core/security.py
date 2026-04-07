import os
import uuid
import pyotp
import random 
import logging
import hmac
import hashlib
import requests
import resend  
from pathlib import Path
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vibe-garage-security")


resend.api_key = os.getenv("RESEND_API_KEY")

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def generate_vg_id(prefix: str = "VG-U") -> str:
    unique_suffix = str(uuid.uuid4())[:8] 
    return f"{prefix}-{unique_suffix}"

def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"

def send_welcome_verification_email(email: str, username: str, code: str):
   
    html_content = f"""
    <html>
        <body style="font-family: sans-serif; background-color: #121212; color: #ffffff; padding: 40px; border-radius: 12px;">
            <h2 style="color: #00ffcc; text-align: center;">VIBE GARAGE</h2>
            <p>Welcome to VibeGarage, {username}!</p>
            <p>To complete your registration and start streaming, use the activation code below:</p>
            <div style="background: #1e1e1e; padding: 20px; border-radius: 8px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #00ffcc; border: 1px solid #333; margin: 20px 0;">
                {code}
            </div>
            <p style="text-align: center; color: #888;">Stay tuned.<br>The VibeGarage Team</p>
        </body>
    </html>
    """

    try:
        params = {
            "from": "VibeGarage <hello@vibegarage.app>",
            "to": [email],
            "subject": "Welcome to VibeGarage | Verify Your Account",
            "html": html_content
        }
        
        resend.Emails.send(params)
        logger.info(f"Resend API: Verification email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Resend API Error for {email}: {str(e)}", exc_info=True)
        return False

def verify_paystack_signature(payload: bytes, signature: str) -> bool: 
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)