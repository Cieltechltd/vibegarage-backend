from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.clip import GarageClip
from app.models.user import User
from app.models.track import Track
from app.models.play import Play    
from app.models.lyrics import Lyric
from app.core.config import settings

router = APIRouter(prefix="/discovery", tags=["Discovery"])



@router.get("/trending")
def get_trending_tracks(db: Session = Depends(get_db), limit: int = 10):
    
    time_threshold = datetime.utcnow() - timedelta(days=7)

    trending_query = (
        db.query(Track, func.count(Play.id).label("recent_plays"))
        .join(Play, Play.track_id == Track.id)
        .filter(Play.created_at >= time_threshold)
        .group_by(Track.id)
        .order_by(desc("recent_plays"))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": track.id,
            "title": track.title,
            "cover_art": track.cover_art,
            "artist_name": db.query(User.stage_name).filter(User.id == track.artist_id).scalar(),
            "trending_score": recent_plays
        }
        for track, recent_plays in trending_query
    ]

@router.get("/new-releases")
def get_new_releases(db: Session = Depends(get_db), limit: int = 10):
   
    return db.query(Track).order_by(desc(Track.created_at)).limit(limit).all()



@router.get("/feed")
def get_garage_feed(db: Session = Depends(get_db), limit: int = 20):
    
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
                "is_verified": artist.is_verified_artist, 
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