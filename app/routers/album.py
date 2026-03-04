from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.album import Album
from app.models.track import Track
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumOut, AlbumPublic
from app.core.deps import get_current_user
import uuid
import os

router = APIRouter(
    prefix="/albums",
    tags=["Albums"]
)

UPLOAD_DIR = "media/tracks"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=AlbumOut, status_code=status.HTTP_201_CREATED)
def create_album(
    album_data: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create albums"
        )

    album = Album(
        title=album_data.title,
        description=album_data.description,
        cover_image=album_data.cover_image,
        artist_id=current_user.id,
        release_date=album_data.release_date
    )

    db.add(album)
    db.commit()
    db.refresh(album)

    return album


@router.get("/my", response_model=List[AlbumOut])
def get_my_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_artist:
        raise HTTPException(status_code=403, detail="Not an artist")

    albums = db.query(Album).filter(
        Album.artist_id == current_user.id
    ).all()

    return albums

@router.get("/{album_id}", response_model=AlbumOut)
def get_album(
    album_id: int,
    db: Session = Depends(get_db)
):
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return album


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(
    album_id: int,
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


@router.post("/bulk-upload")
async def bulk_album_upload(
    album_data: AlbumCreate,
    title: str = Form(...),
    tracks: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
): 
    if not current_user.is_artist:
        raise HTTPException(status_code=403, detail="Only artists can upload albums")


    album = Album(
        title=title,
        description=album_data.description,
        cover_image=album_data.cover_image,
        artist_id=current_user.id,
        release_date=album_data.release_date
    )
    db.add(album)
    db.commit()
    db.refresh(album)

    created_tracks = []


    for file in tracks:
        file_ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"
        audio_path = os.path.join(UPLOAD_DIR, filename)

        with open(audio_path, "wb") as buffer:
            buffer.write(await file.read())

        track = Track(
            title=file.filename.rsplit(".", 1)[0],
            file_url=audio_path,
            album_id=album.id,
            artist_id=current_user.id
        )

        db.add(track)
        created_tracks.append(track)

    db.commit()

    return {
        "message": "Album uploaded successfully",
        "album_id": album.id,
        "total_tracks": len(created_tracks)
    }
