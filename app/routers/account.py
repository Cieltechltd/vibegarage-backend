from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from sqlalchemy.orm import Session
import os
from pydantic import BaseModel
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.config import settings
from app.core.security import hash_password, verify_password 
from supabase import create_client, Client

router = APIRouter(prefix="/account", tags=["Account Management"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
BUCKET_NAME = "vibegarage"


@router.get("/me")
def get_account_overview(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "stage_name": getattr(current_user, 'stage_name', None),
        "email": current_user.email,
        "role": current_user.role,
        "is_verified": getattr(current_user, 'is_verified_artist', False),
        "created_at": current_user.created_at,
        "avatar_url": getattr(current_user, 'avatar', None) or getattr(current_user, 'avatar_url', None)
    }

@router.patch("/update-profile")
def update_profile(
    display_name: str = Query(None),
    bio: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if display_name:
        current_user.stage_name = display_name 
    if bio:
        current_user.bio = bio
    
    db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Cloud storage service credentials are not configured.")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        file_ext = os.path.splitext(file.filename)[1] or ".jpg"
        file_name = f"avatars/user_{current_user.id}{file_ext}"
        file_data = await file.read()

        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=file_name,
            file=file_data,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )

        storage_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_name}"

        if hasattr(current_user, 'avatar'):
            current_user.avatar = storage_url
        if hasattr(current_user, 'avatar_url'):
            current_user.avatar_url = storage_url

        db.commit()
        return {"avatar_url": storage_url}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload profile picture to cloud assets storage: {str(e)}"
        )


class PasswordChangeRequest(BaseModel):
    current_pw: str
    new_pw: str

@router.put("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.current_pw, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.password_hash = hash_password(payload.new_pw)
    db.commit()
    return {"message": "Password updated successfully"}

@router.patch("/deactivate")
def deactivate_account(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully. For reactivation, please contact support."}


@router.patch("/socials")
def update_social_links(
    instagram: str = Query(None),
    twitter: str = Query(None),
    website: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.instagram_url = instagram
    current_user.twitter_url = twitter
    current_user.website_url = website
    db.commit()
    return {"message": "Social links updated"}

@router.patch("/preferences")
def update_preferences(
    language: str = Query("en"),
    email_notifications: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.language = language
    current_user.email_notifications = email_notifications
    db.commit()
    return {"message": "Preferences updated"}

class ArtistUpgradeRequest(BaseModel):
    stage_name: str
    bio: str | None = None

@router.post("/upgrade-to-artist")
def upgrade_to_artist(
    request: ArtistUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "artist" or getattr(current_user, 'is_artist', False):
        raise HTTPException(
            status_code=400, 
            detail="You are already registered as an artist."
        )

    current_user.role = "artist"
    current_user.is_artist = True
    current_user.stage_name = request.stage_name
    
    if request.bio:
        current_user.bio = request.bio

    current_user.is_verified_artist = False 
    
    db.commit()
    db.refresh(current_user)

    return {
        "status": "success",
        "message": f"Congratulations {current_user.stage_name}, you are now an Artist on Vibe Garage!",
        "next_step": "Visit your Artist Dashboard to upload your first track."
    }