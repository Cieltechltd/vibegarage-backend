import uuid
import re
import os
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.fanlink import FanLink
from app.models.track import Track
from app.models.user import User
from app.schemas.fanlink import FanLinkCreate, FanLinkOut, FanLinkPublicOut, FanLinkTrackOut

router = APIRouter(prefix="/fanlinks", tags=["FanLinks"])
logger = logging.getLogger("vibe-garage-fanlinks")

SUPABASE_URL = os.getenv("SUPABASE_URL")
BUCKET_NAME = "vibegarage"


def _clean_slug(raw: str) -> str:
    return re.sub(r"[^a-z0-9-_]", "", raw.lower())


def _to_out(link: FanLink) -> FanLinkOut:
    return FanLinkOut(
        id=link.id,
        slug=link.slug,
        track_id=str(link.track_id),
        streaming_links=link.streaming_links or {},
        accept_tips=link.accept_tips,
        subaccount_id=link.subaccount_id
    )


@router.post("", response_model=FanLinkOut, status_code=201)
def create_fanlink(
    payload: FanLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Only artists can create FanLinks.")

    track = db.query(Track).filter(
        Track.id == payload.track_id,
        Track.artist_id == current_user.id
    ).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found or not owned by you.")

    clean_slug = _clean_slug(payload.slug)
    if not clean_slug:
        raise HTTPException(status_code=400, detail="Invalid link handle.")

    existing = db.query(FanLink).filter(FanLink.slug == clean_slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="That link handle is already taken.")

    fanlink = FanLink(
        id=str(uuid.uuid4()),
        slug=clean_slug,
        track_id=payload.track_id,
        artist_id=current_user.id,
        streaming_links=payload.streaming_links,
        accept_tips=payload.accept_tips,
        subaccount_id=payload.subaccount_id
    )
    db.add(fanlink)
    db.commit()
    db.refresh(fanlink)

    return _to_out(fanlink)


@router.get("/mine", response_model=list[FanLinkOut])
def list_my_fanlinks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(FanLink).filter(FanLink.artist_id == current_user.id).all()
    return [_to_out(l) for l in links]


@router.get("/public/{slug}", response_model=FanLinkPublicOut)
def get_fanlink_public(slug: str, db: Session = Depends(get_db)):
    fanlink = db.query(FanLink).filter(FanLink.slug == slug).first()
    if not fanlink:
        raise HTTPException(status_code=404, detail="FanLink not found")

    track = db.query(Track).filter(Track.id == fanlink.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track for this FanLink no longer exists")

    artist = db.query(User).filter(User.id == fanlink.artist_id).first()

    return FanLinkPublicOut(
        slug=fanlink.slug,
        artist_id=fanlink.artist_id,
        artist_username=artist.username if artist else "",
        streaming_links=fanlink.streaming_links or {},
        is_tipping_enabled=fanlink.accept_tips,
        subaccount_id=fanlink.subaccount_id,
        track=FanLinkTrackOut(
            id=str(track.id),
            title=track.title,
            artist_name=(artist.stage_name or artist.username) if artist else "Unknown Artist",
            cover_url=track.cover_path,
            preview_url=track.audio_path
        )
    )


@router.get("/public/{slug}/download")
async def download_fanlink_track(slug: str, db: Session = Depends(get_db)):
   
    fanlink = db.query(FanLink).filter(FanLink.slug == slug).first()
    if not fanlink:
        raise HTTPException(status_code=404, detail="FanLink not found")

    track = db.query(Track).filter(Track.id == fanlink.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    if getattr(track, 'is_for_sale', False):
        raise HTTPException(status_code=403, detail="This track is not available for free download.")

    if not track.audio_path:
        logger.error(f"FanLink '{slug}' (track {track.id}) has no audio_path set at all.")
        raise HTTPException(status_code=500, detail="This track has no audio file on record.")

 
    audio_url = track.audio_path
    if not audio_url.startswith("http"):
        base_filename = os.path.basename(audio_url)
        audio_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/audio/{base_filename}"

    safe_title = re.sub(r'[^\w\s-]', '', track.title).strip() or "track"
    ext = os.path.splitext(audio_url)[1] or ".mp3"
    filename = f"{safe_title}{ext}"

    client = httpx.AsyncClient(timeout=60.0)
    try:
        upstream_request = client.build_request("GET", audio_url)
        upstream_response = await client.send(upstream_request, stream=True)
    except Exception as e:
        await client.aclose()
        logger.error(f"FanLink '{slug}' download failed reaching '{audio_url}': {e}")
        raise HTTPException(status_code=502, detail="Could not reach the audio file storage.")

    if upstream_response.status_code != 200:
        logger.error(
            f"FanLink '{slug}' download got status {upstream_response.status_code} "
            f"fetching '{audio_url}'"
        )
        await upstream_response.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail="Audio file could not be retrieved.")

    async def stream_and_cleanup():
        try:
            async for chunk in upstream_response.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await upstream_response.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_and_cleanup(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )