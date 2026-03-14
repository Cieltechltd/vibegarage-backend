from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.purchase import Purchase
from app.schemas.track import TrackOut

router = APIRouter(prefix="/library", tags=["User Library"])

@router.get("/purchased", response_model=list[TrackOut])
def get_purchased_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all tracks purchased by the current user.
    """
    purchased_tracks = (
        db.query(Track)
        .join(Purchase, Purchase.track_id == Track.id)
        .filter(Purchase.user_id == current_user.id)
        .all()
    )
    
    return purchased_tracks