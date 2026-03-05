from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.payout import PayoutRequestCreate, PayoutResponse
from app.services.wallet import create_payout_request
from app.services.notifications import send_payout_notification

router = APIRouter(prefix="/payouts", tags=["Wallet & Payouts"])

@router.post("/request", response_model=PayoutResponse)
def request_withdrawal(
    data: PayoutRequestCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
   
    if not getattr(current_user, 'monetization_eligible', False):
        raise HTTPException(
            status_code=403, 
            detail="You must reach the 10k/1k milestone before requesting payouts."
        )

    payout, error = create_payout_request(current_user.id, data.amount, db)
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    send_payout_notification(
        artist_name=current_user.stage_name or current_user.email,
        amount=data.amount
    )

    return payout