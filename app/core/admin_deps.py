from fastapi import Depends, HTTPException, status
from app.core.deps import get_current_user
from app.models.user import User

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges. Admin role required."
        )
    return current_user

def get_current_moderator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["ADMIN", "MODERATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Moderator or Admin role required."
        )
    return current_user