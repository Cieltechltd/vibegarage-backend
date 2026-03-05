import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.artist_profile import ArtistProfile
from app.models.user import User
from app.models.track import Track
from app.models.clip import GarageClip
from app.models.follow import Follow
from app.schemas.artist import (
    ArtistProfileCreate, 
    ArtistProfileResponse, 
    ArtistStatsOut, 
    FullArtistProfileResponse
)
from pydantic import BaseModel

router = APIRouter(prefix="/artist", tags=["artist"])



@router.get("/view/{artist_id}", response_model=FullArtistProfileResponse)
def get_public_artist_profile(artist_id: str, db: Session = Depends(get_db)):
    """
    The unified 'Storefront' view for fans on vibegarage.app.
    Combines basic info, tracks, and 60s Garage Clips.
    """

    artist = db.query(User).filter(User.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")


    tracks = db.query(Track).filter(Track.artist_id == artist_id).all()
    clips = db.query(GarageClip).filter(GarageClip.artist_id == artist_id).all()

 
    return {
        "id": artist.id,
        "stage_name": artist.stage_name,
        "bio": artist.bio,
        "avatar": artist.avatar,
        "is_verified": getattr(artist, 'is_verified', False),
        "tracks": tracks,
        "clips": clips
    }



@router.post("/profile", response_model=ArtistProfileResponse)
def create_artist_profile(
    data: ArtistProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initial creation of an artist profile."""
    if current_user.role != "artist":
        current_user.role = "artist"

    existing = (
        db.query(ArtistProfile)
        .filter(ArtistProfile.user_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Artist profile already exists")

    profile = ArtistProfile(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        stage_name=data.stage_name,
        bio=data.bio,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile

@router.get("/profile", response_model=ArtistProfileResponse)
def get_own_artist_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current logged-in artist's profile."""
    profile = (
        db.query(ArtistProfile)
        .filter(ArtistProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Artist profile not found")

    return profile

class ArtistProfileUpdate(BaseModel):
    stage_name: Optional[str] = None
    bio: Optional[str] = None

@router.put("/profile")
def update_profile(
    profile_data: ArtistProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update artist details."""
    if not current_user.is_artist:
        raise HTTPException(status_code=403, detail="Not an artist")

    if profile_data.stage_name is not None:
        current_user.stage_name = profile_data.stage_name
    
   
    profile = db.query(ArtistProfile).filter(ArtistProfile.user_id == current_user.id).first()
    if profile and profile_data.bio is not None:
        profile.bio = profile_data.bio

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "stage_name": current_user.stage_name,
        "message": "Profile updated successfully"
    }



@router.get("/stats", response_model=ArtistStatsOut)
def artist_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Performance metrics for the artist dashboard."""
    tracks_query = db.query(Track).filter(Track.artist_id == current_user.id)

    total_tracks = tracks_query.count()
    total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(
        Track.artist_id == current_user.id
    ).scalar()

    total_likes = db.query(func.coalesce(func.sum(Track.likes), 0)).filter(
        Track.artist_id == current_user.id
    ).scalar()

    top = tracks_query.order_by(Track.plays.desc()).first()

    top_track = None
    if top:
        top_track = {
            "id": top.id,
            "title": top.title,
            "plays": top.plays,
            "likes": top.likes
        }

    return {
        "total_tracks": total_tracks,
        "total_plays": total_plays,
        "total_likes": total_likes,
        "top_track": top_track
    }



@router.post("/{artist_id}/follow")
def follow_artist(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Follow or unfollow another artist."""
    if artist_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    artist = db.query(User).filter(User.id == artist_id, User.role == "artist").first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    existing = db.query(Follow).filter(
        Follow.artist_id == artist_id,
        Follow.follower_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        action = "unfollowed"
    else:
        follow = Follow(artist_id=artist_id, follower_id=current_user.id)
        db.add(follow)
        action = "followed"

    db.commit()
    return {"status": action}

@router.get("/{artist_id}/followers")
def artist_followers_count(artist_id: str, db: Session = Depends(get_db)):
    """Get the total follower count for an artist."""
    count = db.query(Follow).filter(Follow.artist_id == artist_id).count()
    return {"followers": count}

@router.get("/{artist_id}/follow-status")
def follow_status(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check if the current user is following a specific artist."""
    is_following = db.query(Follow).filter(
        Follow.artist_id == artist_id,
        Follow.follower_id == current_user.id
    ).first() is not None

    followers = db.query(Follow).filter(Follow.artist_id == artist_id).count()

    return {
        "is_following": is_following,
        "followers": followers
    }