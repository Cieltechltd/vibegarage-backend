import uuid
import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
from app.schemas.artist import (
    ArtistStatsOut, 
    FullArtistProfileResponse
)
from app.schemas.track import TrackOut 
from pydantic import BaseModel

router = APIRouter(prefix="/artist", tags=["Artist Management"])



class PublicArtistProfileOut(BaseModel):
    id: str
    username: Optional[str]
    stage_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_verified_artist: bool 
    tracks: List[TrackOut]
    clips: List[dict] 

    class Config:
        from_attributes = True


@router.get("/premium/dashboard")
def get_premium_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Exclusive dashboard for Verified Artists to manage 
    advanced features like Clips andd Lyrics.
    """
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

@router.get("/stats", response_model=ArtistStatsOut)
def artist_stats(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    
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



@router.get("/profile/{artist_id}", response_model=PublicArtistProfileOut)
def get_public_artist_profile(artist_id: str, db: Session = Depends(get_db)):
    
    artist = db.query(User).filter(User.id == artist_id, User.role == "artist").first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    tracks = db.query(Track).filter(Track.artist_id == artist_id).all()
    clips = db.query(GarageClip).filter(GarageClip.artist_id == artist_id).all()

    return {
        "id": artist.id,
        "username": artist.username,
        "stage_name": artist.stage_name or "Unknown Artist",
        "bio": artist.bio or "",
        "avatar_url": artist.avatar_url,
        "is_verified_artist": artist.is_verified_artist,
        "tracks": tracks,
        "clips": [{"id": c.id, "caption": getattr(c, 'caption', 'Clip'), "url": c.video_url} for c in clips]
    }



@router.post("/{artist_id}/follow")
def follow_artist(artist_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Allows listeners to follow or unfollow artists."""
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
    """Checks if the current user is following this artist."""
    is_following = db.query(Follow).filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id).first() is not None
    followers = db.query(Follow).filter(Follow.artist_id == artist_id).count()
    return {"is_following": is_following, "followers": followers}