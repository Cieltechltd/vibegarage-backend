from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.play import Play
from app.models.track import Track
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic

router = APIRouter(prefix="/trending", tags=["Trending"])


@router.get("/tracks")
def trending_tracks(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    results = (
        db.query(
            Track,
            func.count(Play.id).label("play_count")
        )
        .join(Play, Play.track_id == Track.id)
        .filter(Play.created_at >= seven_days_ago)
        .group_by(Track.id)
        .order_by(func.count(Play.id).desc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(results),
        "results": [
            TrackPublic(
                id=track.id,
                title=track.title,
                play_count=play_count,
                like_count=track.like_count,
                artist=ArtistPublic(
                    id=track.artist.id,
                    stage_name=track.artist.stage_name
                )
            )
            for track, play_count in results
        ]
    }
