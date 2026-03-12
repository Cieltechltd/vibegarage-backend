import httpx
import os
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.deps import get_current_user, get_db
from app.models.user import User
from dotenv import load_dotenv



load_dotenv()

router = APIRouter(
    prefix="/billing",
    tags=["Billing & Subscriptions"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
VERIFICATION_FEE_NGN = 13000  

@router.post("/verify-artist/initialize")
async def initialize_verification(current_user: User = Depends(get_current_user)):
    """Starts the one-time payment process for artist verification."""
    if current_user.is_verified_artist:
        return {"message": "You are already a verified artist!"}

    url = "https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    
    # Amount is in Kobo (NGN * 100)
    payload = {
        "email": current_user.email,
        "amount": VERIFICATION_FEE_NGN * 100,
        "callback_url": "https://vibegarage.app/verify-success",
        "metadata": {"user_id": current_user.id, "type": "artist_verification"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        data = response.json()

    if not data.get("status"):
        raise HTTPException(status_code=400, detail="Could not initialize payment")

    return {"checkout_url": data["data"]["authorization_url"], "reference": data["data"]["reference"]}

@router.get("/verify-artist/confirm/{reference}")
async def confirm_verification(reference: str, db: Session = Depends(get_db)):
    """Verifies the reference with Paystack and unlocks artist features."""
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()

    if data.get("status") and data["data"]["status"] == "success":
        user_id = data["data"]["metadata"]["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        # The Moment of Truth: Flip the switches!
        user.is_verified_artist = True
        user.verification_fee_paid = True
        user.verified_at = datetime.utcnow()
        db.commit()

        return {"status": "success", "message": "Welcome to the Garage! You are now a Verified Artist."}
    
    raise HTTPException(status_code=400, detail="Payment verification failed")