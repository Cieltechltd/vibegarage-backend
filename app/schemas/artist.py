from pydantic import BaseModel
from typing import Optional

class ArtistProfileCreate(BaseModel):
    stage_name: str
    bio: str | None = None

class ArtistPublic(BaseModel):
    id: int
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