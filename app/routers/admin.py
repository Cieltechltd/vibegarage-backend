import shutil
from pydantic import BaseModel
from sqlalchemy import or_, func, desc, text
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
from app.models.audit import AuditLog
from app.models.system import SystemSetting
from app.schemas.user import UserResponse 
from app.schemas.payout import PayoutResponse
from app.schemas.audit import AuditLogResponse
from app.services.audit import log_admin_action

router = APIRouter(prefix="/admin", tags=["Super Admin"])


class GlobalSettingsUpdate(BaseModel):
    maintenance_mode: bool | None = None
    disable_signups: bool | None = None
    disable_uploads: bool | None = None


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
    artists_count = db.query(func.count(User.id)).filter(User.role == "ARTIST").scalar()
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
    
    user.role = new_role
    db.commit()
    return {"message": f"User role updated to {new_role}"}

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
    payout.status = PayoutStatus.COMPLETED
    db.commit()
    return {"message": "Payout approved."}

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