from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class EarningEntry(Base):
   
    __tablename__ = "earning_entries"

    id = Column(String, primary_key=True, index=True)
    artist_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String, nullable=False)  # "tip" | "track_sale"
    gross_amount_ngn = Column(Float, nullable=False)
    platform_fee_ngn = Column(Float, nullable=False, default=0.0)
    net_amount_ngn = Column(Float, nullable=False)
    reference = Column(String, nullable=True)  
    track_id = Column(String, nullable=True)   
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    artist = relationship("User")