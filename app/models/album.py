from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    cover_image = Column(String, nullable=True)
    description = Column(String, nullable=True)
    release_date = Column(DateTime, default=datetime.utcnow)

    artist_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    artist = relationship("User", backref="albums")
    tracks = relationship("Track", backref="album", cascade="all, delete")
