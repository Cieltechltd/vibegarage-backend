from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.db.database import get_db
from app.models.album import Album
from app.models.track import Track
from app.models.user import User
from app.schemas.album import AlbumOut, AlbumPublic
from app.core.deps import get_current_user
from supabase import create_client, Client
import uuid
import os

router = APIRouter(
    prefix="/albums",
    tags=["Albums"]
)

UPLOAD_DIR = "media/tracks"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
BUCKET_NAME = "vibegarage"


@router.post("/create-with-tracks", response_model=AlbumOut, status_code=status.HTTP_201_CREATED)
async def create_album_with_tracks(
    album_title: str = Form(...),
    album_description: Optional[str] = Form(None),
    album_cover_image: UploadFile = File(None),  # Changed from Form(None) to File(None)
    release_date: Optional[str] = Form(None),
    
    track_titles: List[str] = Form(...),
    track_genres: List[str] = Form([]),
    track_durations: List[float] = Form([]),
    audio_files: List[UploadFile] = File(...),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create albums.")

    cover_image_url = None
    if album_cover_image:
        try:
            cover_ext = os.path.splitext(album_cover_image.filename)[1] or ".jpg"
            cover_filename = f"covers/{uuid.uuid4()}{cover_ext}"
            cover_data = await album_cover_image.read()
            
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=cover_filename,
                file=cover_data,
                file_options={"content-type": album_cover_image.content_type}
            )
            cover_image_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{cover_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload album cover: {str(e)}")

    new_album = Album(
        id=str(uuid.uuid4()),
        title=album_title,
        description=album_description,
        cover_image=cover_image_url,
        artist_id=current_user.id,
        release_date=release_date,
        is_published=False
    )
    db.add(new_album)
    db.flush()

    # Process and append track elements...
    for i, title in enumerate(track_titles):
        if i >= len(audio_files):
            break
        
        audio_file = audio_files[i]
        genre = track_genres[i] if i < len(track_genres) else "Unknown"
        duration = track_durations[i] if i < len(track_durations) else 0.0

        try:
            audio_ext = os.path.splitext(audio_file.filename)[1] or ".mp3"
            audio_filename = f"audio/{uuid.uuid4()}{audio_ext}"
            audio_data = await audio_file.read()
            
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=audio_filename,
                file=audio_data,
                file_options={"content-type": audio_file.content_type}
            )
            audio_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{audio_filename}"
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to upload track '{title}': {str(e)}")

        new_track = Track(
            id=str(uuid.uuid4()),
            title=title,
            genre=genre,
            duration=duration,
            audio_path=audio_url,
            cover_path=cover_image_url,
            artist_id=current_user.id,
            album_id=new_album.id,
            is_for_sale=False,
            price=0.0
        )
        db.add(new_track)

    db.commit()
    db.refresh(new_album)

    return {
        "id": str(new_album.id),
        "album_id": str(new_album.id),
        "title": new_album.title,
        "description": new_album.description,
        "cover_image": new_album.cover_image,
        "artist_id": str(new_album.artist_id),
        "release_date": new_album.release_date,
        "is_published": new_album.is_published
    }


@router.post("/create-empty", response_model=AlbumOut, status_code=status.HTTP_201_CREATED)
async def create_empty_album(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    cover_image: UploadFile = File(None),  # Changed from Form(None) to File(None)
    release_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create albums.")

    cover_image_url = None
    if cover_image:
        try:
            cover_ext = os.path.splitext(cover_image.filename)[1] or ".jpg"
            cover_filename = f"covers/{uuid.uuid4()}{cover_ext}"
            cover_data = await cover_image.read()
            
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=cover_filename,
                file=cover_data,
                file_options={"content-type": cover_image.content_type}
            )
            cover_image_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{cover_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload album cover: {str(e)}")

    new_album = Album(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        cover_image=cover_image_url,
        artist_id=current_user.id,
        release_date=release_date,
        is_published=False
    )
    db.add(new_album)
    db.commit()
    db.refresh(new_album)

    return {
        "id": str(new_album.id),
        "album_id": str(new_album.id),
        "title": new_album.title,
        "description": new_album.description,
        "cover_image": new_album.cover_image,
        "artist_id": str(new_album.artist_id),
        "release_date": new_album.release_date,
        "is_published": new_album.is_published
    }


@router.put("/{album_id}/tracks", status_code=status.HTTP_200_OK)
def add_tracks_to_album(
    album_id: str,
    track_ids: List[str] = Form(...),  # Enforces a repeating list form-data field in Swagger UI
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.artist_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or unauthorized.")

    parsed_track_ids = []
    for track in track_ids:
        if "," in track:
            parsed_track_ids.extend([t.strip() for t in track.split(",") if t.strip()])
        else:
            parsed_track_ids.append(track.strip())

    updated_count = db.query(Track).filter(
        Track.id.in_(parsed_track_ids),
        Track.artist_id == current_user.id
    ).update({Track.album_id: album_id}, synchronize_session=False)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully linked {updated_count} tracks to the album '{album.title}'."
    }


@router.get("/drafts", response_model=List[Dict[str, Any]])
def get_my_album_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'is_artist', False) and current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can view album drafts.")

    drafts = db.query(Album).filter(
        Album.artist_id == current_user.id,
        (Album.is_published == False) | (Album.is_published == None)
    ).all()

    return [
        {
            "id": str(a.id),
            "album_id": str(a.id),
            "title": a.title,
            "description": a.description,
            "cover_image": a.cover_image,
            "artist_id": str(a.artist_id),
            "release_date": a.release_date,
            "is_published": False
        } for a in drafts
    ]


@router.get("/{album_id}", response_model=AlbumOut)
def get_album(
    album_id: str, 
    db: Session = Depends(get_db)
):
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return {
        "id": str(album.id),
        "album_id": str(album.id),
        "title": album.title,
        "description": album.description,
        "cover_image": album.cover_image,
        "artist_id": str(album.artist_id),
        "release_date": album.release_date,
        "is_published": getattr(album, 'is_published', False)
    }


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(
        Album.id == album_id,
        Album.artist_id == current_user.id
    ).first()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    db.delete(album)
    db.commit()
    return None


@router.post("/publish/{album_id}")
def publish_album(
    album_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(
        Album.id == album_id,
        Album.artist_id == current_user.id
    ).first()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found or unauthorized.")

    album.is_published = True
    db.commit()

    return {
        "status": "success",
        "message": f"Album '{album.title}' has been successfully published."
    }