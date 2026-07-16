from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
import httpx
import os
import uuid
from app.db.database import get_db
from app.models.fanlink import Fanlink
from app.models.track import Track
from app.models.album import Album
from app.models.user import User
from app.schemas.fanlink import FanlinkCreate, FanlinkUpdate, FanlinkPublicResponse
from app.core.deps import get_current_user

router = APIRouter(
    prefix="/fanlinks",
    tags=["Fanlinks"]
)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "your_paystack_secret_key")


class TipInitializeRequest(BaseModel):
    email: EmailStr
    amount: int  
    subaccount_code: str  


@router.post("/create", response_model=FanlinkPublicResponse, status_code=status.HTTP_201_CREATED)
def create_fanlink(
    data: FanlinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create fanlinks.")

    existing_slug = db.query(Fanlink).filter(Fanlink.slug == data.slug.lower().strip()).first()
    if existing_slug:
        raise HTTPException(status_code=400, detail="This URL slug is already taken.")

    if data.track_id:
        track = db.query(Track).filter(Track.id == data.track_id, Track.artist_id == current_user.id).first()
        if not track:
            raise HTTPException(status_code=404, detail="Track not found or unauthorized.")
    
    if data.album_id:
        album = db.query(Album).filter(Album.id == data.album_id, Album.artist_id == current_user.id).first()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found or unauthorized.")

   
    new_link = Fanlink(
        id=str(uuid.uuid4()),
        slug=data.slug.lower().strip(),
        track_id=data.track_id,
        album_id=data.album_id,
        artist_id=current_user.id,
        streaming_links=data.streaming_links,
        is_tipping_enabled=data.is_tipping_enabled,
        paystack_subaccount_code=data.paystack_subaccount_code,
        vibe_gate_type=data.vibe_gate_type,
        vibe_gate_value=data.vibe_gate_value
    )
    
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return prepare_fanlink_response(new_link, db)


@router.get("/public/{slug}")
def get_public_fanlink(slug: str, db: Session = Depends(get_db)):
    fanlink = db.query(Fanlink).filter(Fanlink.slug == slug.lower().strip()).first()
    if not fanlink:
        raise HTTPException(status_code=404, detail="Fanlink page not found.")

    fanlink.views_count = (fanlink.views_count or 0.0) + 1
    db.commit()

    return prepare_fanlink_response(fanlink, db)


@router.post("/tips/initialize")
async def initialize_tip(payload: TipInitializeRequest):
    if not payload.subaccount_code:
        raise HTTPException(status_code=400, detail="No valid subaccount associated with this link.")

    amount_in_kobo = payload.amount * 100  
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "email": payload.email,
        "amount": amount_in_kobo,
        "currency": "NGN",
        "subaccount": payload.subaccount_code, 
        "bearer": "subaccount" 
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json=data,
                headers=headers
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Paystack: {str(e)}")


def prepare_fanlink_response(fanlink: Fanlink, db: Session):
    artist = db.query(User).filter(User.id == fanlink.artist_id).first()
    artist_name = artist.username if artist else "Unknown Artist"
    
    # 🌟 MODIFIED: Pull directly from the fanlink's own column
    paystack_subaccount = fanlink.paystack_subaccount_code
    
    title = "Untitled"
    description = ""
    cover_image = None
    preview_audio_url = None

    if fanlink.track_id:
        track = db.query(Track).filter(Track.id == fanlink.track_id).first()
        if track:
            title = track.title
            cover_image = track.cover_path
            preview_audio_url = track.audio_path  
    elif fanlink.album_id:
        album = db.query(Album).filter(Album.id == fanlink.album_id).first()
        if album:
            title = album.title
            cover_image = album.cover_image
            description = album.description

    return {
        "id": fanlink.id,
        "slug": fanlink.slug,
        "artist_name": artist_name,
        "title": title,
        "description": description,
        "cover_image": cover_image,
        "preview_audio_url": preview_audio_url,
        "streaming_links": fanlink.streaming_links or {},
        "is_tipping_enabled": fanlink.is_tipping_enabled,
        "paystack_subaccount_code": paystack_subaccount, 
        "vibe_gate_type": fanlink.vibe_gate_type,
        "views_count": int(fanlink.views_count or 0)
    }