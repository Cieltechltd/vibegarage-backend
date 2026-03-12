import os
import uuid
import pyotp
import random 
import smtplib 
import logging
from pathlib import Path
from dotenv import load_dotenv
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings 

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("SECRET_KEY", "vibe_TIMES@123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

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
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generate_vg_id(prefix: str = "VG-U") -> str:
    unique_suffix = str(uuid.uuid4())[:8] 
    return f"{prefix}-{unique_suffix}"

def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"

def send_verification_email(email: str, code: str):
    subject = "Verify your Vibe Garage Account"
    body = f"Welcome to Vibe Garage! Your activation code is: {code}"

    msg = MIMEMultipart()
    msg['From'] = f"Vibe Garage <{settings.SMTP_USER}>"
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls() 
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Verification email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email}. Error: {str(e)}", exc_info=True)
        return False