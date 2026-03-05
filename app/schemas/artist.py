from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ArtistProfileCreate(BaseModel):
    stage_name: str
    bio: str | None = None

class ArtistPublic(BaseModel):
    id: str 
    stage_name: Optional[str] = None

    class Config:
        from_attributes = True

class ArtistProfileResponse(BaseModel):
    id: str
    stage_name: str
    bio: str | None
    avatar: str | None

    class Config:
        from_attributes = True

class ArtistStatsOut(BaseModel):
    total_tracks: int
    total_plays: int
    total_likes: int
    top_track: dict | None

class ArtistStatsResponse(BaseModel):
    total_streams: int
    required_streams: int = 10000
    total_followers: int
    required_followers: int = 1000
    monetization_eligible: bool
    vcoin_balance: float
    message: str

    class Config:
        from_attributes = True



class TrackResponse(BaseModel):
    
    id: str
    title: str
    cover_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ClipResponse(BaseModel):
    
    id: str
    video_url: str
    caption: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FullArtistProfileResponse(BaseModel):
   
    id: str
    stage_name: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    is_verified: bool = False
    tracks: List[TrackResponse] = []
    clips: List[ClipResponse] = []

    class Config:
        from_attributes = True