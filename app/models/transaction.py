from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum
from datetime import datetime
import enum
from app.db.database import Base

class TransactionType(str, enum.Enum):
    EARNING = "EARNING"
    WITHDRAWAL = "WITHDRAWAL"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType))
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)