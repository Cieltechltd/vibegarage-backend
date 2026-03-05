from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum
from datetime import datetime
import enum
from app.db.database import Base

class PayoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class PayoutRequest(Base):
    __tablename__ = "payout_requests"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    currency = Column(String, default="NGN") 
    status = Column(Enum(PayoutStatus), default=PayoutStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)