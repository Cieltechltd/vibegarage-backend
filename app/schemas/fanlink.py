from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class FanlinkBase(BaseModel):
    slug: str
    track_id: Optional[str] = None
    album_id: Optional[str] = None
    streaming_links: Optional[Dict[str, str]] = {}  
    is_tipping_enabled: Optional[bool] = False
    vibe_gate_type: Optional[str] = None  
    vibe_gate_value: Optional[str] = None  

class FanlinkCreate(FanlinkBase):
    pass

class FanlinkUpdate(BaseModel):
    slug: Optional[str] = None
    streaming_links: Optional[Dict[str, str]] = None
    is_tipping_enabled: Optional[bool] = None
    vibe_gate_type: Optional[str] = None
    vibe_gate_value: Optional[str] = None

class FanlinkPublicResponse(BaseModel):
    id: str
    slug: str
    artist_name: str
    title: str               
    description: Optional[str] = None
    cover_image: Optional[str] = None
    preview_audio_url: Optional[str] = None 
    streaming_links: Dict[str, str]
    is_tipping_enabled: bool
    vibe_gate_type: Optional[str]
    views_count: int

    class Config:
        from_attributes = True