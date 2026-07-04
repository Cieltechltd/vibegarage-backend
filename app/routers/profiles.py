import io
import uuid
import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.track import Track
from app.models.play import Play
from app.models.follow import Follow 
from app.core.deps import get_current_user  

router = APIRouter(prefix="/public/artists", tags=["Discovery & Profiles"])

def find_artist_by_username(username: str, db: Session) -> User:
    clean_username = username.strip()
    artist = db.query(User).filter(User.username.ilike(clean_username)).first()

    if not artist or artist.role.upper() != "ARTIST":
        raise HTTPException(
            status_code=404, 
            detail="Artist profile not found"
        )
        
    return artist

@router.post("/artist/{identifier}/follow")
def follow_or_unfollow_artist(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    artist = db.query(User).filter(
        or_(User.id == identifier, User.username.ilike(identifier.strip())),
        User.role.ilike("artist")
    ).first()

    if not artist:
        raise HTTPException(status_code=404, detail="Artist profile not found")

    if current_user.id == artist.id:
        raise HTTPException(status_code=400, detail="You cannot follow your own profile")
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.artist_id == artist.id
    ).first()

    if existing_follow:
        db.delete(existing_follow)
        db.commit()
        return {
            "status": "unfollowed", 
            "message": f"You have unfollowed {artist.stage_name or artist.username}"
        }
    new_follow = Follow(
        follower_id=current_user.id,
        artist_id=artist.id
    )
    db.add(new_follow)
    db.commit()

    return {
        "status": "followed", 
        "message": f"You are now following {artist.stage_name or artist.username}"
    }


@router.get("/all")
def get_all_artists_public(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit
    
    artists_query = db.query(User).filter(User.role.ilike("artist"))
    
    total_count = artists_query.count()
    artists = artists_query.offset(offset).limit(limit).all()
    
    artists_list = []
    for artist in artists:
        total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(
            Track.artist_id == artist.id
        ).scalar() or 0
       
        follower_count = db.query(func.count(Follow.id)).filter(
            Follow.artist_id == artist.id
        ).scalar() or 0
        
        artists_list.append({
            "id": str(artist.id),
            "username": artist.username,
            "stage_name": artist.stage_name or artist.username,
            "avatar": getattr(artist, 'avatar', None) or getattr(artist, 'avatar_url', None),
            "is_verified": getattr(artist, 'is_verified_artist', False) or getattr(artist, 'is_verified', False),
            "bio": artist.bio or "",
            "stats": {
                "total_plays": total_plays,
                "followers": follower_count
            }
        })
        
    return {
        "total_artists": total_count,
        "page": page,
        "limit": limit,
        "artists": artists_list
    }


@router.get("/profile/{username}")
def get_artist_profile_or_preview(
    username: str, 
    request: Request, 
    json_mode: bool = Query(False, description="Set to true to get JSON response instead of HTML redirect"),
    db: Session = Depends(get_db)
):
    artist = find_artist_by_username(username, db)
    
    total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(
        Track.artist_id == artist.id
    ).scalar() or 0
    
    name = artist.stage_name or artist.username
    bio = artist.bio or f"Listen to {name} on Vibe Garage."
    avatar_url = getattr(artist, 'avatar', None) or getattr(artist, 'avatar_url', None) or ""
    profile_url = str(request.url)
    accept_header = request.headers.get("accept", "")
    
    if json_mode or "application/json" in accept_header:
        tracks = db.query(Track).filter(Track.artist_id == artist.id).all()
        return {
            "id": str(artist.id),                         
            "username": artist.username,             
            "stage_name": name,
            "avatar": avatar_url,
            "is_verified": getattr(artist, 'is_verified_artist', False) or getattr(artist, 'is_verified', False),  
            "bio": artist.bio,
            "joined_date": artist.created_at.strftime("%B %Y") if hasattr(artist, 'created_at') else None,
            "stats": {
                "total_plays": total_plays,
                "track_count": len(tracks)
            },
            "tracks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "cover_art": getattr(t, 'cover_path', getattr(t, 'cover_art', '')),
                    "duration": getattr(t, 'duration', 0.0),
                    "plays": getattr(t, 'plays', 0)
                } for t in tracks
            ]
        }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta property="og:title" content="{username} | Vibe Garage Artist" />
        <meta property="og:description" content="{bio} | {total_plays} Total Plays" />
        <meta property="og:image" content="{avatar_url}" />
        <meta property="og:url" content="{profile_url}" />
        <meta property="og:type" content="profile" />
        <meta name="twitter:card" content="summary_large_image">
        <link rel="canonical" href="{profile_url}">
        <title>{username} - Vibe Garage</title>
    </head>
    <body>
        <script>
            window.location.href = "https://vibegarage.app/artists/{artist.username}";
        </script>
        <p style="font-family: sans-serif; text-align: center; margin-top: 50px;">
            Redirecting to {username}'s profile...
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/profile/{username}/data")
def get_artist_raw_data(username: str, db: Session = Depends(get_db)):
    artist = find_artist_by_username(username, db)

    total_plays = db.query(func.coalesce(func.sum(Track.plays), 0)).filter(
        Track.artist_id == artist.id
    ).scalar() or 0

    tracks = db.query(Track).filter(Track.artist_id == artist.id).all()

    return {
        "id": str(artist.id),                         
        "username": artist.username,             
        "stage_name": artist.stage_name or artist.username,
        "avatar": getattr(artist, 'avatar', None) or getattr(artist, 'avatar_url', None),
        "is_verified": getattr(artist, 'is_verified_artist', False) or getattr(artist, 'is_verified', False),  
        "bio": artist.bio,
        "joined_date": artist.created_at.strftime("%B %Y") if hasattr(artist, 'created_at') else None,
        "stats": {
            "total_plays": total_plays,
            "track_count": len(tracks)
        },
        "tracks": [
            {
                "id": str(t.id),
                "title": t.title,
                "cover_art": getattr(t, 'cover_path', getattr(t, 'cover_art', '')),
                "duration": getattr(t, 'duration', 0.0),
                "plays": getattr(t, 'plays', 0)
            } for t in tracks
        ]
    }


@router.get("/profile/{username}/qrcode")
def get_artist_qr_code(
    username: str, 
    request: Request, 
    db: Session = Depends(get_db)
):
    artist = find_artist_by_username(username, db)
    
    base_url = str(request.base_url).rstrip("/")
    profile_url = f"{base_url}/public/artists/profile/{artist.username}"

    qr = segno.make(profile_url, error='h')
    
    out = io.BytesIO()
    qr.save(out, kind='png', scale=15, dark="#000000", light="#ffffff") 
    out.seek(0)

    return StreamingResponse(out, media_type="image/png")