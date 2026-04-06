import os
import uuid
import pyotp
import random 
import smtplib 
import logging
import hmac
import hashlib
import socket  
import requests
from pathlib import Path
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vibe-garage-security")

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
    subject = "Welcome to the Garage | Verify Your Account"
    
    body = f"""
    Hello {username},

    Welcome to Vibe Garage. 

    To complete your registration and start streaming, please use the activation code below:
    
    CODE: {code}

    Stay tuned.
    The Vibe Garage Team
    """

    msg = MIMEMultipart()
    msg['From'] = f"Vibe Garage <{settings.SMTP_USER}>"
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    orig_getaddrinfo = socket.getaddrinfo



def send_welcome_verification_email(email: str, username: str, code: str):
    url = "https://api.brevo.com/v3/smtp/email"
    
    payload = {
        "sender": {"name": "Vibe Garage", "email": "hello@vibegarage.app"},
        "to": [{"email": email, "name": username}],
        "subject": "Welcome to the Garage | Verify Your Account",
        "htmlContent": f"""
            <html>
                <body style="font-family: sans-serif; background-color: #121212; color: #ffffff; padding: 20px;">
                    <h2 style="color: #ff3366;">Welcome to the Garage, {username}!</h2>
                    <p>To complete yhur registration and start streaming, use the code below:</p>
                    <div style="background: #1e1e1e; padding: 15px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #00ffcc; border: 1px solid #333;">
                        {code}
                    </div>
                    <p>Stay tuned.<br>The Vibe Garage Team</p>
                </body>
            </html>
        """
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": os.getenv("BREVO_API_KEY") 
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            logger.info(f"Brevo API: Verification email sent to {email}")
            return True
        else:
            logger.error(f"Brevo API Error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Brevo API: {str(e)}")
        return False

def verify_paystack_signature(payload: bytes, signature: str) -> bool: 
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)