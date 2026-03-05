from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.monetization import check_and_update_eligibility, get_monetization_progress, calculate_artist_earnings
from app.schemas.artist import ArtistStatsResponse 
from app.services.wallet import get_available_balance 

router = APIRouter(prefix="/artist/stats", tags=["Artist Stats"])

@router.get("/overview", response_model=ArtistStatsResponse)
def get_artist_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "ARTIST":
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Artist role required."
        )

    
    is_eligible = check_and_update_eligibility(current_user.id, db)
    progress = get_monetization_progress(current_user.id, db)
  
    current_balance = get_available_balance(current_user.id, db) if is_eligible else 0.0
    
   
    if is_eligible:
        msg = "Monetization active! You are now earning V-Coins."
    else:
        # Calculate remaining streams for the user message
        remaining = 10000 - progress.get("current_streams", 0)
        msg = f"Keep growing! You need {max(0, remaining)} more streams to unlock V-Coin earnings."

   
    return {
        "total_streams": progress.get("current_streams", 0),
        "required_streams": 10000,
        "total_followers": progress.get("current_followers", 0),
        "required_followers": 1000,
        "monetization_eligible": is_eligible,
        "vcoin_balance": current_balance,
        "message": msg
    }