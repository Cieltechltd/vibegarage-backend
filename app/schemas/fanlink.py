from pydantic import BaseModel
from typing import Optional, Dict


class FanLinkCreate(BaseModel):
    track_id: str
    slug: str
    streaming_links: Dict[str, str] = {}
    accept_tips: bool = False
    subaccount_id: Optional[str] = None


class FanLinkOut(BaseModel):
    id: str
    slug: str
    track_id: str
    streaming_links: Dict[str, str] = {}
    accept_tips: bool
    subaccount_id: Optional[str] = None


class FanLinkTrackOut(BaseModel):
    id: str
    title: str
    artist_name: str
    cover_url: Optional[str] = None
    preview_url: Optional[str] = None


class FanLinkPublicOut(BaseModel):
    slug: str
    artist_id: str
    artist_username: str
    streaming_links: Dict[str, str] = {}
    is_tipping_enabled: bool
    track: FanLinkTrackOut