from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import uuid
import os
import secrets
import shutil
from datetime import datetime
from app.core.artist_deps import verified_artist_required 
from app.db.database import get_db
from app.models.user import User
from app.models.clip import GarageClip
from app.core.config import settings 

router = APIRouter(prefix="/clips", tags=["Garage Clips"])


UPLOAD_DIR = settings.UPLOAD_CLIP_DIR

def generate_secure_filename(artist_id: str, original_name: str):
    """Generates a unique filename: artistID_timestamp_random.ext"""
    ext = original_name.split(".")[-1]
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_hex = secrets.token_hex(4)
    return f"{artist_id}_{timestamp}_{random_hex}.{ext}"

@router.post("/upload")
async def upload_garage_clip(
    caption: str = None,
    file: UploadFile = File(...),
    current_artist: User = Depends(verified_artist_required),
    db: Session = Depends(get_db)
):
   
    if file.content_type not in ["video/mp4", "video/quicktime"]:
        raise HTTPException(status_code=400, detail="Invalid video format. Use MP4 or MOV.")

   
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    secure_name = generate_secure_filename(current_artist.id, file.filename)
    file_path = os.path.join(UPLOAD_DIR, secure_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

   
    video_url = f"{settings.BASE_URL}/static/clips/{secure_name}"

    new_clip = GarageClip(
        id=str(uuid.uuid4()),
        artist_id=current_artist.id,
        video_url=video_url,
        caption=caption
    )
    db.add(new_clip)
    db.commit()

    return {
        "message": "Clip uploaded to the Garage!", 
        "clip_id": new_clip.id,
        "url": video_url
    }