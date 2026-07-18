import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class FanLink(Base):
    __tablename__ = "fan_links"

    id = Column(String, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    artist_id = Column(String, ForeignKey("users.id"), nullable=False)
    streaming_links = Column(JSON, default=dict)

    accept_tips = Column(Boolean, default=False)
    subaccount_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    track = relationship("Track")
    artist = relationship("User")