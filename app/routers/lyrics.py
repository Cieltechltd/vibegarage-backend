from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from app.core.artist_deps import verified_artist_required
from app.db.database import get_db
from app.models.track import Track
from app.models.lyrics import Lyric
from app.models.user import User

router = APIRouter(prefix="/lyrics", tags=["Lyrics"])

@router.post("/upload/{track_id}")
async def upload_lyrics(
    track_id: str,
    content: str, 
    current_artist: User = Depends(verified_artist_required),
    db: Session = Depends(get_db)
):
   
    track = db.query(Track).filter(
        Track.id == track_id, 
        Track.artist_id == current_artist.id
    ).first()
    
    if not track:
        raise HTTPException(status_code=404, detail="Track not found or ownership denied.")

   
    existing_lyric = db.query(Lyric).filter(Lyric.track_id == track_id).first()
    
    if existing_lyric:
        existing_lyric.content = content
        db.commit()
        return {"message": "Lyrics updated successfully!"}

    new_lyric = Lyric(
        id=str(uuid.uuid4()),
        track_id=track_id,
        content=content
    )
    db.add(new_lyric)
    db.commit()

    return {"message": "Lyrics added to your track!"}

@router.get("/{track_id}")
async def get_track_lyrics(track_id: str, db: Session = Depends(get_db)):
    """
    Fetches lyrics for a specific track. 
    Returns the content if found, otherwise a 404.
    """
    lyrics = db.query(Lyric).filter(Lyric.track_id == track_id).first()
    
    if not lyrics:
        raise HTTPException(
            status_code=404, 
            detail="No lyrics available for this track yet."
        )

    return {
        "track_id": lyrics.track_id,
        "content": lyrics.content
    }