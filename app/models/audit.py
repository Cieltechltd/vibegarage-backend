from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from app.db.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    admin_id = Column(String, index=True)
    action = Column(String)              
    target_id = Column(String)           
    details = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)