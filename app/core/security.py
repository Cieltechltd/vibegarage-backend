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

    
    LOGO_URL = f"{settings.BASE_URL}/assets/Logo-t5L1aV8V.svg"
    FACEBOOK_ICON = "https://img.icons8.com/m/fluent/48/facebook-new.png"
    TWITTER_ICON = "https://img.icons8.com/m/fluent/48/twitter.png"
    INSTAGRAM_ICON = "https://img.icons8.com/m/fluent/48/instagram-new.png"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Account</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #080808; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <table width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #080808; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="100%" maxWidth="550px" cellspacing="0" cellpadding="0" border="0" style="max-width: 550px; background-color: #121212; border: 1px solid #222222; border-radius: 16px; padding: 32px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
                        
                        <tr>
                            <td align="center" style="padding-bottom: 24px; border-bottom: 1px solid #222222;">
                                <img src="{LOGO_URL}" alt="VibeGarage" width="160" style="display: block; outline: none; border: none; max-width: 100%; height: auto;" onError="this.style.display='none'; document.getElementById('text-logo').style.display='block';">
                                <h1 id="text-logo" style="display: none; color: #00ffcc; font-size: 26px; font-weight: 800; margin: 0; letter-spacing: 2px;">VIBE GARAGE</h1>
                            </td>
                        </tr>

                        <tr>
                            <td style="padding-top: 32px;">
                                <p style="color: #ffffff; font-size: 18px; font-weight: 600; margin: 0 0 12px 0;">Welcome to VibeGarage, {username}!</p>
                                <p style="color: #aaaaaa; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
                                    Thank you for signing up for VibeGarage. To activate your account and start streaming, please enter the security verification code below:
                                </p>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="padding: 10px 0 20px 0;">
                                <table cellspacing="0" cellpadding="0" border="0" style="background-color: #1a1a1a; border: 1px solid #00ffcc; border-radius: 12px; width: 100%;">
                                    <tr>
                                        <td align="center" style="padding: 24px; letter-spacing: 6px; font-size: 36px; font-weight: 800; color: #00ffcc; font-family: monospace, sans-serif;">
                                            {code}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <tr>
                            <td style="padding-bottom: 32px; border-bottom: 1px solid #222222;">
                                <p style="color: #666666; font-size: 12px; line-height: 1.4; margin: 0; text-align: center;">
                                    This security code expires shortly. If you did not make this request, you can safely ignore this email.
                                </p>
                            </td>
                        </tr>

                        <tr>
                            <td align="center" style="padding-top: 32px;">
                                <p style="color: #888888; font-size: 13px; font-weight: 500; margin: 0 0 16px 0;">Connect with our community</p>
                                
                                <table cellspacing="0" cellpadding="0" border="0">
                                    <tr>
                                        <td style="padding: 0 12px;">
                                            <a href="https://www.facebook.com/VibeGarage" target="_blank" style="text-decoration: none;">
                                                <img src="{FACEBOOK_ICON}" alt="Facebook" width="28" height="28" style="display: block; border: 0;">
                                            </a>
                                        </td>
                                        <td style="padding: 0 12px;">
                                            <a href="https://x.com/VibeGarage" target="_blank" style="text-decoration: none;">
                                                <img src="{TWITTER_ICON}" alt="X (Twitter)" width="28" height="28" style="display: block; border: 0;">
                                            </a>
                                        </td>
                                        <td style="padding: 0 12px;">
                                            <a href="https://www.instagram.com/vibegarage_entertainment" target="_blank" style="text-decoration: none;">
                                                <img src="{INSTAGRAM_ICON}" alt="Instagram" width="28" height="28" style="display: block; border: 0;">
                                            </a>
                                        </td>
                                    </tr>
                                </table>

                                <p style="color: #444444; font-size: 11px; margin: 24px 0 0 0; font-weight: 400; letter-spacing: 0.5px; line-height: 1.5;">
                                    &copy; {datetime.now().year} Vibe Garage. All Rights Reserved.<br>
                                    A product of <a href="https://cieltech.org" target="_blank" style="color: #666666; text-decoration: underline; font-weight: 500;">Ciel Tech Ltd</a>.
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
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