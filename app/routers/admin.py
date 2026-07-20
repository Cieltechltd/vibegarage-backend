import shutil
import logging
import uuid
import os
import re
import bleach
from pydantic import BaseModel
from sqlalchemy import or_, func, desc, text
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from supabase import create_client, Client
from app.db.deps import get_db
from app.core.admin_deps import get_current_admin
from app.core.config import settings
from app.models.system import SystemSetting
from app.models.user import User
from app.models.track import Track
from app.models.lyrics import Lyric
from app.models.clip import GarageClip
from app.models.play import Play
from app.models.payout import PayoutRequest, PayoutStatus
from app.models.payment import ArtistPaymentSettings
from app.models.audit import AuditLog
from app.models.blog import BlogPost
from app.schemas.user import UserResponse 
from app.schemas.payout import PayoutResponse
from app.schemas.audit import AuditLogResponse
from app.schemas.blog import BlogPostCreate, BlogPostUpdate, BlogPostOut, BlogPostListItem
from app.services.audit import log_admin_action
from app.services.clip_cleanup import _storage_path_from_url, supabase_client as clip_supabase_client, BUCKET_NAME as CLIP_BUCKET_NAME
from app.services.email_broadcast import send_broadcast_email
from app.services.paystack import create_transfer_recipient, initiate_transfer

router = APIRouter(prefix="/admin", tags=["Super Admin"])
logger = logging.getLogger("vibe-garage-admin")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
blog_supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
BLOG_BUCKET_NAME = "vibegarage"


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "post"



ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "h1", "h2", "h3",
    "ul", "ol", "li", "a", "img", "blockquote", "code", "pre"
]
ALLOWED_ATTRS = {"a": ["href", "target", "rel"], "img": ["src", "alt"]}


def sanitize_html(raw_html: str) -> str:
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _author_name(post: BlogPost) -> str | None:
    if not post.author:
        return None
    return post.author.stage_name or post.author.username


def _serialize_post(post: BlogPost) -> BlogPostOut:
    return BlogPostOut(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content_html=post.content_html,
        cover_image_url=post.cover_image_url,
        status=post.status,
        author_name=_author_name(post),
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at
    )


class GlobalSettingsUpdate(BaseModel):
    maintenance_mode: bool | None = None
    disable_signups: bool | None = None
    disable_uploads: bool | None = None


class BroadcastEmailRequest(BaseModel):
    subject: str
    html_body: str
    target: str = "all"  # "all" | "artists" | "listeners"


PLATFORM_CONFIG = {
    "maintenance_mode": False,
    "disable_signups": False,
    "disable_uploads": False
}


