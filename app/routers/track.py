import uuid
import os
from alembic.environment import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Body, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from sqlalchemy import desc
from app.core.deps import get_current_user
from app.db.deps import get_db
from app.models.track import Track
from app.schemas.track import TrackOut, PublicTrackOut
from app.services.file_storage import save_file
from app.models.like import Like
from app.models.user import User
from app.models.play import Play
from app.models.purchase import Purchase  
from app.models.download import Download 
from app.core.config import settings 
from app.routers.admin import is_feature_enabled



router = APIRouter(prefix="/tracks", tags=["Tracks"])

@router.post("/upload", response_model=TrackOut)
def upload_track(
    title: str = Form(...),
    audio: UploadFile = File(...),
    cover: UploadFile | None = File(None),
    price: float = Form(0.0),
    is_for_sale: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    if is_feature_enabled(db, "maintenance_mode") or is_feature_enabled(db, "disable_uploads"):
        raise HTTPException(
            status_code=503, 
            detail="Uploads are temporarily disabled by the administrator."
        )

    if current_user.role.lower() != "artist":
        raise HTTPException(
            status_code=403, 
            detail="You must upgrade to an Artist account to upload tracks."
        )

    audio_path = save_file(audio, "audio") 
    cover_path = save_file(cover, "covers") if cover else None

    track = Track(
        id=str(uuid.uuid4()), 
        title=title,
        audio_path=audio_path,
        cover_path=cover_path,
        artist_id=current_user.id,
        price=price, 
        is_for_sale=is_for_sale 
    )

    db.add(track)
    db.commit()
    db.refresh(track)
    return track

@router.get("/stream/{track_id}")
def stream_track(
    track_id: str, 
    ad_viewed: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    artist = db.query(User).filter(User.id == track.artist_id).first()
    user_owns_track = False
    
    if current_user.id == track.artist_id:
        user_owns_track = True
    elif getattr(track, 'is_for_sale', False):
        purchase = db.query(Purchase).filter(
            Purchase.track_id == track_id,
            Purchase.user_id == current_user.id
        ).first()
        if purchase:
            user_owns_track = True
    else:
        user_owns_track = True

    final_path = track.audio_path
    if getattr(track, 'is_for_sale', False) and not user_owns_track:
        preview_filename = f"preview_{os.path.basename(track.audio_path)}"
        final_path = os.path.join("app/uploads/previews", preview_filename)
        
        if not os.path.exists(final_path):
             raise HTTPException(status_code=402, detail="Purchase required for full stream")

    is_monetized = False
    if ad_viewed and artist and getattr(artist, 'monetization_eligible', False):
        is_monetized = True

    new_play = Play(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        track_id=track_id,
        is_monetized_stream=is_monetized
    )
    db.add(new_play)
    track.plays += 1
    db.commit()

    return FileResponse(path=final_path, media_type="audio/mpeg")

@router.get("/download/{track_id}")
def download_track(
    track_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    is_owner = db.query(Purchase).filter(
        Purchase.track_id == track_id,
        Purchase.user_id == current_user.id
    ).first() is not None or current_user.id == track.artist_id

    if getattr(track, 'is_for_sale', False) and not is_owner:
        raise HTTPException(status_code=403, detail="Purchase required to download")

   
    new_download = Download(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        track_id=track_id
    )
    db.add(new_download)
    db.commit()

    return FileResponse(
        path=track.audio_path,
        media_type="audio/mpeg",
        filename=f"{track.title}.mp3" 
    )


@router.get("/my", response_model=List[TrackOut])
def get_my_tracks(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    tracks = db.query(Track).filter(Track.artist_id == current_user.id).all()
    
    
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "audio_path": t.audio_path,
            "cover_path": t.cover_path,
            "price": t.price,
            "is_for_sale": t.is_for_sale,
            "plays": getattr(t, 'plays', 0),
            "likes": getattr(t, 'likes', 0)
        } 
        for t in tracks
    ]

@router.post("/{track_id}/like")
def like_track(track_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(Like).filter(Like.track_id == track_id, Like.user_id == current_user.id).first()
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
    tracks = db.query(Track, User).join(User, Track.artist_id == User.id).order_by(Track.id.desc()).limit(20).all()
    return [{"id": t.id, "title": t.title, "plays": t.plays, "likes": t.likes, "artist_name": u.stage_name or u.email} for t, u in tracks]

@router.get("/public/trending", response_model=list[PublicTrackOut])
def trending_tracks(db: Session = Depends(get_db)):
    tracks = db.query(Track, User).join(User, Track.artist_id == User.id).order_by(Track.plays.desc()).limit(20).all()
    return [{"id": t.id, "title": t.title, "plays": t.plays, "likes": t.likes, "artist_name": u.stage_name or u.email} for t, u in tracks]