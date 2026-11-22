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
from sqlalchemy import text
from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.track import Track
from app.models.transaction import Transaction, TransactionType
from app.models.purchase import Purchase
from app.models.fanlink import FanLink
from app.models.earning import EarningEntry
from app.services.revenue import apply_platform_fee_and_credit
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


def _grant_or_extend_verification(
    db: Session, user: User, plan_key: str, paid_amount_kobo, reference: str
) -> bool:
    """Apply a verification payment once, using its Paystack reference as the key."""
    plan_info = VERIFICATION_PLANS.get(plan_key)
    if not plan_info:
        return False

    expected_amount_kobo = plan_info["amount_ngn"] * 100
    if paid_amount_kobo != expected_amount_kobo:
        return False

    # Serialize callbacks for this artist. This also makes legacy payments without
    # a locally stored transaction safe to process exactly once.
    locked_user = db.query(User).filter(User.id == user.id).with_for_update().first()
    if not locked_user:
        return False

    transaction = (
        db.query(Transaction)
        .filter(Transaction.reference == reference)
        .with_for_update()
        .first()
    )
    expected_description = f"artist_verification:{plan_key}"

    if transaction:
        if (
            transaction.user_id != locked_user.id
            or transaction.type != TransactionType.PURCHASE
            or transaction.description != expected_description
            or round(transaction.amount * 100) != expected_amount_kobo
        ):
            return False
        if transaction.status == "success":
            return True
        if transaction.status != "pending":
            return False
    else:
        # Older verification checkouts did not create a local transaction row.
        # Record their reference before applying the benefit so future retries skip it.
        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=locked_user.id,
            amount=plan_info["amount_ngn"],
            type=TransactionType.PURCHASE,
            status="pending",
            description=expected_description,
            reference=reference,
        )
        db.add(transaction)

    now = datetime.utcnow()
    base_date = (
        locked_user.subscription_expiry
        if locked_user.subscription_expiry and locked_user.subscription_expiry > now
        else now
    )
    locked_user.subscription_expiry = base_date + timedelta(days=plan_info["duration_days"])
    locked_user.is_verified_artist = True
    locked_user.verification_fee_paid = True
    locked_user.verified_at = now
    transaction.status = "success"
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
    db: Session = Depends(get_db),
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
    reference = f"VG-VER-{uuid.uuid4().hex.upper()}"

    new_transaction = Transaction(
        id=uuid.uuid4(),
        user_id=current_user.id,
        amount=plan_info["amount_ngn"],
        type=TransactionType.PURCHASE,
        status="pending",
        description=f"artist_verification:{plan}",
        reference=reference,
    )
    db.add(new_transaction)
    db.commit()

    payload = {
        "email": current_user.email,
        "amount": plan_info["amount_ngn"] * 100,
        "reference": reference,
        "callback_url": "https://vibegarage.app/verify-success",
        "metadata": {"user_id": current_user.id, "type": "artist_verification", "plan": plan}
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload, headers=headers)
        data = response.json()

    if not data.get("status") or (data.get("data") or {}).get("reference") != reference:
        db.refresh(new_transaction)
        if new_transaction.status == "pending":
            new_transaction.status = "failed"
            db.commit()
        raise HTTPException(status_code=400, detail="Could not initialize payment")

    return {
        "checkout_url": data["data"]["authorization_url"],
        "reference": reference,
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

    if (
        data.get("status")
        and data["data"].get("status") == "success"
        and data["data"].get("reference") == reference
    ):
        metadata = data["data"].get("metadata", {})
        if metadata.get("type") != "artist_verification":
            raise HTTPException(status_code=400, detail="Payment is not an artist verification transaction")
        user_id = metadata.get("user_id")
        plan_key = metadata.get("plan")
        paid_amount = data["data"].get("amount")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found for this transaction.")

        granted = _grant_or_extend_verification(db, user, plan_key, paid_amount, reference)
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

    new_transaction = Transaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        track_id=track_id,
        amount=track.price,
        type=TransactionType.PURCHASE,
        reference=reference,
        status="pending",
    )
    db.add(new_transaction)
    db.commit()
    
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

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        # Keep the transaction pending when the result is ambiguous. Paystack
        # may have accepted the request before the connection was interrupted,
        # and its webhook still needs a local reference to reconcile against.
        logger.exception("Could not confirm Paystack initialization for %s", reference)
        raise HTTPException(
            status_code=502,
            detail="Payment setup could not be confirmed. Please contact support before retrying.",
        ) from exc

    if not data.get("status") or (data.get("data") or {}).get("reference") != reference:
        new_transaction.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Could not initialize track purchase")

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
            _process_track_purchase(db, user_id, track_id, paid_amount, reference)

        elif payment_type == "artist_verification":
            user_id = metadata.get("user_id")
            plan_key = metadata.get("plan")

            user = db.query(User).filter(User.id == user_id).first()
            if user:
                granted = _grant_or_extend_verification(db, user, plan_key, paid_amount, reference)
                if not granted:
                    logger.warning(
                        f"webhook artist_verification rejected for user {user_id}: "
                        f"plan={plan_key} paid_amount={paid_amount} did not match expected plan pricing."
                    )

        elif payment_type == "tip":
            artist_id = metadata.get("artist_id")
            fanlink_slug = metadata.get("fanlink_slug")
            currency = data["data"].get("currency")
            if not _process_tip(
                db, artist_id, fanlink_slug, paid_amount, reference, currency
            ):
                logger.warning(
                    "Tip webhook did not match a valid tip for reference %s", reference
                )

    return {"status": "success"}


