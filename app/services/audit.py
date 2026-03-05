import uuid
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_admin_action(
    db: Session, 
    admin_id: str, 
    action: str, 
    target_id: str, 
    details: dict = None
):
    log_entry = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_id,
        action=action,
        target_id=target_id,
        details=details
    )
    db.add(log_entry)
    db.commit()