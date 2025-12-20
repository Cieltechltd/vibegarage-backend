from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.dependencies import get_current_user
from app.models.play import Play
from app.models.follow import Follow
from app.services.monetization import check_artist_eligibility

router = APIRouter(prefix="/artist", tags=["Artist Stats"])


@router.get("/monetization-status")
def monetization_status(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # total ad-based streams
    total_streams = (
        db.query(func.count(Play.id))
        .filter(
            Play.artist_id == current_user.id,
            Play.has_ad == True
        )
        .scalar()
    )

    # followers
    total_followers = (
        db.query(func.count(Follow.id))
        .filter(Follow.artist_id == current_user.id)
        .scalar()
    )

    eligible = check_artist_eligibility(
        total_streams=total_streams,
        total_followers=total_followers
    )

    return {
        "total_streams": total_streams,
        "total_followers": total_followers,
        "eligible_for_monetization": eligible
    }
