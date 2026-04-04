from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from app.db.database import Base

class TransactionType(str, enum.Enum):
    EARNING = "EARNING"
    WITHDRAWAL = "WITHDRAWAL"
    PURCHASE = "PURCHASE"  

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"))
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType))
    status = Column(String, default="pending")  
    description = Column(String, nullable=True)
    reference = Column(String, unique=True, index=True) # Paystack reference
    created_at = Column(DateTime, default=datetime.utcnow)