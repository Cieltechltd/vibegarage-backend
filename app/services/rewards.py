from sqlalchemy.orm import Session
from app.models.user import User

VCOIN_REWARD_SHARE = 5.0
VCOIN_REWARD_COMMENT = 2.0

def reward_listener_activity(user: User, activity_type: str, db: Session):
    """
    Adds V-Coins to a listener's balance IF they are verified.
    V-Coins cannot be converted to cash.
    """
    if not user.is_verified:
        return 
    if activity_type == "SHARE":
        user.vcoin_balance += VCOIN_REWARD_SHARE
    elif activity_type == "COMMENT":
        user.vcoin_balance += VCOIN_REWARD_COMMENT
    
    db.commit()