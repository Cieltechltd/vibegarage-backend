from pydantic import BaseModel
from typing import List, Optional


class AlbumBase(BaseModel):
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    release_date: Optional[str] = None


class AlbumCreate(AlbumBase):
    pass


class AlbumOut(AlbumBase):
    pass

class AlbumPublic(AlbumBase):
    id: int
    artist_id: int

    class Config:
        from_attributes = True
