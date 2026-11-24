from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.purchase import Purchase as Library 
from app.services.recommender import RecommenderService
from app.schemas.track import TrackPublic
from app.services.track_media import track_playback_url

router = APIRouter(prefix="/daily-mix", tags=["Listener Discovery"])

@router.get("/")
def get_daily_mix(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    mix_tracks = RecommenderService.generate_daily_mix(db, current_user.id)
    response_data = []
    for track in mix_tracks:
        is_owned = db.query(Library).filter(
            Library.user_id == current_user.id, 
            Library.track_id == track.id
        ).first() is not None

        if current_user.id == track.artist_id:
            is_owned = True

        has_full_access = is_owned or current_user.id == track.artist_id
        show_preview = bool(track.is_for_sale and not has_full_access)
        try:
            audio_url = track_playback_url(track, can_play_full=has_full_access)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Track audio is temporarily unavailable.") from exc

        response_data.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist.stage_name,
            "is_verified": track.artist.is_verified_artist, # Maroon Badge
            "audio_url": audio_url,
            "is_preview": show_preview,
            "cover_image": track.cover_path,
            "genre": track.genre
        })

    return {
        "title": "Your Daily Vibe",
        "description": "Personalized mix based on your library and the artists yhu follow.",
        "tracks": response_data
    }
