import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from supabase import create_client, Client
from app.models.clip import GarageClip

logger = logging.getLogger("vibe-garage-clip-cleanup")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "vibegarage"

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None


def _storage_path_from_url(video_url: str) -> str | None:
    """Extracts the bucket-relative storage path (e.g. 'clips/xyz.mp4') from a public Supabase URL."""
    marker = f"/object/public/{BUCKET_NAME}/"
    if marker in video_url:
        return video_url.split(marker, 1)[1]
    return None


def delete_expired_clips(db: Session) -> int:
    expired = db.query(GarageClip).filter(GarageClip.expires_at <= datetime.utcnow()).all()

    deleted_count = 0
    for clip in expired:
        storage_path = _storage_path_from_url(clip.video_url) if clip.video_url else None

        if storage_path and supabase_client:
            try:
                supabase_client.storage.from_(BUCKET_NAME).remove([storage_path])
            except Exception as e:
                logger.error(f"Failed to delete storage file for expired clip {clip.id}: {e}")

        db.delete(clip)
        deleted_count += 1

    if deleted_count:
        db.commit()
        logger.info(f"Deleted {deleted_count} expired garage clip(s).")

    return deleted_count


def start_clip_expiry_scheduler(session_factory):
   
    from apscheduler.schedulers.background import BackgroundScheduler

    def job():
        db = session_factory()
        try:
            delete_expired_clips(db)
        finally:
            db.close()

    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", minutes=15, id="clip_expiry_cleanup", replace_existing=True)
    scheduler.start()
    return scheduler