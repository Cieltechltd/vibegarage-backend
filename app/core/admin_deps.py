from fastapi import Depends, HTTPException, status
from app.core.deps import get_current_user
from app.models.user import User
import os


MASTER_ADMIN = os.getenv("MASTER_ADMIN_EMAIL")

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    
    is_admin = current_user.role == "admin" or current_user.email == MASTER_ADMIN

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access only."
        )

    if not getattr(current_user, "two_factor_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA is required for admin accounts. Complete setup at /auth/2fa/setup and /auth/2fa/enable before continuing.",
            headers={"X-2FA-Setup-Required": "true"}
        )

    return current_user

def get_current_moderator(current_user: User = Depends(get_current_user)) -> User:
    
    
    if current_user.role.lower() not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Moderator or Admin role required."
        )
    return current_user