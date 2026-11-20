import os
import requests
from app.agent_distro.service import run_autonomous_agent_pipeline
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
import hmac
import hashlib
import json
import logging
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.agent_distro.schemas import TrackDistroSubmission
from app.agent_distro.models import DistributionRelease, RoyaltySplit, ReleaseStatus

router = APIRouter()
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_placeholder_key")
logger = logging.getLogger("vibe-garage-distribution")
DISTRIBUTION_FEE_KOBO = 500000


def verify_paystack_signature(payload: bytes, signature: str | None) -> bool:
    """Check that a distribution webhook was signed with our Paystack secret."""
    if not signature:
        return False
    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"), payload, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize_distribution_and_licensing(
    submission: TrackDistroSubmission,
    db: Session = Depends(get_db),
):
    try:
        db_release = DistributionRelease(
            track_id=submission.track_id,
            user_id="00000000-0000-0000-0000-000000000000",
            status=ReleaseStatus.PENDING_PAYMENT,
            allow_sync_licensing=submission.allow_sync_licensing,
        )
        db.add(db_release)
        db.flush()

        for split_item in submission.splits:
            db.add(
                RoyaltySplit(
                    release_id=db_release.id,
                    collaborator_email=split_item.collaborator_email,
                    share_percentage=split_item.share_percentage,
                )
            )

        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": "billing@vibegarage.app",
            "amount": DISTRIBUTION_FEE_KOBO,
            "callback_url": "https://agent.vibegarage.app/dashboard",
            "metadata": {
                "release_id": str(db_release.id),
                "track_id": str(submission.track_id),
            },
        }

        response = requests.post(paystack_url, json=payload, headers=headers)
        if response.status_code != 200:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paystack initialization failed.",
            )

        paystack_data = response.json()
        db_release.paystack_reference = paystack_data["data"]["reference"]
        db.commit()
        return {
            "status": "success",
            "release_id": db_release.id,
            "checkout_url": paystack_data["data"]["authorization_url"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Distribution payment initialization failed")
        raise HTTPException(status_code=500, detail="Could not initialize distribution payment.") from exc


@router.post("/webhook")
async def paystack_secure_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    payload = await request.body()
    if not verify_paystack_signature(payload, x_paystack_signature):
        raise HTTPException(status_code=401, detail="Invalid Paystack signature.")

    try:
        event_data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc

    if event_data.get("event") == "charge.success":
        payment = event_data.get("data") or {}
        reference = payment.get("reference")
        metadata = payment.get("metadata") or {}
        if not reference:
            raise HTTPException(status_code=400, detail="Payment reference is missing.")

        release = (
            db.query(DistributionRelease)
            .filter(DistributionRelease.paystack_reference == reference)
            .with_for_update()
            .first()
        )

        if not release:
            logger.warning("Distribution webhook received unknown reference %s", reference)
        elif (
            payment.get("status") != "success"
            or payment.get("amount") != DISTRIBUTION_FEE_KOBO
            or payment.get("currency") != "NGN"
            or str(metadata.get("release_id")) != str(release.id)
            or str(metadata.get("track_id")) != str(release.track_id)
        ):
            logger.warning("Distribution payment data did not match release %s", release.id)
        elif release.status == ReleaseStatus.PENDING_PAYMENT:
            release.status = ReleaseStatus.PAYMENT_RECEIVED
            db.commit()
            run_autonomous_agent_pipeline(release.id, db)

    return {"status": "event_acknowledged"}