def _process_track_purchase(
    db: Session, user_id: str, track_id: str, paid_amount_kobo: int, reference: str
) -> bool:
    """Record and credit one track purchase, safely handling retried webhooks."""
    # The local transaction is created before checkout. Locking it serializes
    # concurrent Paystack retries for the same reference until the purchase and
    # artist credit are committed together.
    txn = (
        db.query(Transaction)
        .filter(Transaction.reference == reference)
        .with_for_update()
        .first()
    )
    if not txn:
        logger.warning("Track purchase webhook has no local transaction for reference %s", reference)
        # Ask Paystack to retry instead of acknowledging a callback that arrived
        # before its transaction record became visible.
        raise HTTPException(status_code=503, detail="Payment record is not ready; retry the webhook.")

    if (
        txn.type != TransactionType.PURCHASE
        or txn.user_id != user_id
        or str(txn.track_id) != str(track_id)
        or round(float(txn.amount) * 100) != paid_amount_kobo
    ):
        logger.warning(
            "Track purchase webhook does not match local transaction for reference %s", reference
        )
        return False

    if txn.status == "success":
        return True
    if txn.status not in {"pending", "failed"}:
        logger.warning("Track purchase transaction %s is not pending", reference)
        return False

    track = db.query(Track).filter(Track.id == txn.track_id).first()
    if not track:
        logger.warning("Track purchase webhook references missing track %s", txn.track_id)
        return False

    existing = db.query(Purchase).filter(Purchase.transaction_ref == reference).first()
    if existing:
        # A purchase should normally be committed with the successful status.
        # Treat an already-recorded reference as processed to avoid a second credit.
        txn.status = "success"
        db.commit()
        return True

    purchase = Purchase(
        id=str(uuid.uuid4()),
        user_id=user_id,
        track_id=txn.track_id,
        transaction_ref=reference,
    )
    db.add(purchase)

    artist = db.query(User).filter(User.id == track.artist_id).with_for_update().first()
    if artist:
        apply_platform_fee_and_credit(
            db,
            artist,
            paid_amount_kobo / 100,
            source="track_sale",
            reference=reference,
            track_id=str(txn.track_id),
        )
    else:
        logger.warning("Track sale %s: could not find artist %s to credit", reference, track.artist_id)

    txn.status = "success"
    db.commit()
    return True

def _process_tip(
    db: Session,
    artist_id: str,
    fanlink_slug: str,
    paid_amount_kobo: int,
    reference: str,
    currency: str,
) -> bool:
    """Credit a verified tip once, serializing retries and artist balance updates."""
    if (
        not artist_id
        or not fanlink_slug
        or not reference
        or currency != "NGN"
        or type(paid_amount_kobo) is not int
        or paid_amount_kobo <= 0
    ):
        return False

    # A transaction-scoped advisory lock works even though tip checkouts do not
    # currently create a local Transaction row. It serializes concurrent webhook
    # deliveries with the same Paystack reference before checking for an earning.
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:reference))"),
        {"reference": reference},
    )

    already_processed = db.query(EarningEntry).filter(
        EarningEntry.reference == reference
    ).first()
    if already_processed:
        logger.info("Tip %s already credited; skipping duplicate webhook delivery.", reference)
        return True

    fanlink = (
        db.query(FanLink)
        .filter(FanLink.slug == fanlink_slug)
        .with_for_update()
        .first()
    )
    if not fanlink or not fanlink.accept_tips or str(fanlink.artist_id) != str(artist_id):
        return False

    artist = db.query(User).filter(User.id == artist_id).with_for_update().first()
    if not artist:
        return False

    apply_platform_fee_and_credit(
        db,
        artist,
        paid_amount_kobo / 100,
        source="tip",
        reference=reference,
        track_id=str(fanlink.track_id),
    )
    db.commit()
    return True
