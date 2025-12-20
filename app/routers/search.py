from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.database import get_db
from app.models.track import Track
from app.models.user import User
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic


router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/tracks")
def search_tracks(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    results = (
        db.query(Track)
        .join(User, Track.artist_id == User.id)
        .filter(
            or_(
                Track.title.ilike(f"%{q}%"),
                User.stage_name.ilike(f"%{q}%")
            )
        )
        .all()
    )

    return {
    "query": q,
    "count": len(results),
    "results": [
        TrackPublic(
            id=track.id,
            title=track.title,
            play_count=track.play_count,
            like_count=track.like_count,
            artist=ArtistPublic(
                id=track.artist.id,
                stage_name=track.artist.stage_name
            )
        )
        for track in results
    ]
}



@router.get("/artists")
def search_artists(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    results = (
        db.query(User)
        .filter(
            User.is_artist == True,
            User.stage_name.ilike(f"%{q}%")
        )
        .all()
    )

    return {
    "query": q,
    "count": len(results),
    "results": [
        ArtistPublic(
            id=artist.id,
            stage_name=artist.stage_name
        )
        for artist in results
    ]
}

