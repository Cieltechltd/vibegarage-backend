from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from app.core.config import settings
import uuid

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    cover_image = Column(String, nullable=True, default=f"{settings.BASE_URL}/static/default-playlist.png")
    created_at = Column(DateTime, default=datetime.utcnow)
    tracks = relationship("PlaylistTrack", back_populates="playlist")

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id = Column(String, ForeignKey("playlists.id"))
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    added_at = Column(DateTime, default=datetime.utcnow)

    playlist = relationship("Playlist", back_populates="tracks")