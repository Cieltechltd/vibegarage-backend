from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.album import Album
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumOut, AlbumPublic
from app.core.deps import get_current_user

router = APIRouter(
    prefix="/albums",
    tags=["Albums"]
)


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
