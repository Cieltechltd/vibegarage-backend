from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid

class Track(Base):
    __tablename__ = "tracks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    audio_path = Column(String, nullable=False)
    cover_path = Column(String, nullable=True)
    plays = Column(Integer, default=0)
    likes = Column(Integer, default=0)


    artist_id = Column(String, ForeignKey("users.id"))
    artist = relationship("User", back_populates="tracks")
    likes_rel = relationship("Like", backref="track")

