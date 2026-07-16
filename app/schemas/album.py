from pydantic import BaseModel
from typing import Optional
from datetime import datetime  

class AlbumBase(BaseModel):
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    release_date: Optional[datetime] = None 


class AlbumCreate(AlbumBase):
    pass


class AlbumOut(AlbumBase):
    pass

class AlbumPublic(AlbumBase):
    id: int
    artist_id: int

    class Config:
        from_attributes = True