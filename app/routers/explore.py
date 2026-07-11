from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from typing import List, Optional
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.track import Track
from app.models.user import User
from app.models.follow import Follow
from app.models.clip import GarageClip
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic
from app.routers.track import format_public_track


router = APIRouter(prefix="/explore", tags=["Explore & Search"])


@router.get("/feed")
def get_personalized_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    followed_ids = db.query(Follow.artist_id).filter(
        Follow.follower_id == current_user.id
    ).all()
    
    ids = [a_id for (a_id,) in followed_ids]

    social_tracks = []
    if ids:
        social_tracks = (
            db.query(Track)
            .filter(Track.artist_id.in_(ids))
            .order_by(Track.id.desc())
            .limit(20)
            .all()
        )

    
    if not social_tracks:
        trending_tracks = (
            db.query(Track)
            .order_by(Track.plays.desc())
            .limit(20)
            .all()
        )
        return [format_public_track(t, t.artist, db, current_user) for t in trending_tracks]

    return [format_public_track(t, t.artist, db, current_user) for t in social_tracks]


@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
   
    search_ts_query = func.plainto_tsquery('english', q)

    track_text = func.to_tsvector(
        'english',
        func.concat(func.coalesce(Track.title, ''), ' ', func.coalesce(User.stage_name, ''))
    )
    track_results = (
        db.query(Track)
        .join(User, Track.artist_id == User.id)
        .filter(track_text.op('@@')(search_ts_query))
        .order_by(desc(func.ts_rank(track_text, search_ts_query)))
        .limit(10)
        .all()
    )
    if not track_results:
        track_results = (
            db.query(Track)
            .join(User, Track.artist_id == User.id)
            .filter(or_(Track.title.ilike(f"%{q}%"), User.stage_name.ilike(f"%{q}%")))
            .limit(10).all()
        )

    artist_text = func.to_tsvector(
        'english',
        func.concat(func.coalesce(User.stage_name, ''), ' ', func.coalesce(User.username, ''))
    )
    artist_results = (
        db.query(User)
        .filter(User.role.ilike("artist"), artist_text.op('@@')(search_ts_query))
        .order_by(desc(func.ts_rank(artist_text, search_ts_query)))
        .limit(10)
        .all()
    )
    if not artist_results:
        artist_results = (
            db.query(User)
            .filter(
                User.role.ilike("artist"),
                or_(User.stage_name.ilike(f"%{q}%"), User.username.ilike(f"%{q}%"))
            )
            .limit(10).all()
        )

    clip_text = func.to_tsvector(
        'english',
        func.concat(func.coalesce(GarageClip.caption, ''), ' ', func.coalesce(User.stage_name, ''))
    )
    clip_results = (
        db.query(GarageClip)
        .join(User, GarageClip.artist_id == User.id)
        .filter(clip_text.op('@@')(search_ts_query))
        .order_by(desc(func.ts_rank(clip_text, search_ts_query)))
        .limit(10)
        .all()
    )
    if not clip_results:
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
                    id=str(t.id), 
                    title=t.title, 
                    play_count=getattr(t, 'plays', 0), 
                    like_count=getattr(t, 'likes', 0), 
                    artist=ArtistPublic(id=str(t.artist.id), stage_name=t.artist.stage_name)
                ) for t in track_results
            ],
            "artists": [
                {
                    "id": str(a.id), 
                    "stage_name": a.stage_name or a.username,
                    "is_verified": a.is_verified_artist
                } for a in artist_results
            ],
            "clips": [
                {
                    "id": str(c.id),
                    "video_url": c.video_url,
                    "caption": c.caption,
                    "artist_name": c.artist.stage_name or c.artist.username,
                    "is_verified": c.artist.is_verified_artist 
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
        .filter(User.is_verified_artist == False, User.role.ilike("artist"))
        .group_by(User.id)
        .order_by(desc("follower_count"))
        .limit(limit).all()
    )
    return [
        {"id": str(a.id), "name": a.stage_name or a.username, "followers": count} 
        for a, count in stars
    ]