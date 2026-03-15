from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.purchase import Purchase as Library 
from app.services.recommender import RecommenderService
from app.schemas.track import TrackPublic

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

        response_data.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist.stage_name,
            "is_verified": track.artist.is_verified_artist, # Maroon Badge
            "audio_url": track.file_url if is_owned else track.preview_url,
            "is_preview": not is_owned,
            "cover_image": track.cover_image,
            "genre": track.genre
        })

    return {
        "title": "Your Daily Vibe",
        "description": "Personalized mix based on your library and the artists yhu follow.",
        "tracks": response_data
    }