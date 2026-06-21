import io
import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.user import User
from app.models.track import Track
from app.models.play import Play

router = APIRouter(prefix="/public/artists", tags=["Discovery & Profiles"])

def find_artist_by_username(username: str, db: Session) -> User:
    clean_username = username.strip()
    artist = db.query(User).filter(User.username == clean_username).first()

    if not artist or artist.role != "ARTIST":
        raise HTTPException(
            status_code=404, 
            detail="Artist profile not found"
        )
        
    return artist

@router.get("/profile/{username}", response_class=HTMLResponse)
def get_artist_profile_or_preview(
    username: str, 
    request: Request, 
    db: Session = Depends(get_db)
):
    artist = find_artist_by_username(username, db)
    
    total_streams = db.query(func.count(Play.id)).join(Track).filter(
        Track.artist_id == artist.id
    ).scalar() or 0
    
    name = artist.stage_name or artist.username
    bio = artist.bio or f"Listen to {name} on Vibe Garage."
    avatar_url = artist.avatar_url or "https://vibegarage.app/static/default-avatar.png"
    profile_url = str(request.url)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta property="og:title" content="{username} | Vibe Garage Artist" />
        <meta property="og:description" content="{bio} | {total_streams} Total Streams" />
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

    total_streams = db.query(func.count(Play.id)).join(Track).filter(
        Track.artist_id == artist.id
    ).scalar() or 0

    tracks = db.query(Track).filter(Track.artist_id == artist.id).all()

    return {
        "id": artist.id,                         
        "username": artist.username,             
        "stage_name": artist.stage_name or artist.username,
        "avatar": artist.avatar_url or "https://vibegarage.app/static/default-avatar.png",
        "is_verified": artist.is_verified,  
        "bio": artist.bio,
        "joined_date": artist.created_at.strftime("%B %Y") if hasattr(artist, 'created_at') else None,
        "stats": {
            "total_streams": total_streams,
            "track_count": len(tracks)
        },
        "tracks": [
            {
                "id": t.id,
                "title": t.title,
                "cover_art": t.cover_art,
                "duration": t.duration
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