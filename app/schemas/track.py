from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.schemas.artist import ArtistPublic


class TrackOut(BaseModel):
    id: str
    title: str
    audio_path: str
    cover_path: str | None
    price: float = 0.0
    is_for_sale: bool = False
    plays: int = 0
    likes: int = 0

    class Config:
        from_attributes = True


class PublicTrackOut(BaseModel):
    id: str
    title: str
    artist: str                       
    artist_id: str
    album: Optional[str] = "Single"   
    album_id: Optional[str] = None
    duration: float = 0.0
    cover_path: Optional[str] = ""
    audio_path: str
    genre: Optional[str] = "Unknown"
    plays: int = 0
    likes: int = 0
    releaseDate: str
    isLiked: bool = False
    is_for_sale: bool = False
    price: float = 0.0

    
    model_config = ConfigDict(from_attributes=True)


class TrackPublic(BaseModel):
    id: str
    title: str
    play_count: int
    like_count: int
    artist: ArtistPublic

    class Config:
        from_attributes = True