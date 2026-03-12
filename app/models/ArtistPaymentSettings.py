from sqlalchemy import Column, String, ForeignKey, Enum
from app.db.database import Base
import enum

class PaymentMethod(enum.Enum):
    BANK = "bank"      # For Nigeria (NGN)
    PAYPAL = "paypal"  # For International (USD)

class ArtistPaymentSettings(Base):
    __tablename__ = "artist_payment_settings"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    preferred_method = Column(Enum(PaymentMethod), default=PaymentMethod.BANK)
    
    # Nigeria Bank Details
    bank_name = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    account_name = Column(String, nullable=True)
    
    # International Details
    paypal_email = Column(String, nullable=True)