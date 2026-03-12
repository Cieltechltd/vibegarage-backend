from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Album(Base):
    __tablename__ = "albums"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    cover_image = Column(String, nullable=True)
    description = Column(String, nullable=True)
    release_date = Column(DateTime, default=datetime.utcnow)

    artist_id = Column(String, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    artist = relationship("User", back_populates="albums")
    tracks = relationship("Track", backref="track_album", cascade="all, delete")
