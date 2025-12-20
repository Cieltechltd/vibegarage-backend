from pydantic import BaseModel
from typing import Optional
from app.schemas.artist import ArtistPublic


class TrackOut(BaseModel):
    id: str
    title: str
    audio_path: str
    cover_path: str | None

    class Config:
        from_attributes = True


class PublicTrackOut(BaseModel):
    id: str
    title: str
    plays: int
    likes: int
    artist_name: str

    class Config:
        from_attributes = True

# use class TrackPublic, imm trying to fix something

class TrackPublic(BaseModel):
    id: int
    title: str
    play_count: int
    like_count: int
    artist: ArtistPublic

    class Config:
        from_attributes = True