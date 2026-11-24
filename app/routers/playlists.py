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
from app.services.track_media import track_playback_url
from app.services.track_access import get_owned_track_ids

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.get("/public")
def get_public_playlists(db: Session = Depends(get_db), limit: int = 10):
    playlists = db.query(Playlist).filter(Playlist.is_public == True).limit(limit).all()
    return playlists

@router.get("/my-favorites")
def get_my_favorites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    fav_playlist = db.query(Playlist).filter(
        Playlist.user_id == current_user.id,
        Playlist.is_favorites == True
    ).first()

    if not fav_playlist:
        return {"name": "Favorites", "cover_image": f"{settings.BASE_URL}/static/default-playlist.png", "tracks": []}

    results = (
        db.query(Track, User)
        .join(PlaylistTrack, PlaylistTrack.track_id == Track.id)
        .join(User, Track.artist_id == User.id)
        .filter(PlaylistTrack.playlist_id == fav_playlist.id)
        .all()
    )

    owned_track_ids = get_owned_track_ids(
        db, current_user.id, (track.id for track, _artist in results)
    )
    playlist_content = []
    for track, artist in results:
        artist_name = artist.stage_name or artist.username or "Unknown Artist"
        is_verified = getattr(artist, 'is_verified_artist', False)
        has_full_access = (
            track.id in owned_track_ids or track.artist_id == current_user.id
        )
        try:
            audio_url = track_playback_url(track, can_play_full=has_full_access)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Track audio is temporarily unavailable.") from exc

        playlist_content.append({
            "id": str(track.id),
            "title": track.title,
            "artist": artist_name,
            "is_verified": is_verified,
            "audio_url": audio_url,
            "is_preview": bool(track.is_for_sale and not has_full_access)
        })

    return {
        "id": fav_playlist.id,
        "name": fav_playlist.name,
        "cover_image": fav_playlist.cover_image or f"{settings.BASE_URL}/static/default-playlist.png",
        "tracks": playlist_content
    }

@router.post("/create")
def create_playlist(
    name: str,
    is_public: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_playlist = Playlist(
        id=str(uuid.uuid4()),
        name=name,
        user_id=current_user.id,
        is_public=is_public,
        is_favorites=False
    )
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
    playlists = db.query(Playlist).filter(
        Playlist.user_id == current_user.id,
        Playlist.is_favorites == False
    ).all()
    return playlists


@router.get("/{playlist_id}")
def get_playlist_details(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(status_code=404, detail="Playlist not found")

    results = (
        db.query(Track, User)
        .join(PlaylistTrack, PlaylistTrack.track_id == Track.id)
        .join(User, Track.artist_id == User.id)
        .filter(PlaylistTrack.playlist_id == playlist_id)
        .all()
    )

    owned_track_ids = get_owned_track_ids(
        db, current_user.id, (track.id for track, _artist in results)
    )
    playlist_content = []
    for track, artist in results:
        artist_name = artist.stage_name or artist.username or "Unknown Artist"
        is_verified = getattr(artist, 'is_verified_artist', False)
        has_full_access = (
            track.id in owned_track_ids or track.artist_id == current_user.id
        )
        try:
            audio_url = track_playback_url(track, can_play_full=has_full_access)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Track audio is temporarily unavailable.") from exc

        playlist_content.append({
            "id": str(track.id),
            "title": track.title,
            "artist": artist_name,
            "is_verified": is_verified,
            "audio_url": audio_url,
            "is_preview": bool(track.is_for_sale and not has_full_access)
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
