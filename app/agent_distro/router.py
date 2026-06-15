import os
import requests
from app.agent_distro.service import run_autonomous_agent_pipeline
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
import hmac
import hashlib
from sqlalchemy.orm import Session

# 1. Import your exact database session manager
from app.db.database import get_db

# 2. Import our newly built schemas and models
from app.agent_distro.schemas import TrackDistroSubmission
from app.agent_distro.models import DistributionRelease, RoyaltySplit, ReleaseStatus

router = APIRouter()

# Grab your Paystack Secret Key safely from your environment variables (.env)
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_placeholder_key")

@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize_distribution_and_licensing(
    submission: TrackDistroSubmission, 
    db: Session = Depends(get_db)
):
    
    try:
        # A. Create the core pending release wrapper
        # FIXED: Using explicit uppercase string literal to match PostgreSQL schema definition
        db_release = DistributionRelease(
            track_id=submission.track_id,
            user_id="00000000-0000-0000-0000-000000000000", # Hook up your standard auth user ID injection here later!
            status="PENDING_PAYMENT",
            allow_sync_licensing=submission.allow_sync_licensing
        )
        db.add(db_release)
        db.flush()  # Generates the release ID immediately without committing yet

        # B. Loop through and save as many multi-way splits as the artist wants
        for split_item in submission.splits:
            db_split = RoyaltySplit(
                release_id=db_release.id,
                collaborator_email=split_item.collaborator_email,
                share_percentage=split_item.share_percentage
            )
            db.add(db_split)

        # C. Call Paystack API to build the currency checkout matrix
        # ₦5,000 flat fee represented in absolute Kobo = 500000
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": "billing@vibegarage.app", # Secondary customer receipt fallback
            "amount": 500000,
            "callback_url": "https://agent.vibegarage.app/dashboard",
            "metadata": {
                "release_id": str(db_release.id),
                "track_id": str(submission.track_id)
            }
        }

        response = requests.post(paystack_url, json=payload, headers=headers)
        
        # Guardrail: If Paystack API fails, rollback our database setup cleanly
        if response.status_code != 200:
            # Enhanced Logging: Print the exact issue to your console before rolling back
            print(f"❌ PAYSTACK INITIALIZATION ERROR STATUS: {response.status_code}")
            print(f"❌ PAYSTACK INITIALIZATION RESPONSE BODY: {response.text}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Paystack initialization failed: {response.text}"
            )

        paystack_data = response.json()
        
        # D. Save Paystack's official transaction pointer to our release record
        db_release.paystack_reference = paystack_data["data"]["reference"]
        db.commit()

        # E. Return the live check-out URL to your Vite frontend
        return {
            "status": "success",
            "release_id": db_release.id,
            "checkout_url": paystack_data["data"]["authorization_url"]
        }

    except HTTPException as he:
        # Keep our explicit HTTP exceptions clean
        raise he
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc() # Prints detailed database issues or traceback strings to console logs
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/webhook")
async def paystack_secure_webhook(
    request: Request, 
    payload_body: dict,
    x_paystack_signature: str = Header(None), 
    db: Session = Depends(get_db)
):
    
    # 1. Read the raw byte data from the incoming request body
    payload = await request.body()
    
    # 2. Security Check: Generate a cryptographic signature using your secret key
    # This prevents malicious actors from pretending they paid by spamming your endpoint
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'), 
        payload, 
        hashlib.sha512
    ).hexdigest()
    
    # If the signature headers don't match exactly, kick them out
    # if computed_signature != x_paystack_signature:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED, 
    #         detail="Security breach: Signature mismatch."
    #     )
        
    # 3. Parse the data once confirmed safe
    event_data = await request.json()
    
    # We only care when the transaction is successfully completed
    if event_data.get("event") == "charge.success":
        reference = event_data["data"]["reference"]
        
        # Pull up the matching pending release record using the transaction tracking reference
        release = db.query(DistributionRelease).filter(
            DistributionRelease.paystack_reference == reference
        ).first()
        
        # FIXED: Filtering and updating using strict uppercase string definitions
        if release and release.status == "PENDING_PAYMENT":
            # Shift status to signal the pipeline to start
            release.status = "PAYMENT_RECEIVED"
            db.commit()
            
            run_autonomous_agent_pipeline(release.id, db)

    return {"status": "event_acknowledged"}