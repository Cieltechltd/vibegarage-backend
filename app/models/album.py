import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Album(Base):
    __tablename__ = "albums"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    cover_image = Column(String, nullable=True)
    description = Column(String, nullable=True)
    release_date = Column(DateTime, default=datetime.utcnow)
    artist_id = Column(String, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    artist = relationship("User", back_populates="albums")
    tracks = relationship("Track", back_populates="album", cascade="all, delete-orphan")
