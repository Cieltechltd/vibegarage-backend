from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.purchase import Purchase
from app.models.like import Like
from app.models.play import Play
from app.models.download import Download
from app.schemas.track import TrackOut

router = APIRouter(prefix="/library", tags=["User Library"])


@router.get("/purchased", response_model=List[TrackOut])
def get_purchased_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    return db.query(Track).join(Purchase).filter(Purchase.user_id == current_user.id).all()

@router.get("/liked", response_model=List[TrackOut])
def get_liked_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    return db.query(Track).join(Like).filter(Like.user_id == current_user.id).all()


@router.get("/recently-played", response_model=List[TrackOut])
def get_recently_played(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recent_tracks = (
        db.query(Track)
        .join(Play, Play.track_id == Track.id)
        .filter(Play.user_id == current_user.id)
        .order_by(desc(Play.id)) 
        .limit(20)
        .all()
    )
    return recent_tracks

@router.get("/downloads", response_model=List[TrackOut])
def get_download_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    downloaded_tracks = (
        db.query(Track)
        .join(Download, Download.track_id == Track.id)
        .filter(Download.user_id == current_user.id)
        .order_by(desc(Download.downloaded_at))
        .all()
    )
    return downloaded_tracks



@router.get("/my-uploads", response_model=List[TrackOut])
def get_artist_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() != "artist":
        return []
    return db.query(Track).filter(Track.artist_id == current_user.id).all()