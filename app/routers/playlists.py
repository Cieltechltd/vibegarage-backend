from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import os
import shutil
from fastapi import UploadFile, File
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.playlist import Playlist, PlaylistTrack
from app.models.track import Track
from app.models.purchase import Purchase as Library 
from app.core.config import settings

router = APIRouter(prefix="/playlists", tags=["Playlists"])

@router.post("/create")
def create_playlist(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_playlist = Playlist(id=str(uuid.uuid4()), name=name, user_id=current_user.id)
    db.add(new_playlist)
    db.commit()
    return {"message": f"Playlist '{name}' created!", "id": new_playlist.id}

@router.post("/{playlist_id}/add/{track_id}")
def add_to_playlist(
    playlist_id: str, 
    track_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    
    owned = db.query(Library).filter(Library.user_id == current_user.id, Library.track_id == track_id).first()
    if not owned:
        raise HTTPException(status_code=403, detail="You must purchase this track to add it to a playlist.")
    
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found.")
    
    entry = PlaylistTrack(id=str(uuid.uuid4()), playlist_id=playlist_id, track_id=track_id)
    db.add(entry)
    db.commit()
    return {"message": "Track added to playlist"}


@router.delete("/{playlist_id}/remove/{track_id}")
def remove_from_playlist(
    playlist_id: str,
    track_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Removes a specific track from a listener's playlist.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found or unauthorized.")

    entry = db.query(PlaylistTrack).filter(
        PlaylistTrack.playlist_id == playlist_id, 
        PlaylistTrack.track_id == track_id
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Track not found in this playlist.")

    db.delete(entry)
    db.commit()
    return {"message": "Track removed from playlist"}

@router.get("/me")
def get_my_playlists(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Returns all playlists created by the current listener.
    """
    playlists = db.query(Playlist).filter(Playlist.user_id == current_user.id).all()
    return playlists


@router.get("/{playlist_id}")
def get_playlist_details(
    playlist_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all tracks in a playlist, applying 15-second preview logic where applicable.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

   
    results = (
        db.query(Track)
        .join(PlaylistTrack, PlaylistTrack.track_id == Track.id)
        .filter(PlaylistTrack.playlist_id == playlist_id)
        .all()
    )

    playlist_content = []
    for track in results:
        is_owned = db.query(Library).filter(
            Library.user_id == current_user.id, 
            Library.track_id == track.id
        ).first() is not None

        playlist_content.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist.stage_name,
            "is_verified": track.artist.is_verified_artist,
            "audio_url": track.file_url if is_owned else track.preview_url,
            "is_preview": not is_owned
        })

    return {
        "name": playlist.name,
        "cover_image": playlist.cover_image,
        "tracks": playlist_content
    }

@router.post("/{playlist_id}/upload-cover")
async def upload_playlist_cover(
    playlist_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    os.makedirs("uploads/playlists", exist_ok=True)
    file_ext = file.filename.split(".")[-1]
    file_name = f"playlist_{playlist_id}.{file_ext}"
    file_path = os.path.join("uploads/playlists", file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    playlist.cover_image = f"{settings.BASE_URL}/static/playlists/{file_name}"
    db.commit()
    
    return {"status": "success", "cover_url": playlist.cover_image}