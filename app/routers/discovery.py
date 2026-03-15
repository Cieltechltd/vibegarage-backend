from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.db.database import get_db
from app.models.clip import GarageClip
from app.models.user import User
from app.models.lyrics import Lyric
from app.core.config import settings

router = APIRouter(prefix="/discovery", tags=["Discovery"])

@router.get("/feed")
def get_garage_feed(db: Session = Depends(get_db), limit: int = 20):
    """
    Unified feed of Garage Clips. 
    Prioritizes Verified Artists with the Maroon Badge.
    """
    query_results = (
        db.query(GarageClip, User)
        .join(User, GarageClip.artist_id == User.id)
        .order_by(
            desc(User.is_verified_artist), 
            desc(GarageClip.id)            
        )
        .limit(limit)
        .all()
    )

    feed_items = []
    for clip, artist in query_results:
        has_lyrics = db.query(Lyric).filter(Lyric.track_id == clip.track_id).first() is not None

        feed_items.append({
            "clip_id": clip.id,
            "video_url": clip.video_url,
            "caption": clip.caption,
            "artist": {
                "id": artist.id,
                "username": artist.username,
                "is_verified": artist.is_verified_artist, # Used to render the Maroon Badge
                "avatar": getattr(artist, 'avatar', f"{settings.BASE_URL}/static/default-avatar.png")
            },
            "meta": {
                "has_lyrics": has_lyrics,
                "track_id": clip.track_id
            }
        })

    return {
        "status": "success",
        "feed": feed_items,
        "count": len(feed_items)
    }