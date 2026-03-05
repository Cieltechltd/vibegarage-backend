from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
from typing import Optional

class PayoutStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class PayoutRequestCreate(BaseModel):
    """Schema for an artist to initiate a withdrawal."""
    amount: float = Field(..., gt=0, description="The amount of V-Coins to withdraw")
    currency: str = Field("NGN", description="The target currency for payout")
    
    @field_validator('amount')
    @classmethod
    def minimum_withdrawal(cls, v: float) -> float:
        if v < 200:
            raise ValueError('Minimum withdrawal is 200 V-Coins')
        return v

class PayoutResponse(BaseModel):
    """Schema for returning payout details to the artist."""
    id: str
    amount: float
    currency: str
    status: PayoutStatus
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: str
    amount: float
    type: str # EARNING or WITHDRAWAL
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True