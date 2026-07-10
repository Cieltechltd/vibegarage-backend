import logging
from fastapi import APIRouter, Depends, HTTPException
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
logger = logging.getLogger("vibe-garage-discovery")


@router.get("/trending")
def get_trending_tracks(db: Session = Depends(get_db), limit: int = 10):
    time_threshold = datetime.utcnow() - timedelta(days=10)

    trending_query = (
        db.query(Track, User, func.count(Play.id).label("recent_plays"))
        .join(Play, Play.track_id == Track.id)
        .join(User, Track.artist_id == User.id)
        .filter(Play.created_at >= time_threshold)
        .group_by(Track.id, User.id)
        .order_by(desc("recent_plays"))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(track.id),
            "title": track.title,
            "audio_path": track.audio_path,
            "cover_path": track.cover_path,
            "artist_name": artist.stage_name or artist.username,
            "trending_score": recent_plays
        }
        for track, artist, recent_plays in trending_query
    ]


@router.get("/new-releases")
def get_new_releases(limit: int = 10, db: Session = Depends(get_db)):
    try:
        query_results = (
            db.query(Track, User.username)
            .join(User, Track.artist_id == User.id)
            .order_by(desc(Track.id))
            .limit(limit)
            .all()
        )
        
        response_data = []
        for track, username in query_results:
            response_data.append({
                "id": str(track.id),
                "title": track.title,
                "audio_path": track.audio_path,
                "cover_path": track.cover_path,
                "plays": track.plays,
                "likes": track.likes,
                "genre": track.genre,
                "duration": track.duration,
                "price": track.price,
                "is_for_sale": track.is_for_sale,
                "album_id": str(track.album_id) if track.album_id else None,
                "artist_id": str(track.artist_id),
                "username": username
            })

        return response_data

    except Exception as e:
        logger.error(f"Discovery Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not fetch new releases")


@router.get("/feed")
def get_garage_feed(db: Session = Depends(get_db), limit: int = 20):
    query_results = (
        db.query(GarageClip, User)
        .join(User, GarageClip.artist_id == User.id)
        .filter(GarageClip.expires_at > datetime.utcnow())
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
            "clip_id": str(clip.id),
            "video_url": clip.video_url,
            "caption": clip.caption,
            "artist": {
                "id": str(artist.id),
                "username": artist.username,
                "is_verified": artist.is_verified_artist, 
                "avatar": getattr(artist, 'avatar', f"{settings.BASE_URL}/static/default-avatar.png")
            },
            "meta": {
                "has_lyrics": has_lyrics,
                "track_id": str(clip.track_id) if clip.track_id else None
            }
        })

    return {
        "status": "success",
        "feed": feed_items,
        "count": len(feed_items)
    }


@router.get("/editor-picks")
def get_editor_picks(db: Session = Depends(get_db), limit: int = 10):
    try:
        # Get tracks with most plays in the last 30 days
        time_threshold = datetime.utcnow() - timedelta(days=30)
        editor_picks_query = (
            db.query(Track, User, func.count(Play.id).label("recent_plays"))
            .join(Play, Play.track_id == Track.id)
            .join(User, Track.artist_id == User.id)
            .filter(Play.created_at >= time_threshold)
            .group_by(Track.id, User.id)
            .order_by(desc("recent_plays"))
            .limit(limit)
            .all()
        )

        editor_picks = [
            {
                "plays_count": recent_plays,
                "track": {
                    "id": str(track.id),
                    "title": track.title,
                    "audio_path": track.audio_path,
                    "cover_path": track.cover_path,
                    "genre": track.genre,
                    "duration": track.duration,
                    "price": track.price,
                    "is_for_sale": track.is_for_sale,
                    "artist": {
                        "id": str(artist.id),
                        "username": artist.username,
                        "stage_name": artist.stage_name or artist.username,
                        "is_verified": artist.is_verified_artist,
                        "avatar": getattr(artist, 'avatar', f"{settings.BASE_URL}/static/default-avatar.png")
                    }
                }
            }
            for track, artist, recent_plays in editor_picks_query
        ]

        return {
            "status": "success",
            "editor_picks": editor_picks,
            "count": len(editor_picks)
        }

    except Exception as e:
        logger.error(f"Editor Picks Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not fetch editor picks")