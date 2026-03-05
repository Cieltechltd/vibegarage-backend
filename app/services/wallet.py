from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.payout import PayoutRequest, PayoutStatus
from app.models.user import User
from app.services.monetization import calculate_artist_earnings
import uuid

def get_available_balance(user_id: str, db: Session) -> float:
    """
    Calculates the actual spendable balance: 
    Total Earnings - (Completed Payouts + Pending Payouts)
    """

    gross_earnings = calculate_artist_earnings(user_id, db)

    
    locked_funds = (
        db.query(func.sum(PayoutRequest.amount))
        .filter(
            PayoutRequest.user_id == user_id,
            PayoutRequest.status.in_([PayoutStatus.COMPLETED, PayoutStatus.PENDING])
        )
        .scalar() or 0.0
    )

    return float(gross_earnings - locked_funds)

def create_payout_request(user_id: str, amount: float, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    
    
    available_balance = get_available_balance(user_id, db)
    
    if amount > available_balance:
        return None, f"Insufficient funds. Your available balance is {available_balance} V-Coins."

    # Create the request
    request = PayoutRequest(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        status=PayoutStatus.PENDING
    )
    
    db.add(request)
    db.commit()
    return request, None