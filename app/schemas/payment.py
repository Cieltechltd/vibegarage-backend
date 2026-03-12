from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class ArtistPaymentSettingsBase(BaseModel):
    preferred_method: str = Field(..., pattern="^(bank|paypal)$")
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    paypal_email: Optional[EmailStr] = None

class ArtistPaymentSettingsCreate(ArtistPaymentSettingsBase):
    pass

class ArtistPaymentSettingsUpdate(BaseModel):
    preferred_method: Optional[str] = Field(None, pattern="^(bank|paypal)$")
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    paypal_email: Optional[EmailStr] = None

class ArtistPaymentSettingsResponse(ArtistPaymentSettingsBase):
    id: str
    user_id: str
    updated_at: datetime

    class Config:
        from_attributes = True