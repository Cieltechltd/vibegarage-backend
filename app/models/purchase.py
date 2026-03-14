from sqlalchemy import Column, String, ForeignKey, DateTime
from datetime import datetime
from app.db.database import Base

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    track_id = Column(String, ForeignKey("tracks.id"), nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    transaction_ref = Column(String, unique=True, nullable=True)