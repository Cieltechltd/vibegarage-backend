from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional
from app.schemas.artist import ArtistPublic


SUPABASE_STORAGE_URL = "https://tatswhuxpbxzlprjfvln.supabase.co/storage/v1/object/public"


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

    @model_validator(mode="after")
    def use_preview_for_paid_tracks(self):
        # This schema is also used for purchased-library and artist-upload
        # responses. Keep those audio fields useful without ever turning the
        # private storage reference into a public URL.
        if self.is_for_sale:
            self.audio_path = (
                f"{SUPABASE_STORAGE_URL}/vibegarage/previews/{self.id}.mp3"
            )
        return self

    @field_validator("cover_path", mode="before")
    @classmethod
    def convert_cover_to_full_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        
        
        clean_path = value.lstrip("/")
        return f"{SUPABASE_STORAGE_URL}/vibegarage/{clean_path}"

    @field_validator("audio_path", mode="before")
    @classmethod
    def convert_audio_to_full_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        if value.startswith("private://"):
            return ""
        if value.startswith("http://") or value.startswith("https://"):
            return value
        
        clean_path = value.lstrip("/")
        return f"{SUPABASE_STORAGE_URL}/vibegarage/{clean_path}"


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

    @field_validator("cover_path", mode="before")
    @classmethod
    def convert_public_cover_to_full_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        
        clean_path = value.lstrip("/")
        return f"{SUPABASE_STORAGE_URL}/vibegarage/{clean_path}"

    @field_validator("audio_path", mode="before")
    @classmethod
    def convert_public_audio_to_full_url(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        if value.startswith("private://"):
            return ""
        if value.startswith("http://") or value.startswith("https://"):
            return value
        
        clean_path = value.lstrip("/")
        return f"{SUPABASE_STORAGE_URL}/vibegarage/{clean_path}"


class TrackPublic(BaseModel):
    id: str
    title: str
    play_count: int
    like_count: int
    artist: ArtistPublic

    class Config:
        from_attributes = True
