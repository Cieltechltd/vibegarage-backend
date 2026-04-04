import uuid
from sqlalchemy import Column, ForeignKey, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.sql import func
from app.db.database import Base

class Play(Base):
    __tablename__ = "plays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    
    is_monetized_stream = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
