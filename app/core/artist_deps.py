from fastapi import HTTPException, status, Depends
from app.core.deps import get_current_user
from app.models.user import User

def verified_artist_required(current_user: User = Depends(get_current_user)):
    """
    Ensures the artist has paid their fee and is verified 
    before allowing access to premium features.
    """
    if not current_user.is_verified_artist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature is for Verified Artists only. Please pay the one-time verification fee."
        )
    return current_user