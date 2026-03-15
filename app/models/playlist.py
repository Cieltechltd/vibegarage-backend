from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from app.core.config import settings
import uuid

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    cover_image = Column(String, nullable=True, default=f"{settings.BASE_URL}/static/default-playlist.png")
    created_at = Column(DateTime, default=datetime.utcnow)
    tracks = relationship("PlaylistTrack", back_populates="playlist")

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(String, primary_key=True, index=True)
    playlist_id = Column(String, ForeignKey("playlists.id"))
    track_id = Column(String, ForeignKey("tracks.id"))
    added_at = Column(DateTime, default=datetime.utcnow)

    playlist = relationship("Playlist", back_populates="tracks")