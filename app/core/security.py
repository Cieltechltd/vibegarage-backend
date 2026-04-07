import os
import uuid
import random 
import logging
import hmac
import hashlib
import requests  
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vibe-garage-security")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def generate_vg_id(prefix: str = "VG-U") -> str:
    unique_suffix = str(uuid.uuid4())[:8] 
    return f"{prefix}-{unique_suffix}"

def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"

def send_welcome_verification_email(email: str, username: str, code: str):
    
    api_key = os.getenv("RESEND_API_KEY")
    url = "https://api.resend.com/emails"
    
    if not api_key:
        logger.error("RESEND_API_KEY is not set in environment variables.")
        return False

    
    api_key = api_key.strip().replace('"', '').replace("'", "")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    html_content = f"""
    <div style="font-family: sans-serif; background-color: #000; color: #fff; padding: 40px; border-radius: 12px; border: 1px solid #333;">
        <h2 style="color: #00ffcc; text-align: center;">VIBE GARAGE</h2>
        <p>Welcome to VibeGarage, {username}!</p>
        <p>Use the code below to verify your account:</p>
        <div style="background: #111; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #00ffcc; border: 1px solid #00ffcc; margin: 20px 0;">
            {code}
        </div>
        <p style="text-align: center; color: #666;">The Vibe Garage Team</p>
    </div>
    """

    payload = {
        "from": "Vibe Garage <hello@vibegarage.app>",
        "to": [email],
        "subject": "Verify Your Account | Vibe Garage",
        "html": html_content
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code in [200, 201]:
            logger.info(f"Direct API: Verification email sent to {email}")
            return True
        else:
            logger.error(f"Resend API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to connect to Resend API: {str(e)}")
        return False

def verify_paystack_signature(payload: bytes, signature: str) -> bool: 
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)