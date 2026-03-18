import uuid
import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.clip import GarageClip
from app.models.follow import Follow
from app.core.config import settings 
from app.services.file_storage import save_file 
from app.schemas.artist import (
    ArtistStatsOut, 
    FullArtistProfileResponse
)
from app.schemas.track import TrackOut 
from pydantic import BaseModel

router = APIRouter(prefix="/artist", tags=["Artist Management"])


@router.get("/dashboard")
def get_artist_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Standard Dashboard for all artists."""
    if current_user.role.lower() != "artist":
        raise HTTPException(
            status_code=403, 
            detail="Access Denied. Please upgrade your account to Artist to access this dashboard."
        )

    tracks_count = db.query(Track).filter(Track.artist_id == current_user.id).count()
    followers_count = db.query(Follow).filter(Follow.artist_id == current_user.id).count()
    is_verified = getattr(current_user, "is_verified_artist", False)

    return {
        "artist_name": current_user.stage_name,
        "verification_status": "Maroon Badge Verified" if is_verified else "Standard Artist",
        "stats": {
            "total_tracks": tracks_count,
            "total_followers": followers_count,
        },
        "premium_access": is_verified,
        "message": "Welcome to your Artist Hub. Upload tracks and engage with your listeners."
    }

@router.get("/premium/dashboard")
def get_premium_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Exclusive dashboard for Verified Artists."""
    if current_user.role.upper() != "ARTIST":
        raise HTTPException(status_code=403, detail="Artist account required")
        
    if not getattr(current_user, "is_verified_artist", False):
        raise HTTPException(
            status_code=403, 
            detail="The Maroon Badge is required to access Premium Features. Please visit Billing to verify."
        )

    clips_count = db.query(GarageClip).filter(GarageClip.artist_id == current_user.id).count()
    
    return {
        "status": "Verified",
        "message": f"Welcome back to the Inner Circle, {current_user.stage_name}",
        "tools": {
            "garage_clips": {"status": "Active", "count": clips_count},
            "lyrics_manager": {"status": "Active"}
        }
    }


@router.post("/upload", response_model=TrackOut)
def upload_track(
    title: str = Form(...),
    audio: UploadFile = File(...),
    cover: UploadFile | None = File(None),
    price: float = Form(0.0),
    is_for_sale: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Artist role required for uploads")

    audio_path = save_file(audio, "audio") 
    cover_path = save_file(cover, "covers") if cover else None

    track = Track(
        id=str(uuid.uuid4()), 
        title=title,
        audio_path=audio_path,
        cover_path=cover_path,
        artist_id=current_user.id,
        price=price, 
        is_for_sale=is_for_sale 
    )

    db.add(track)
    db.commit()
    db.refresh(track)
    return track



@router.get("/stats", response_model=ArtistStatsOut)
def artist_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Detailed analytics for the artist's tracks."""
    tracks_query = db.query(Track).filter(Track.artist_id == current_user.id)
    total_tracks = tracks_query.count()
    total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(Track.artist_id == current_user.id).scalar()
    total_likes = db.query(func.coalesce(func.sum(Track.likes), 0)).filter(Track.artist_id == current_user.id).scalar()
    
    top = tracks_query.order_by(Track.plays.desc()).first()
    top_track = {"id": top.id, "title": top.title, "plays": top.plays, "likes": top.likes} if top else None
    
    return {
        "total_tracks": total_tracks, 
        "total_plays": total_plays, 
        "total_likes": total_likes, 
        "top_track": top_track
    }

@router.get("/profile/{artist_id}")
def get_public_artist_profile(artist_id: str, db: Session = Depends(get_db)):
    """Public-facing profile for fans."""
    artist = db.query(User).filter(User.id == artist_id, User.role == "artist").first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    tracks = db.query(Track).filter(Track.artist_id == artist_id).all()
    clips = db.query(GarageClip).filter(GarageClip.artist_id == artist_id).all()

    return {
        "id": artist.id,
        "username": artist.username,
        "stage_name": artist.stage_name or "Unknown Artist",
        "bio": getattr(artist, 'bio', ""),
        "avatar_url": getattr(artist, 'avatar_url', None),
        "is_verified_artist": artist.is_verified_artist,
        "tracks": tracks,
        "clips": [{"id": c.id, "caption": getattr(c, 'caption', 'Clip'), "url": c.video_url} for c in clips]
    }

@router.post("/{artist_id}/follow")
def follow_artist(artist_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Follow/Unfollow logic."""
    if artist_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    
    artist = db.query(User).filter(User.id == artist_id, User.role == "artist").first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    existing = db.query(Follow).filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id).first()
    if existing:
        db.delete(existing)
        action = "unfollowed"
    else:
        follow = Follow(artist_id=artist_id, follower_id=current_user.id)
        db.add(follow)
        action = "followed"
    
    db.commit()
    return {"status": action}

@router.get("/{artist_id}/follow-status")
def follow_status(artist_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Check if following and get follower count."""
    is_following = db.query(Follow).filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id).first() is not None
    followers = db.query(Follow).filter(Follow.artist_id == artist_id).count()
    return {"is_following": is_following, "followers": followers}