from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Body
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.track import Track
from app.schemas.track import TrackOut, PublicTrackOut
from app.services.file_storage import save_file
from app.models.like import Like
from app.models.user import User
from app.models.play import Play
from fastapi import HTTPException
import uuid


router = APIRouter(prefix="/tracks", tags=["Tracks"])

@router.post("/upload", response_model=TrackOut)
def upload_track(
    title: str = Form(...),
    audio: UploadFile = File(...),
    cover: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    audio_path = save_file(audio, "audio")
    cover_path = save_file(cover, "covers") if cover else None

    track = Track(
        title=title,
        audio_path=audio_path,
        cover_path=cover_path,
        artist_id=current_user.id
    )

    db.add(track)
    db.commit()
    db.refresh(track)

    return track


@router.get("/my", response_model=list[TrackOut])
def get_my_tracks(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(Track).filter(
        Track.artist_id == current_user.id
    ).all()

# Removed the duplicate my_tracks function to keep code clean

@router.get("/stream/{track_id}")
def stream_track(
    track_id: str, 
    ad_viewed: bool = Query(False), # Captured from the frontend signal
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Now requires user for tracking
):
    # 1. Verify track and get the artist (owner)
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    artist = db.query(User).filter(User.id == track.artist_id).first()

    # 2. Logic: Only record as monetized if ad was shown AND artist is eligible
    is_monetized = False
    if ad_viewed and artist and getattr(artist, 'monetization_eligible', False):
        is_monetized = True

    # 3. Create detailed Play record
    new_play = Play(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        track_id=track_id,
        is_monetized_stream=is_monetized
    )
    db.add(new_play)

    # 4. Increment legacy play counter
    track.plays += 1
    db.commit()

    return FileResponse(
        path=track.audio_path,
        media_type="audio/mpeg"
    )

@router.post("/{track_id}/like")
def like_track(
    track_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(Like).filter(
        Like.track_id == track_id,
        Like.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        track.likes -= 1
        action = "unliked"
    else:
        like = Like(user_id=current_user.id, track_id=track_id)
        db.add(like)
        track.likes += 1
        action = "liked"

    db.commit()
    return {"status": action, "likes": track.likes}


@router.get("/public/latest", response_model=list[PublicTrackOut])
def latest_tracks(db: Session = Depends(get_db)):
    tracks = (
        db.query(Track, User)
        .join(User, Track.artist_id == User.id)
        .order_by(Track.id.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": track.id,
            "title": track.title,
            "plays": track.plays,
            "likes": track.likes,
            "artist_name": user.stage_name or user.email
        }
        for track, user in tracks
    ]


@router.get("/public/trending", response_model=list[PublicTrackOut])
def trending_tracks(db: Session = Depends(get_db)):
    tracks = (
        db.query(Track, User)
        .join(User, Track.artist_id == User.id)
        .order_by(Track.plays.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": track.id,
            "title": track.title,
            "plays": track.plays,
            "likes": track.likes,
            "artist_name": user.stage_name or user.email
        }
        for track, user in tracks
    ]