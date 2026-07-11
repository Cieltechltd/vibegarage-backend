import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User

logger = logging.getLogger("vibe-garage-subscription-cleanup")


def revoke_expired_verifications(db: Session) -> int:
    now = datetime.utcnow()
    expired_users = db.query(User).filter(
        User.is_verified_artist == True,
        User.subscription_expiry.isnot(None),
        User.subscription_expiry <= now
    ).all()

    for user in expired_users:
        user.is_verified_artist = False

    if expired_users:
        db.commit()
        logger.info(f"Revoked verification for {len(expired_users)} expired subscription(s).")

    return len(expired_users)


def start_subscription_expiry_scheduler(session_factory):
    from apscheduler.schedulers.background import BackgroundScheduler

    def job():
        db = session_factory()
        try:
            revoke_expired_verifications(db)
        finally:
            db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", hours=1, id="subscription_expiry_cleanup", replace_existing=True)
    scheduler.start()
    return scheduler