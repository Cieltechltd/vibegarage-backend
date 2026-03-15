from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from typing import List, Optional
from app.db.database import get_db
from app.models.track import Track
from app.models.user import User
from app.models.follow import Follow
from app.models.clip import GarageClip
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic

router = APIRouter(prefix="/explore", tags=["Explore & Search"])

@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    Unified global search across Tracks, Artists, and Garage Clips.
    """
    track_results = (
        db.query(Track)
        .join(User, Track.artist_id == User.id)
        .filter(or_(Track.title.ilike(f"%{q}%"), User.stage_name.ilike(f"%{q}%")))
        .limit(10).all()
    )

    
    artist_results = (
        db.query(User)
        .filter(
            User.role == "artist", 
            or_(User.stage_name.ilike(f"%{q}%"), User.username.ilike(f"%{q}%"))
        )
        .limit(10).all()
    )

    
    clip_results = (
        db.query(GarageClip)
        .join(User, GarageClip.artist_id == User.id)
        .filter(or_(GarageClip.caption.ilike(f"%{q}%"), User.stage_name.ilike(f"%{q}%")))
        .limit(10).all()
    )

    return {
        "query": q,
        "results": {
            "tracks": [
                TrackPublic(
                    id=t.id, 
                    title=t.title, 
                    play_count=t.play_count, 
                    like_count=t.like_count,
                    artist=ArtistPublic(id=t.artist.id, stage_name=t.artist.stage_name)
                ) for t in track_results
            ],
            "artists": [
                {
                    "id": a.id, 
                    "stage_name": a.stage_name or a.username,
                    "is_verified": a.is_verified_artist
                } for a in artist_results
            ],
            "clips": [
                {
                    "id": c.id,
                    "video_url": c.video_url,
                    "caption": c.caption,
                    "artist_name": c.artist.stage_name or c.artist.username,
                    "is_verified": c.artist.is_verified_artist #
                } for c in clip_results
            ]
        }
    }

@router.get("/rising-stars")
def get_rising_stars(db: Session = Depends(get_db), limit: int = 10):
    """Promotes high-performing non-verified talent."""
    stars = (
        db.query(User, func.count(Follow.id).label("follower_count"))
        .join(Follow, Follow.artist_id == User.id)
        .filter(User.is_verified_artist == False, User.role == "artist")
        .group_by(User.id)
        .order_by(desc("follower_count"))
        .limit(limit).all()
    )
    return [
        {"id": a.id, "name": a.stage_name or a.username, "followers": count} 
        for a, count in stars
    ]