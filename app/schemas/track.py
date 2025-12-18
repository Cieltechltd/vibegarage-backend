from pydantic import BaseModel

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
