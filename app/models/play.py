from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class Play(Base):
    __tablename__ = "plays"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
