from sqlalchemy import Column, String, Boolean, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID  
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid

class Fanlink(Base):
    __tablename__ = "fanlinks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=True)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=True)
    artist_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    streaming_links = Column(JSON, nullable=True, default=dict)
    is_tipping_enabled = Column(Boolean, default=False)
    vibe_gate_type = Column(String, nullable=True)
    vibe_gate_value = Column(String, nullable=True)
    views_count = Column(Float, default=0.0)

    track = relationship("Track", backref="fanlink")
    album = relationship("Album", backref="fanlink")