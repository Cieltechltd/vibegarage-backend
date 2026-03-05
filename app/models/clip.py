from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from datetime import datetime, timedelta
from app.db.database import Base

class GarageClip(Base):
    __tablename__ = "garage_clips"

    id = Column(String, primary_key=True, index=True)
    artist_id = Column(String, ForeignKey("users.id"))
    video_url = Column(String)  
    caption = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))