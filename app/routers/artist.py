import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.deps import get_db
from app.core.deps import get_current_user
from app.models.artist_profile import ArtistProfile
from app.models.user import User
from app.models.track import Track
from app.schemas.artist import ArtistProfileCreate, ArtistProfileResponse, ArtistStatsOut
from app.models.follow import Follow



router = APIRouter(prefix="/artist", tags=["artist"])


@router.post("/profile", response_model=ArtistProfileResponse)
def create_artist_profile(
    data: ArtistProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
def get_artist_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(ArtistProfile)
        .filter(ArtistProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Artist profile not found")

    return profile


@router.get("/stats", response_model=ArtistStatsOut)
def artist_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    tracks = db.query(Track).filter(
        Track.artist_id == current_user.id
    )

    total_tracks = tracks.count()
    total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(
        Track.artist_id == current_user.id
    ).scalar()

    total_likes = db.query(func.coalesce(func.sum(Track.likes), 0)).filter(
        Track.artist_id == current_user.id
    ).scalar()

    top = tracks.order_by(Track.plays.desc()).first()

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
    if artist_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    artist = db.query(User).filter(
        User.id == artist_id,
        User.role == "artist"
    ).first()

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
        follow = Follow(
            artist_id=artist_id,
            follower_id=current_user.id
        )
        db.add(follow)
        action = "followed"

    db.commit()
    return {"status": action}


@router.get("/{artist_id}/followers")
def artist_followers_count(artist_id: str, db: Session = Depends(get_db)):
    count = db.query(Follow).filter(
        Follow.artist_id == artist_id
    ).count()

    return {"followers": count}


@router.get("/{artist_id}/follow-status")
def follow_status(
    artist_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    is_following = db.query(Follow).filter(
        Follow.artist_id == artist_id,
        Follow.follower_id == current_user.id
    ).first() is not None

    followers = db.query(Follow).filter(
        Follow.artist_id == artist_id
    ).count()

    return {
        "is_following": is_following,
        "followers": followers
    }


