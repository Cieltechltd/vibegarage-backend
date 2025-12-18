from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.like import Like
from app.models.track import Track
from app.models.follow import Follow
from app.models.user import User


router = APIRouter(prefix="/user", tags=["User"])


@router.get("/liked-tracks")
def liked_tracks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    likes = (
        db.query(Track)
        .join(Like, Like.track_id == Track.id)
        .filter(Like.user_id == current_user.id)
        .all()
    )

    return likes

@router.get("/following")
def followed_artists(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    artists = (
        db.query(User)
        .join(Follow, Follow.artist_id == User.id)
        .filter(Follow.follower_id == current_user.id)
        .all()
    )

    return artists

@router.get("/recently-played")
def recently_played(db: Session = Depends(get_db)):
    tracks = (
        db.query(Track)
        .order_by(Track.plays.desc())
        .limit(10)
        .all()
    )

    return tracks

