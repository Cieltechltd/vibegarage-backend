import os
import requests
from app.agent_distro.service import run_autonomous_agent_pipeline
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
import hmac
import hashlib
from sqlalchemy.orm import Session
from app.db.database import get_db


from app.agent_distro.schemas import TrackDistroSubmission
from app.agent_distro.models import DistributionRelease, RoyaltySplit, ReleaseStatus

router = APIRouter()


PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_placeholder_key")

@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize_distribution_and_licensing(
    submission: TrackDistroSubmission, 
    db: Session = Depends(get_db)
):
    
    try:
        
        db_release = DistributionRelease(
            track_id=submission.track_id,
            user_id="00000000-0000-0000-0000-000000000000", 
            status="PENDING_PAYMENT",
            allow_sync_licensing=submission.allow_sync_licensing
        )
        db.add(db_release)
        db.flush()  
        for split_item in submission.splits:
            db_split = RoyaltySplit(
                release_id=db_release.id,
                collaborator_email=split_item.collaborator_email,
                share_percentage=split_item.share_percentage
            )
            db.add(db_split)

        
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": "billing@vibegarage.app", 
            "amount": 500000,
            "callback_url": "https://agent.vibegarage.app/dashboard",
            "metadata": {
                "release_id": str(db_release.id),
                "track_id": str(submission.track_id)
            }
        }

        response = requests.post(paystack_url, json=payload, headers=headers)
        
    
        if response.status_code != 200:
            
            print(f"❌ PAYSTACK INITIALIZATION ERROR STATUS: {response.status_code}")
            print(f"❌ PAYSTACK INITIALIZATION RESPONSE BODY: {response.text}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Paystack initialization failed: {response.text}"
            )

        paystack_data = response.json()
        
        
        db_release.paystack_reference = paystack_data["data"]["reference"]
        db.commit()

        
        return {
            "status": "success",
            "release_id": db_release.id,
            "checkout_url": paystack_data["data"]["authorization_url"]
        }

    except HTTPException as he:
        
        raise he
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/webhook")
async def paystack_secure_webhook(
    request: Request, 
    payload_body: dict,
    x_paystack_signature: str = Header(None), 
    db: Session = Depends(get_db)
):
    
    
    payload = await request.body()
    
    
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'), 
        payload, 
        hashlib.sha512
    ).hexdigest()
    
    
    # if computed_signature != x_paystack_signature:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED, 
    #         detail="Security breach: Signature mismatch."
    #     )
        
    
    event_data = await request.json()
    
    
    if event_data.get("event") == "charge.success":
        reference = event_data["data"]["reference"]
        
       
        release = db.query(DistributionRelease).filter(
            DistributionRelease.paystack_reference == reference
        ).first()
        
        
        if release and release.status == "PENDING_PAYMENT":
            
            release.status = "PAYMENT_RECEIVED"
            db.commit()
            
            run_autonomous_agent_pipeline(release.id, db)

    return {"status": "event_acknowledged"}