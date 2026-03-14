import httpx
import os
import uuid
import hmac
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.track import Track
from app.models.transaction import Transaction, TransactionType
from app.models.purchase import Purchase
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/billing",
    tags=["Billing & Subscriptions"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
VERIFICATION_FEE_NGN = 13000  

def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    """Verifies that the webhook request is genuinely from Paystack."""
    if not signature:
        return False
    computed_hash = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed_hash, signature)

@router.post("/verify-artist/initialize")
async def initialize_verification(current_user: User = Depends(get_current_user)):
    """Starts the verification process for an artist."""
    if current_user.is_verified_artist:
        return {"message": "You are already a verified artist!"}

    url = "https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    
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
    """Confirms verification and activates the maroon badge."""
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()

    if data.get("status") and data["data"]["status"] == "success":
        user_id = data["data"]["metadata"]["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            user.is_verified_artist = True
            user.verification_fee_paid = True
            user.verified_at = datetime.utcnow()
            db.commit()

        return {"status": "success", "message": "Welcome to the Garage! You are now a Verified Artist."}
    
    raise HTTPException(status_code=400, detail="Payment verification failed")

@router.post("/buy-track/{track_id}")
async def initialize_track_purchase(
    track_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Initializes payment for a specific track."""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if not track.is_for_sale:
        raise HTTPException(status_code=400, detail="This track is not for sale")

    existing_purchase = db.query(Purchase).filter(
        Purchase.track_id == track_id, 
        Purchase.user_id == current_user.id
    ).first()
    if existing_purchase:
        return {"message": "You already own this track!"}

    reference = f"VG-TRK-{uuid.uuid4().hex[:8].upper()}"
    url = "https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    
    payload = {
        "email": current_user.email,
        "amount": int(track.price * 100), 
        "reference": reference,
        "callback_url": "https://vibegarage.app/purchase-success",
        "metadata": {
            "user_id": current_user.id, 
            "track_id": track_id, 
            "type": "track_purchase"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        data = response.json()

    if not data.get("status"):
        raise HTTPException(status_code=400, detail="Could not initialize track purchase")

    new_transaction = Transaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        track_id=track_id,
        amount=track.price,
        type=TransactionType.PURCHASE,
        reference=reference,
        status="pending"
    )
    db.add(new_transaction)
    db.commit()

    return {"checkout_url": data["data"]["authorization_url"], "reference": reference}

@router.post("/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Background handler for successful payments."""
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not verify_paystack_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(payload)
    event = data.get("event")

    if event == "charge.success":
        reference = data["data"]["reference"]
        metadata = data["data"].get("metadata", {})
        payment_type = metadata.get("type")

        if payment_type == "track_purchase":
            user_id = metadata.get("user_id")
            track_id = metadata.get("track_id")
            
            existing = db.query(Purchase).filter(Purchase.transaction_ref == reference).first()
            if not existing:
                txn = db.query(Transaction).filter(Transaction.reference == reference).first()
                if txn:
                    txn.status = "success"
                
                new_purchase = Purchase(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    track_id=track_id,
                    transaction_ref=reference
                )
                db.add(new_purchase)
                db.commit()

        elif payment_type == "artist_verification":
            user_id = metadata.get("user_id")
            user = db.query(User).filter(User.id == user_id).first()
            
            if user and not user.is_verified_artist:
                user.is_verified_artist = True
                user.verification_fee_paid = True
                user.verified_at = datetime.utcnow()
                db.commit()

    return {"status": "success"}