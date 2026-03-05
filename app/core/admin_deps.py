from fastapi import Depends, HTTPException, status
from app.core.deps import get_current_user
from app.models.user import User
import os

# Loaded from your .env file
MASTER_ADMIN = os.getenv("MASTER_ADMIN_EMAIL")

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifies if the user is an admin.
    Checks the 'role' column or if the email matches the MASTER_ADMIN_EMAIL in .env.
    """
    # Updated to check .role == "admin" since .is_admin does not exist in your model
    if current_user.role == "admin" or current_user.email == MASTER_ADMIN:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access only."
    )

def get_current_moderator(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifies if the user is a Moderator or an Admin.
    Note: Case-sensitivity should match how you store roles (e.g., 'admin' vs 'ADMIN').
    """
    # Standardizing to lowercase 'admin' to match your init_db.py logic
    if current_user.role.lower() not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Moderator or Admin role required."
        )
    return current_user