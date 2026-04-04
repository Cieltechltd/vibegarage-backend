from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.database import Base

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    transaction_ref = Column(String, unique=True, nullable=True)