import os
import uuid
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from supabase import create_client, Client
from app.core.artist_deps import verified_artist_required
from app.db.database import get_db
from app.models.user import User
from app.models.clip import GarageClip
from app.core.config import settings

router = APIRouter(prefix="/clips", tags=["Garage Clips"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
BUCKET_NAME = "vibegarage"


def generate_secure_filename(artist_id: str, original_name: str):
    """Generates a unique filename: artistID_timestamp_random.ext."""
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
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Cloud storage service credentials are not configured.")

    if not getattr(current_artist, "is_verified_artist", False):
        raise HTTPException(
            status_code=403,
            detail="The Maroon Badge is required to upload Garage Clips. Please verify your account in the Billing section."
        )

    if file.content_type not in ["video/mp4", "video/quicktime"]:
        raise HTTPException(status_code=400, detail="Invalid video format. Use MP4 or MOV.")

    secure_name = generate_secure_filename(current_artist.id, file.filename)
    storage_path = f"clips/{secure_name}"

    try:
        file_data = await file.read()
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload clip: {e}")

    video_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"

    new_clip = GarageClip(
        id=str(uuid.uuid4()),
        artist_id=current_artist.id,
        video_url=video_url,
        caption=caption
    )
    db.add(new_clip)
    db.commit()
    db.refresh(new_clip)

    return {
        "message": "Clip uploaded to the Garage! It will be available for 24 hours.",
        "clip_id": new_clip.id,
        "url": video_url,
        "expires_at": new_clip.expires_at
    }