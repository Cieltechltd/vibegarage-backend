# app/schemas/fanlink.py
from pydantic import BaseModel
from typing import Optional, Dict

class FanlinkBase(BaseModel):
    slug: str
    track_id: Optional[str] = None
    album_id: Optional[str] = None
    streaming_links: Optional[Dict[str, str]] = {}
    is_tipping_enabled: Optional[bool] = True
    paystack_subaccount_code: Optional[str] = None
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
    description: Optional[str] = ""
    cover_image: Optional[str] = None
    preview_audio_url: Optional[str] = None
    streaming_links: Dict[str, str] = {}
    is_tipping_enabled: bool = True
    paystack_subaccount_code: Optional[str] = None
    vibe_gate_type: Optional[str] = None
    views_count: int = 0

    class Config:
        from_attributes = True  