import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

class ReleaseStatus(enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_RECEIVED = "payment_received"
    AI_AUDITING = "ai_auditing"
    AI_FAILED = "ai_failed"
    PROCESSING_DISTRIBUTION = "processing_distribution"
    LIVE = "live"

class DistributionRelease(Base):
    __tablename__ = "distribution_releases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    paystack_reference = Column(String(255), unique=True, nullable=True)
    status = Column(SQLEnum(ReleaseStatus), default=ReleaseStatus.PENDING_PAYMENT)
    
    
    upc = Column(String(13), nullable=True)
    isrc = Column(String(12), nullable=True)
    
   
    allow_sync_licensing = Column(Boolean, default=True)
    license_contract_url = Column(String(1000), nullable=True) 
    agent_trace_id = Column(String(255), nullable=True)        
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    splits = relationship("RoyaltySplit", back_populates="release", cascade="all, delete-orphan")

class RoyaltySplit(Base):
    __tablename__ = "royalty_splits"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(PG_UUID(as_uuid=True), ForeignKey("distribution_releases.id", ondelete="CASCADE"), nullable=False)
    collaborator_email = Column(String(255), index=True, nullable=False)
    share_percentage = Column(Float, nullable=False)
    is_confirmed = Column(Boolean, default=False)

   
    release = relationship("DistributionRelease", back_populates="splits")