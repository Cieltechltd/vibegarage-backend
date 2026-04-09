from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.play import Play
from app.models.follow import Follow
from app.models.track import Track
from app.models.user import User


NAIRA_PER_STREAM = 1.50

def check_and_update_eligibility(artist_id: str, db: Session) -> bool:
    
    artist = db.query(User).filter(User.id == artist_id).first()
    if not artist or artist.monetization_eligible:
        return True if artist and artist.monetization_eligible else False

    
    total_streams = (
        db.query(func.count(Play.id))
        .join(Track, Play.track_id == Track.id)
        .filter(Track.artist_id == artist_id)
        .scalar() or 0
    )

    
    total_followers = (
        db.query(func.count(Follow.id))
        .filter(Follow.artist_id == artist_id)
        .scalar() or 0
    )

    STREAM_THRESHOLD = 10000
    FOLLOWER_THRESHOLD = 1000

    if total_streams >= STREAM_THRESHOLD and total_followers >= FOLLOWER_THRESHOLD:
        artist.monetization_eligible = True
        db.commit()
        return True

    return False

def get_monetization_progress(artist_id: str, db: Session):
    """
    Returns current stats vs requirements for progress bars on the artist dashboard.
    """
    streams = (
        db.query(func.count(Play.id))
        .join(Track, Play.track_id == Track.id)
        .filter(Track.artist_id == artist_id)
        .scalar() or 0
    )
    
    followers = (
        db.query(func.count(Follow.id))
        .filter(Follow.artist_id == artist_id)
        .scalar() or 0
    )

    return {
        "current_streams": streams,
        "required_streams": 10000,
        "current_followers": followers,
        "required_followers": 1000,
        "is_eligible": streams >= 10000 and followers >= 1000
    }
    
def calculate_artist_earnings(artist_id: str, db: Session) -> float:

    monetized_plays_count = (
        db.query(func.count(Play.id))
        .join(Track, Play.track_id == Track.id)
        .filter(
            Track.artist_id == artist_id,
            Play.is_monetized_stream == True
        )
        .scalar() or 0
    )
    
    return float(monetized_plays_count * NAIRA_PER_STREAM)

def mark_artist_as_verified(db: Session, user_id: str):
    """
    Automatically flips the verification switch and 
    prepares the maroon badge for the profile.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role == "ARTIST":
        user.is_verified_artist = True
        db.commit()
        return True
    return False
    
   