@router.get("/dashboard/health")
def get_system_health(
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Monitors database connectivity and server storage status."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    total, used, free = shutil.disk_usage("/")
    
    return {
        "database": {
            "status": db_status,
            "engine": db.bind.dialect.name if db.bind else "unknown"
        },
        "storage": {
            "total_gb": round(total / (2**30), 2),
            "used_gb": round(used / (2**30), 2),
            "free_gb": round(free / (2**30), 2),
            "percent_full": round((used / total) * 100, 2)
        },
        "environment": {
            "mode": "production" if not settings.DEBUG else "development",
            "server_time": datetime.utcnow()
        }
    }

@router.get("/dashboard/summary")
def get_dashboard_metrics(
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Provides a high-level snapshot of platform health."""
    total_users = db.query(func.count(User.id)).scalar()
    artists_count = db.query(func.count(User.id)).filter(User.role.ilike("artist")).scalar()
    total_tracks = db.query(func.count(Track.id)).scalar()
    total_plays = db.query(func.count(Play.id)).scalar()
    last_week = datetime.utcnow() - timedelta(days=7)
    recent_signups = db.query(func.count(User.id)).filter(User.created_at >= last_week).scalar()

    pending_payouts = db.query(func.sum(PayoutRequest.amount)).filter(
        PayoutRequest.status == PayoutStatus.PENDING
    ).scalar() or 0
    
    completed_payouts = db.query(func.sum(PayoutRequest.amount)).filter(
        PayoutRequest.status == PayoutStatus.COMPLETED
    ).scalar() or 0

    return {
        "overview": {
            "total_users": total_users,
            "artists": artists_count,
            "tracks": total_tracks,
            "total_streams": total_plays
        },
        "performance": {
            "weekly_growth": recent_signups,
            "avg_plays_per_track": round(total_plays / total_tracks, 2) if total_tracks > 0 else 0
        },
        "finance": {
            "pending_obligations": pending_payouts,
            "total_payouts_processed": completed_payouts
        }
    }

@router.get("/dashboard/recent-activity")
def get_recent_system_activity(
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Aggregates latest signups and track uploads for the dashboard feed."""
    recent_users = db.query(User).order_by(desc(User.created_at)).limit(5).all()
    recent_tracks = db.query(Track).order_by(desc(Track.id)).limit(5).all() 
    
    return {
        "new_users": [{"email": u.email, "role": u.role, "date": u.created_at} for u in recent_users],
        "new_uploads": [{"title": t.title, "artist_id": t.artist_id} for t in recent_tracks]
    }

@router.get("/users", response_model=list[UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return db.query(User).all()

@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    new_role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    normalized_role = new_role.strip().lower()
    if normalized_role not in ("listener", "artist", "admin"):
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Must be one of: listener, artist, admin."
        )

    user.role = normalized_role
    db.commit()
    return {"message": f"User role updated to {normalized_role}"}

@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: str, 
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    
    log_admin_action(
        db, 
        admin_id=admin.id, 
        action="SUSPEND_USER", 
        target_id=user_id,
        details={"email": user.email}
    )
    
    db.commit()
    return {"message": f"User {user.email} has been suspended."}

@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: str, 
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True

    log_admin_action(
        db,
        admin_id=admin.id,
        action="REACTIVATE_USER",
        target_id=user_id,
        details={"email": user.email}
    )

    db.commit()
    return {"message": f"User {user.email} has been reactivated."}



@router.delete("/tracks/{track_id}")
def delete_track_as_admin(
    track_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    db.delete(track)
    db.commit()
    return {"message": "Track successfully removed by Admin"}

@router.get("/lyrics/all")
def list_all_lyrics(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(Lyric).all()

@router.delete("/lyrics/{lyric_id}")
def delete_lyric_as_admin(lyric_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    lyric = db.query(Lyric).filter(Lyric.id == lyric_id).first()
    if not lyric:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    
    log_admin_action(db, admin_id=admin.id, action="DELETE_LYRIC", target_id=lyric_id, details={"track_id": lyric.track_id})
    db.delete(lyric)
    db.commit()
    return {"message": "Lyrics removed."}

@router.get("/clips/all")
def list_all_garage_clips(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(GarageClip).all()

@router.delete("/clips/{clip_id}")
def delete_clip_as_admin(clip_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    clip = db.query(GarageClip).filter(GarageClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    
    storage_path = _storage_path_from_url(clip.video_url) if clip.video_url else None
    if storage_path and clip_supabase_client:
        try:
            clip_supabase_client.storage.from_(CLIP_BUCKET_NAME).remove([storage_path])
        except Exception as e:
            logger.error(f"Failed to delete storage file for clip {clip_id} during admin deletion: {e}")

    log_admin_action(db, admin_id=admin.id, action="DELETE_CLIP", target_id=clip_id, details={"artist_id": clip.artist_id})
    db.delete(clip)
    db.commit()
    return {"message": "Garage Clip removed."}



@router.get("/payouts/pending", response_model=list[PayoutResponse])
def list_pending_payouts(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(PayoutRequest).filter(PayoutRequest.status == PayoutStatus.PENDING).all()

@router.post("/payouts/{payout_id}/approve")
def approve_payout(payout_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
   
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout or payout.status != PayoutStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invalid payout request")

    settings_row = db.query(ArtistPaymentSettings).filter(
        ArtistPaymentSettings.user_id == payout.user_id
    ).first()

    if not settings_row or settings_row.preferred_method != "bank":
        raise HTTPException(
            status_code=400,
            detail="This artist has no bank payout method configured."
        )

    if not (settings_row.bank_code and settings_row.account_number and settings_row.account_name):
        raise HTTPException(
            status_code=400,
            detail="This artist's bank details are incomplete (missing bank code, account number, or account name)."
        )


    recipient_code = settings_row.paystack_recipient_code
    if not recipient_code:
        recipient_response = create_transfer_recipient(
            name=settings_row.account_name,
            account_number=settings_row.account_number,
            bank_code=settings_row.bank_code
        )
        if not recipient_response.get("status"):
            logger.error(f"Failed to create Paystack transfer recipient for payout {payout_id}: {recipient_response}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not register this artist's bank account with Paystack: {recipient_response.get('message', 'Unknown error')}"
            )
        recipient_code = recipient_response["data"]["recipient_code"]
        settings_row.paystack_recipient_code = recipient_code
        db.commit()

    transfer_reference = f"VG-PAYOUT-{uuid.uuid4().hex[:10].upper()}"
    transfer_response = initiate_transfer(
        amount_ngn=payout.amount,
        recipient_code=recipient_code,
        reason=f"VibeGarage payout for {payout.user_id}",
        reference=transfer_reference
    )

    if not transfer_response.get("status"):
        logger.error(f"Payout {payout_id} transfer request failed: {transfer_response}")
        raise HTTPException(
            status_code=502,
            detail=f"Paystack transfer failed: {transfer_response.get('message', 'Unknown error')}"
        )

    transfer_status = transfer_response.get("data", {}).get("status")

    if transfer_status == "success":
        payout.status = PayoutStatus.COMPLETED
        log_admin_action(
            db, admin_id=admin.id, action="APPROVE_PAYOUT", target_id=payout_id,
            details={"amount": payout.amount, "transfer_reference": transfer_reference, "recipient_code": recipient_code}
        )
        db.commit()
        return {"message": "Payout approved and transfer completed.", "transfer_reference": transfer_reference}

    if transfer_status == "otp":
        logger.warning(
            f"Payout {payout_id} transfer requires OTP finalization in the Paystack "
            f"dashboard (reference {transfer_reference})."
        )
        return {
            "message": (
                "Transfer initiated but requires OTP confirmation in your Paystack dashboard "
                "before it completes. This payout remains pending here until you finish it there."
            ),
            "status": "otp_required",
            "transfer_reference": transfer_reference
        }

    logger.error(f"Payout {payout_id} transfer returned unexpected status '{transfer_status}': {transfer_response}")
    raise HTTPException(status_code=502, detail=f"Transfer returned an unexpected status: {transfer_status}")

@router.post("/payouts/{payout_id}/reject")
def reject_payout(payout_id: str, reason: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    payout.status = PayoutStatus.REJECTED
    db.commit()
    return {"message": f"Payout rejected: {reason}"}



@router.get("/stats/summary")
def get_platform_summary(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = db.query(func.count(User.id)).scalar()
    total_tracks = db.query(func.count(Track.id)).scalar()
    total_streams = db.query(func.count(Play.id)).scalar()
    
    payout_stats = db.query(
        func.sum(PayoutRequest.amount).label("total_requested"),
        func.count(PayoutRequest.id).label("request_count")
    ).filter(PayoutRequest.status == PayoutStatus.PENDING).first()

    return {
        "platform_metrics": {"total_users": total_users, "total_tracks": total_tracks, "total_streams": total_streams},
        "financial_metrics": {"pending_amount": payout_stats.total_requested or 0, "request_count": payout_stats.request_count or 0}
    }

@router.get("/search/users")
def admin_search_users(query: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(User).filter(or_(User.email.ilike(f"%{query}%"), User.stage_name.ilike(f"%{query}%"))).all()

@router.get("/logs", response_model=list[AuditLogResponse])
def get_admin_audit_logs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/settings")
def get_platform_settings(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
   
    settings = db.query(SystemSetting).all()
    return {s.key: s.value for s in settings}

@router.patch("/settings")
def update_platform_settings(
    updates: GlobalSettingsUpdate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
   
    for key, value in updates.dict(exclude_unset=True).items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            new_setting = SystemSetting(key=key, value=value)
            db.add(new_setting)
    
    db.commit()
    return {"message": "Settings saved to database"}

def is_feature_enabled(db: Session, key: str) -> bool:
    """Check if a specific platform feature is disabled via the database."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else False


@router.post("/broadcast-email")
def broadcast_email(
    payload: BroadcastEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
   
    query = db.query(User.email).filter(User.is_active == True)

    if payload.target == "artists":
        query = query.filter(User.role.ilike("artist"))
    elif payload.target == "listeners":
        query = query.filter(User.role.ilike("listener"))
    elif payload.target != "all":
        raise HTTPException(
            status_code=400,
            detail="Invalid target. Must be one of: all, artists, listeners."
        )

    recipient_emails = [row[0] for row in query.all() if row[0]]

    if not recipient_emails:
        raise HTTPException(status_code=400, detail="No matching recipients found.")

    background_tasks.add_task(send_broadcast_email, payload.subject, payload.html_body, recipient_emails)

    log_admin_action(
        db,
        admin_id=admin.id,
        action="BROADCAST_EMAIL",
        target_id=payload.target,
        details={"subject": payload.subject, "recipient_count": len(recipient_emails)}
    )
    db.commit()

    return {
        "message": f"Broadcast queued for {len(recipient_emails)} recipient(s).",
        "recipient_count": len(recipient_emails)
    }


@router.get("/blog", response_model=list[BlogPostListItem])
def admin_list_all_posts(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Lists every post regardless of status -- drafts included -- for the admin management view."""
    posts = db.query(BlogPost).order_by(desc(BlogPost.created_at)).all()
    return [
        BlogPostListItem(
            id=p.id,
            title=p.title,
            slug=p.slug,
            excerpt=p.excerpt,
            cover_image_url=p.cover_image_url,
            author_name=_author_name(p),
            status=p.status,
            published_at=p.published_at,
            created_at=p.created_at
        )
        for p in posts
    ]


@router.get("/blog/{post_id}", response_model=BlogPostOut)
def admin_get_post(post_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialize_post(post)


@router.post("/blog", response_model=BlogPostOut, status_code=201)
def create_blog_post(
    payload: BlogPostCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Creates a new post as a draft. Use /admin/blog/{post_id}/publish to make it public."""
    base_slug = slugify(payload.title)
    slug = base_slug
    counter = 2
    while db.query(BlogPost).filter(BlogPost.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    post = BlogPost(
        id=str(uuid.uuid4()),
        title=payload.title,
        slug=slug,
        excerpt=payload.excerpt,
        content_html=sanitize_html(payload.content_html),
        cover_image_url=payload.cover_image_url,
        status="draft",
        author_id=admin.id
    )
    db.add(post)
    log_admin_action(db, admin_id=admin.id, action="CREATE_BLOG_POST", target_id=post.id, details={"title": payload.title})
    db.commit()
    db.refresh(post)
    return _serialize_post(post)


@router.put("/blog/{post_id}", response_model=BlogPostOut)
def update_blog_post(
    post_id: str,
    payload: BlogPostUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if payload.title is not None:
        post.title = payload.title
    if payload.content_html is not None:
        post.content_html = sanitize_html(payload.content_html)
    if payload.excerpt is not None:
        post.excerpt = payload.excerpt
    if payload.cover_image_url is not None:
        post.cover_image_url = payload.cover_image_url

    log_admin_action(db, admin_id=admin.id, action="UPDATE_BLOG_POST", target_id=post_id, details={"title": post.title})
    db.commit()
    db.refresh(post)
    return _serialize_post(post)


@router.post("/blog/{post_id}/publish")
def publish_blog_post(post_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "published"
    post.published_at = datetime.utcnow()
    log_admin_action(db, admin_id=admin.id, action="PUBLISH_BLOG_POST", target_id=post_id, details={"title": post.title})
    db.commit()
    return {"message": f"'{post.title}' is now published."}


@router.post("/blog/{post_id}/unpublish")
def unpublish_blog_post(post_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = "draft"
    log_admin_action(db, admin_id=admin.id, action="UNPUBLISH_BLOG_POST", target_id=post_id, details={"title": post.title})
    db.commit()
    return {"message": f"'{post.title}' moved back to draft."}


@router.delete("/blog/{post_id}")
def delete_blog_post(post_id: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    log_admin_action(db, admin_id=admin.id, action="DELETE_BLOG_POST", target_id=post_id, details={"title": post.title})
    db.delete(post)
    db.commit()
    return {"message": "Post deleted."}


@router.post("/blog/upload-image")
async def upload_blog_image(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin)
):
    """
    Uploads an image (cover image or one embedded inline in the rich text
    body) to Supabase storage and returns its public URL. The admin console
    calls this both for the cover-image picker and for the rich text
    editor's "insert image" button.
    """
    if not blog_supabase_client:
        raise HTTPException(status_code=500, detail="Cloud storage service credentials are not configured.")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        filename = f"blog/{uuid.uuid4()}{ext}"
        data = await file.read()

        blog_supabase_client.storage.from_(BLOG_BUCKET_NAME).upload(
            path=filename,
            file=data,
            file_options={"content-type": file.content_type}
        )
        url = f"{SUPABASE_URL}/storage/v1/object/public/{BLOG_BUCKET_NAME}/{filename}"
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")