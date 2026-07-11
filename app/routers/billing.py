import httpx
import os
import uuid
import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from datetime import datetime, timedelta
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

logger = logging.getLogger("vibe-garage-billing")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
if not PAYSTACK_SECRET_KEY:
    raise RuntimeError("Paystack credentials missing from environment variables.")

HTTP_TIMEOUT_SECONDS = 15.0

VERIFICATION_PLANS = {
    "monthly":   {"label": "Monthly",               "amount_ngn": 7000,  "duration_days": 30},
    "quarterly": {"label": "Tri-Monthly (3 Months)", "amount_ngn": 20000, "duration_days": 90},
    "biannual":  {"label": "6 Months",               "amount_ngn": 36000, "duration_days": 182},
    "annual":    {"label": "Annual (12 Months)",     "amount_ngn": 60000, "duration_days": 365},
}


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


def _grant_or_extend_verification(db: Session, user: User, plan_key: str, paid_amount_kobo) -> bool:
    
    plan_info = VERIFICATION_PLANS.get(plan_key)
    if not plan_info:
        return False

    expected_amount_kobo = plan_info["amount_ngn"] * 100
    if paid_amount_kobo != expected_amount_kobo:
        return False

    now = datetime.utcnow()
    base_date = user.subscription_expiry if (user.subscription_expiry and user.subscription_expiry > now) else now
    user.subscription_expiry = base_date + timedelta(days=plan_info["duration_days"])
    user.is_verified_artist = True
    user.verification_fee_paid = True
    user.verified_at = now
    db.commit()
    return True


@router.get("/verify-artist/plans")
def list_verification_plans():
    """Public list of available artist verification subscription plans."""
    return {
        key: {"label": info["label"], "amount_ngn": info["amount_ngn"], "duration_days": info["duration_days"]}
        for key, info in VERIFICATION_PLANS.items()
    }


@router.post("/verify-artist/initialize")
async def initialize_verification(
    plan: str = Query(..., description=f"One of: {', '.join(VERIFICATION_PLANS.keys())}"),
    current_user: User = Depends(get_current_user)
):
    """Starts (or renews) the artist verification subscription for the chosen plan."""
    plan_info = VERIFICATION_PLANS.get(plan)
    if not plan_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan '{plan}'. Choose one of: {', '.join(VERIFICATION_PLANS.keys())}"
        )

    url = "https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    payload = {
        "email": current_user.email,
        "amount": plan_info["amount_ngn"] * 100,
        "callback_url": "https://vibegarage.app/verify-success",
        "metadata": {"user_id": current_user.id, "type": "artist_verification", "plan": plan}
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload, headers=headers)
        data = response.json()

    if not data.get("status"):
        raise HTTPException(status_code=400, detail="Could not initialize payment")

    return {
        "checkout_url": data["data"]["authorization_url"],
        "reference": data["data"]["reference"],
        "plan": plan,
        "amount_ngn": plan_info["amount_ngn"]
    }


@router.get("/verify-artist/confirm/{reference}")
async def confirm_verification(reference: str, db: Session = Depends(get_db)):
    """Confirms verification payment and activates/extends the maroon badge."""
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=headers)
        data = response.json()

    if data.get("status") and data["data"]["status"] == "success":
        metadata = data["data"].get("metadata", {})
        user_id = metadata.get("user_id")
        plan_key = metadata.get("plan")
        paid_amount = data["data"].get("amount")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found for this transaction.")

        granted = _grant_or_extend_verification(db, user, plan_key, paid_amount)
        if not granted:
            logger.warning(
                f"verify-artist/confirm rejected for user {user_id}: "
                f"plan={plan_key} paid_amount={paid_amount} did not match expected plan pricing."
            )
            raise HTTPException(
                status_code=400,
                detail="Payment amount does not match the selected verification plan. Please contact support."
            )

        return {
            "status": "success",
            "message": "Welcome to the Garage! You are now a Verified Artist.",
            "plan": plan_key,
            "verified_until": user.subscription_expiry
        }

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

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
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
        paid_amount = data["data"].get("amount")

        if payment_type == "track_purchase":
            user_id = metadata.get("user_id")
            track_id = metadata.get("track_id")

            existing = db.query(Purchase).filter(Purchase.transaction_ref == reference).first()
            if not existing:
                track = db.query(Track).filter(Track.id == track_id).first()
                expected_amount = int(track.price * 100) if track else None

                if track is None or paid_amount != expected_amount:
                    logger.warning(
                        f"webhook track_purchase rejected for reference {reference}: "
                        f"track_id={track_id} paid_amount={paid_amount} expected={expected_amount}"
                    )
                else:
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
            plan_key = metadata.get("plan")

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                granted = _grant_or_extend_verification(db, user, plan_key, paid_amount)
                if not granted:
                    logger.warning(
                        f"webhook artist_verification rejected for user {user_id}: "
                        f"plan={plan_key} paid_amount={paid_amount} did not match expected plan pricing."
                    )

    return {"status": "success"}