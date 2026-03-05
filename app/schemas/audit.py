from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class AuditLogResponse(BaseModel):
    id: str
    admin_id: str
    action: str
    target_id: str
    details: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True