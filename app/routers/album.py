from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.album import Album
from app.models.track import Track
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumOut, AlbumPublic
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
    album_cover_image: Optional[str] = Form(None),
    release_date: Optional[str] = Form(None),
    
   
    track_titles: List[str] = Form(...),
    track_genres: List[str] = Form([]),
    track_durations: List[float] = Form([]),
    track_prices: List[float] = Form([]),
    track_is_for_sale: List[bool] = Form([]),
    
    
    audio_files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Cloud storage service credentials are not configured.")

    if not getattr(current_user, 'is_artist', False) and current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create albums and upload music.")

    if len(audio_files) != len(track_titles):
        raise HTTPException(
            status_code=400, 
            detail=f"Mismatch between number of audio files ({len(audio_files)}) and track titles ({len(track_titles)})."
        )

   
    album_id = str(uuid.uuid4())
    album = Album(
        id=album_id, 
        title=album_title,
        description=album_description,
        cover_image=album_cover_image,
        artist_id=current_user.id,
        release_date=release_date,
        is_published=False 
    )
    db.add(album)

    try:
        
        for index, audio in enumerate(audio_files):
            track_id = str(uuid.uuid4())
            
            
            audio_ext = os.path.splitext(audio.filename)[1] or ".mp3"
            audio_filename = f"audio/{track_id}{audio_ext}"
            audio_data = await audio.read()
            
            supabase_client.storage.from_(BUCKET_NAME).upload(
                path=audio_filename,
                file=audio_data,
                file_options={"content-type": audio.content_type}
            )
            audio_path_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{audio_filename}"
            genre = track_genres[index] if index < len(track_genres) else "Unknown"
            duration = track_durations[index] if index < len(track_durations) else 0.0
            price = track_prices[index] if index < len(track_prices) else 0.0
            is_sale = track_is_for_sale[index] if index < len(track_is_for_sale) else False

            
            track = Track(
                id=track_id, 
                title=track_titles[index],
                audio_path=audio_path_url,
                album_id=album_id,
                cover_path=album_cover_image,  
                artist_id=current_user.id,
                price=price, 
                is_for_sale=is_sale,
                genre=genre,
                duration=duration
            )
            db.add(track)

        db.commit()
        db.refresh(album)
        return album

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create album or upload music batch assets: {str(e)}"
        )


@router.post("/", response_model=AlbumOut, status_code=status.HTTP_201_CREATED)
def create_album(
    album_data: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'is_artist', False) and current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create albums")

    album = Album(
        id=str(uuid.uuid4()), 
        title=album_data.title,
        description=album_data.description,
        cover_image=album_data.cover_image,
        artist_id=current_user.id,
        release_date=album_data.release_date,
        is_published=False 
    )

    db.add(album)
    db.commit()
    db.refresh(album)

    return {
        "id": str(album.id),
        "title": album.title,
        "description": album.description,
        "cover_image": album.cover_image,
        "artist_id": str(album.artist_id),
        "release_date": album.release_date,
        "is_published": getattr(album, 'is_published', False)
    }


@router.get("/my", response_model=List[AlbumOut])
def get_my_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'is_artist', False) and current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Not an artist")

    albums = db.query(Album).filter(Album.artist_id == current_user.id).all()

    return [
        {
            "id": str(a.id),
            "title": a.title,
            "description": a.description,
            "cover_image": a.cover_image,
            "artist_id": str(a.artist_id),
            "release_date": a.release_date,
            "is_published": getattr(a, 'is_published', False)
        } for a in albums
    ]


@router.get("/drafts", response_model=List[AlbumOut])
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
            "title": a.title,
            "description": a.description,
            "cover_image": a.cover_image,
            "artist_id": str(a.artist_id),
            "release_date": a.release_date,
            "is_published": False
        } for a in drafts
    ]


@router.put("/{album_id}/tracks", status_code=status.HTTP_200_OK)
def add_tracks_to_album(
    album_id: str,
    track_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    album = db.query(Album).filter(Album.id == album_id, Album.artist_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or unauthorized.")

    updated_count = db.query(Track).filter(
        Track.id.in_(track_ids),
        Track.artist_id == current_user.id
    ).update({Track.album_id: album_id}, synchronize_session=False)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully linked {updated_count} tracks to the album '{album.title}'."
    }


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
    album = db.query(Album).filter(Album.id == album_id, Album.artist_id == current_user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    album.is_published = True
    db.commit()
    return {"message": "Album published successfully"}