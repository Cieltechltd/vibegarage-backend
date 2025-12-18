from pydantic import BaseModel


class ArtistProfileCreate(BaseModel):
    stage_name: str
    bio: str | None = None


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