from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.track import Track
from app.models.like import Like
from app.models.follow import Follow
from app.models.play import Play
from app.models.user import User
from app.schemas.track import TrackPublic
from app.schemas.artist import ArtistPublic


router = APIRouter(prefix="/listener", tags=["Listener Dashboard"])

@router.get("/dashboard")
def listener_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total_likes = db.query(Like).filter(
        Like.user_id == current_user.id
    ).count()

   
    total_follows = db.query(Follow).filter(
        Follow.follower_id == current_user.id
    ).count()

    total_plays = db.query(Play).filter(
        Play.user_id == current_user.id
    ).count()

    return {
        "total_likes": total_likes,
        "total_follows": total_follows,
        "total_plays": total_plays
    }

@router.get("/recently-played")
def recently_played(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plays = (
        db.query(Play)
        .filter(Play.user_id == current_user.id)
        .order_by(Play.created_at.desc())
        .limit(20)
        .all()
    )

    tracks = [
        {
            "track_id": play.track.id,
            "title": play.track.title,
            "artist": play.track.artist.stage_name
        }
        for play in plays
    ]

    return tracks


@router.get("/likes")
def liked_tracks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    likes = (
        db.query(Like)
        .filter(Like.user_id == current_user.id)
        .all()
    )

    return [
        {
            "track_id": like.track.id,
            "title": like.track.title,
            "artist": like.track.artist.stage_name
        }
        for like in likes
    ]


@router.get("/following")
def followed_artists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    follows = (
        db.query(Follow)
        .filter(Follow.follower_id == current_user.id)
        .all()
    )

    return [
        {
            "artist_id": follow.artist.id,
            "stage_name": follow.artist.stage_name
        }
        for follow in follows
    ]


@router.get("/details")
def listener_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # liked tracks
    liked_tracks = (
        db.query(Track)
        .join(Like, Like.track_id == Track.id)
        .filter(Like.user_id == current_user.id)
        .all()
    )

    
    followed_artists = (
        db.query(User)
        .join(Follow, Follow.artist_id == User.id)
        .filter(Follow.follower_id == current_user.id)
        .all()
    )

    # recent plays
    recent_plays = (
        db.query(Play)
        .filter(Play.user_id == current_user.id)
        .order_by(Play.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "listener": {
            "id": current_user.id,
            "email": current_user.email,
        },
        "liked_tracks": [
            {
                "id": track.id,
                "title": track.title
            }
            for track in liked_tracks
        ],
        "followed_artists": [
            {
                "id": artist.id,
                "stage_name": artist.stage_name
            }
            for artist in followed_artists
        ],
        "recent_plays": [
            {
                "track_id": play.track_id,
                "played_at": play.created_at
            }
            for play in recent_plays
        ]
    }
    
    
@router.get("/profile")
def view_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "id": current_user.id,
        "email": current_user.email,
    }


@router.get("/history")
def listening_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plays = (
        db.query(Play)
        .filter(Play.user_id == current_user.id)
        .order_by(Play.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "count": len(plays),
        "results": [
            {
                "played_at": play.created_at,
                "track": TrackPublic(
                    id=play.track.id,
                    title=play.track.title,
                    play_count=play.track.play_count,
                    like_count=play.track.like_count,
                    artist=ArtistPublic(
                        id=play.track.artist.id,
                        stage_name=play.track.artist.stage_name
                    )
                )
            }
            for play in plays
        ]
    }


@router.get("/recommendations")
def recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recent_plays = (
        db.query(Play)
        .filter(Play.user_id == current_user.id)
        .order_by(Play.created_at.desc())
        .limit(20)
        .all()
    )

    artist_ids = list(
        {play.track.artist_id for play in recent_plays}
    )

    if not artist_ids:
        return {"results": []}

    tracks = (
        db.query(Track)
        .filter(Track.artist_id.in_(artist_ids))
        .limit(20)
        .all()
    )

    return {
        "count": len(tracks),
        "results": [
            TrackPublic(
                id=track.id,
                title=track.title,
                play_count=track.play_count,
                like_count=track.like_count,
                artist=ArtistPublic(
                    id=track.artist.id,
                    stage_name=track.artist.stage_name
                )
            )
            for track in tracks
        ]
    }