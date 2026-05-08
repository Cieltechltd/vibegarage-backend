from pydantic import BaseModel
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
    plays: int
    likes: int
    artist_name: str
    price: float = 0.0
    is_for_sale: bool = False

    class Config:
        from_attributes = True

# use class TrackPublic, imm trying to fix something

class TrackPublic(BaseModel):
    id: str
    title: str
    play_count: int
    like_count: int
    artist: ArtistPublic

    class Config:
        from_attributes = True