import uuid
from sqlalchemy import Boolean, Column, String, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID 
from app.db.database import Base

class Track(Base):
    __tablename__ = "tracks"

    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    audio_path = Column(String, nullable=False)
    cover_path = Column(String, nullable=True)
    plays = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    artist_id = Column(String, ForeignKey("users.id"))
    artist = relationship("User", back_populates="tracks")
    likes_rel = relationship("Like", backref="track")
    plays_rel = relationship("Play", backref="track")
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=True)
    price = Column(Numeric(10, 2), default=0.00) 
    is_for_sale = Column(Boolean, default=False)
    
    album = relationship("Album", back_populates="tracks", overlaps="track_album")
    lyrics = relationship("Lyric", backref="track", uselist=False, cascade="all, delete-orphan")

