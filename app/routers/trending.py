from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List
from app.db.database import get_db
from app.models.play import Play
from app.models.track import Track
from app.models.user import User
from app.models.follow import Follow
from app.models.clip import GarageClip
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic

router = APIRouter(prefix="/trending", tags=["Trending"])

@router.get("/landing-page")
def get_landing_page_data(db: Session = Depends(get_db), limit: int = 10):
   
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    
    verified_carousel = (
        db.query(User)
        .filter(User.is_verified_artist == True)
        .order_by(desc(User.verified_at))
        .limit(5)
        .all()
    )

 
    trending_tracks_results = (
        db.query(Track, func.count(Play.id).label("play_count"))
        .join(Play, Play.track_id == Track.id)
        .filter(Play.created_at >= seven_days_ago)
        .group_by(Track.id)
        .order_by(desc("play_count"))
        .limit(limit)
        .all()
    )

    
    trending_artists = (
        db.query(User, func.count(Follow.id).label("follower_gain"))
        .join(Follow, Follow.artist_id == User.id)
        .filter(User.role == "artist")
        .group_by(User.id)
        .order_by(desc("follower_gain"))
        .limit(5)
        .all()
    )

    return {
        "hero_carousel": [
            {
                "id": artist.id,
                "stage_name": getattr(artist, 'stage_name', artist.username),
                "avatar": getattr(artist, 'avatar', None),
                "badge": "Maroon"
            } for artist in verified_carousel
        ],
        "trending_tracks": [
            {
                "id": track.id,
                "title": track.title,
                "play_count": play_count,
                "artist_name": track.artist.stage_name,
                "is_verified": track.artist.is_verified_artist
            } for track, play_count in trending_tracks_results
        ],
        "trending_artists": [
            {
                "id": artist.id,
                "stage_name": getattr(artist, 'stage_name', artist.username),
                "follower_gain": follower_gain,
                "is_verified": artist.is_verified_artist
            } for artist, follower_gain in trending_artists
        ]
    }
