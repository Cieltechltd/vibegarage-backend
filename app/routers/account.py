from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os
from pydantic import BaseModel
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.config import settings
from app.core.security import hash_password, verify_password 

router = APIRouter(prefix="/account", tags=["Account Management"])


@router.get("/me")
def get_account_overview(current_user: User = Depends(get_current_user)):
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_verified": getattr(current_user, 'is_verified_artist', False),
        "created_at": current_user.created_at,
        "avatar_url": getattr(current_user, 'avatar_url', None)
    }

@router.patch("/update-profile")
def update_profile(
    display_name: str = None,
    bio: str = None,
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
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    os.makedirs("uploads/avatars", exist_ok=True)
    file_ext = file.filename.split(".")[-1]
    file_name = f"user_{current_user.id}.{file_ext}"
    file_path = os.path.join("uploads/avatars", file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.avatar_url = f"{settings.BASE_URL}/static/avatars/{file_name}"
    db.commit()
    return {"avatar_url": current_user.avatar_url}


@router.put("/change-password")
def change_password(
    current_pw: str,
    new_pw: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    if not verify_password(current_pw, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
   
    current_user.hashed_password = hash_password(new_pw)
    db.commit()
    return {"message": "Password updated successfully"}

@router.patch("/deactivate")
def deactivate_account(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    current_user.is_active = False
    db.commit()
    return {"message": "Account deactivated successfully."}



@router.patch("/socials")
def update_social_links(
    instagram: str = None,
    twitter: str = None,
    website: str = None,
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
    language: str = "en",
    email_notifications: bool = True,
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
    if current_user.role == "artist" or current_user.is_artist:
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