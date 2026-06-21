import uuid
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi.responses import FileResponse, RedirectResponse
from supabase import create_client, Client
from app.core.deps import get_current_user, get_current_user_optional
from app.db.deps import get_db
from app.models.track import Track
from app.schemas.track import PublicTrackOut
from app.models.like import Like
from app.models.user import User
from app.models.play import Play
from app.models.purchase import Purchase  
from app.models.download import Download 
from app.routers.admin import is_feature_enabled

router = APIRouter(prefix="/tracks", tags=["Tracks"])


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials missing from environment variables.")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "vibegarage"


def format_public_track(track: Track, artist_user: User, db: Session, current_user: Optional[User] = None) -> dict:
    is_liked = False
    if current_user:
        like_exists = db.query(Like).filter(Like.track_id == track.id, Like.user_id == current_user.id).first()
        is_liked = True if like_exists else False

    artist_name = artist_user.stage_name or artist_user.email if artist_user else "Unknown Artist"
    album_title = track.album.title if (hasattr(track, 'album') and track.album) else "Single"

    return {
        "id": str(track.id),
        "title": track.title,
        "artist": artist_name,
        "artist_id": str(track.artist_id),
        "album": album_title,
        "album_id": str(track.album_id) if track.album_id else None,
        "duration": getattr(track, 'duration', 0.0),
        "cover_path": track.cover_path or "",
        "audio_path": track.audio_path,
        "genre": getattr(track, 'genre', "Unknown"),
        "plays": getattr(track, 'plays', 0),
        "likes": getattr(track, 'likes', 0),
        "releaseDate": datetime.utcnow().strftime("%Y-%m-%d"), 
        "isLiked": is_liked,
        "is_for_sale": getattr(track, 'is_for_sale', False),
        "price": float(track.price) if track.price else 0.0
    }


@router.post("/upload", response_model=PublicTrackOut, status_code=status.HTTP_201_CREATED)
async def upload_track(
    title: str = Form(...),
    genre: str = Form("Unknown"),
    duration: float = Form(0.0),
    audio: UploadFile = File(...),
    album_id: str = Form(None),
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

    try:
        unique_id = str(uuid.uuid4())
        
        audio_ext = os.path.splitext(audio.filename)[1] or ".mp3"
        audio_filename = f"tracks/{unique_id}{audio_ext}"
        audio_data = await audio.read()
        
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=audio_filename,
            file=audio_data,
            file_options={"content-type": audio.content_type}
        )
        audio_path_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{audio_filename}"

        cover_path_url = ""
        if cover:
            cover_ext = os.path.splitext(cover.filename)[1] or ".jpg"
            cover_filename = f"covers/{unique_id}{cover_ext}"
            cover_data = await cover.read()
            
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=cover_filename,
                file=cover_data,
                file_options={"content-type": cover.content_type}
            )
            cover_path_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{cover_filename}"

        track = Track(
            id=unique_id, 
            title=title,
            audio_path=audio_path_url,
            album_id=album_id if album_id else None,
            cover_path=cover_path_url if cover else None,
            artist_id=current_user.id,
            price=price, 
            is_for_sale=is_for_sale,
            genre=genre,
            duration=duration
        )

        db.add(track)
        db.commit()
        db.refresh(track)
        
        return format_public_track(track, current_user, db, current_user)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Cloud asset storage upload failed: {str(e)}"
        )


@router.get("/stream/{track_id}")
def stream_track(
    track_id: str, 
    request: Request,
    ad_viewed: bool = Query(False),
    db: Session = Depends(get_db)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    artist = db.query(User).filter(User.id == track.artist_id).first()
    
    
    current_user = None
    auth_header = request.headers.get("Authorization")
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            from jose import jwt
            from app.core.config import settings
            
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id:
                current_user = db.query(User).filter(User.id == user_id).first()
        except Exception:
            current_user = None

   
    user_owns_track = False
    if current_user:
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
        user_owns_track = False

    
    audio_path_str = track.audio_path
    
    if not audio_path_str.startswith("http"):
        base_filename = os.path.basename(audio_path_str)
        audio_path_str = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/tracks/{base_filename}"

    final_stream_url = audio_path_str
    
    if getattr(track, 'is_for_sale', False) and not user_owns_track:
        base_filename = os.path.basename(audio_path_str)
        final_stream_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/previews/preview_{base_filename}"

    
    is_monetized = False
    if ad_viewed and artist and getattr(artist, 'monetization_eligible', False):
        is_monetized = True

    if current_user is not None:
        new_play = Play(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            track_id=track.id,  
            is_monetized_stream=is_monetized
        )
        db.add(new_play)
    if track.plays is None:
        track.plays = 0
    track.plays += 1
    db.commit()
    return RedirectResponse(url=final_stream_url)


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


@router.get("/my", response_model=List[PublicTrackOut])
def get_my_tracks(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    tracks = db.query(Track).filter(Track.artist_id == current_user.id).all()
    return [format_public_track(t, current_user, db, current_user) for t in tracks]


@router.post("/{track_id}/like")
def like_track(track_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    existing = db.query(Like).filter(Like.track_id == track_id, Like.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        db.query(Track).filter(Track.id == track_id).update({Track.likes: Track.likes - 1})
        action = "unliked"
    else:
        like = Like(user_id=current_user.id, track_id=track_id)
        db.add(like)
        db.query(Track).filter(Track.id == track_id).update({Track.likes: Track.likes + 1})
        action = "liked"

    db.commit()
    db.refresh(track)  
    return {"status": action, "likes": track.likes}


@router.get("/public/{track_id}", response_model=PublicTrackOut)
def get_public_track_by_id(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    result = db.query(Track, User).join(User, Track.artist_id == User.id).filter(Track.id == track_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Track not found"
        )
    
    track, artist_user = result

    current_user = None
    auth_header = request.headers.get("Authorization")
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            from jose import jwt
            from app.core.config import settings
            
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id:
                current_user = db.query(User).filter(User.id == user_id).first()
        except Exception:
            current_user = None

    
    return format_public_track(track, artist_user, db, current_user)


@router.get("/public/latest", response_model=List[PublicTrackOut])
def latest_tracks(db: Session = Depends(get_db)):
    results = db.query(Track, User).join(User, Track.artist_id == User.id).order_by(desc(Track.id)).limit(20).all()
    return [format_public_track(t, u, db, current_user=None) for t, u in results]


@router.get("/public/trending", response_model=List[PublicTrackOut])
def trending_tracks(db: Session = Depends(get_db)):
    results = db.query(Track, User).join(User, Track.artist_id == User.id).order_by(desc(Track.plays)).limit(20).all()
    return [format_public_track(t, u, db, current_user=None) for t, u in results]