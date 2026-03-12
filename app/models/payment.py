from app.db.database import Base
from sqlalchemy import Column, String, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from app.core.security import generate_vg_id

class ArtistPaymentSettings(Base):
    __tablename__ = "artist_payment_settings"

    id = Column(String, primary_key=True, default=lambda: generate_vg_id("VG-P"))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    preferred_method = Column(String, default="bank") # 'bank' or 'paypal'
    
    # Nigeria Bank Details (Optimized for Paystack)
    bank_name = Column(String, nullable=True)
    bank_code = Column(String, nullable=True) 
    account_number = Column(String, nullable=True)
    account_name = Column(String, nullable=True)
    
    # International Details
    paypal_email = Column(String, nullable=True)
    
    updated_at = Column(DateTime, server_default=text('now()'), onupdate=text('now()'))
    user = relationship("User", back_populates="payment_settings")