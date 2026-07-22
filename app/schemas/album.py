from pydantic import BaseModel
from typing import Optional
from datetime import datetime  

class AlbumBase(BaseModel):
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    release_date: Optional[str] = None  


class AlbumCreate(AlbumBase):
    pass


class AlbumOut(AlbumBase):
    id: str
    album_id: str
    artist_id: str
    is_published: Optional[bool] = False

    class Config:
        from_attributes = True


class AlbumPublic(AlbumBase):
    id: int
    artist_id: int

    class Config:
        from_attributes = True