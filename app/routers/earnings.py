from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.earning import EarningEntry
from app.models.payout import PayoutRequest, PayoutStatus
from app.services.monetization import calculate_artist_earnings
from app.services.wallet import get_available_balance

router = APIRouter(prefix="/artist/earnings", tags=["Artist Earnings"])


@router.get("")
def get_artist_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   
    if current_user.role.lower() != "artist":
        raise HTTPException(status_code=403, detail="Artist role required.")

   
    streaming_earnings = calculate_artist_earnings(current_user.id, db)

    tips_total = db.query(func.coalesce(func.sum(EarningEntry.net_amount_ngn), 0.0)).filter(
        EarningEntry.artist_id == current_user.id,
        EarningEntry.source == "tip"
    ).scalar()

    sales_total = db.query(func.coalesce(func.sum(EarningEntry.net_amount_ngn), 0.0)).filter(
        EarningEntry.artist_id == current_user.id,
        EarningEntry.source == "track_sale"
    ).scalar()

    total_lifetime_earnings = streaming_earnings + tips_total + sales_total

    completed_payouts = db.query(func.coalesce(func.sum(PayoutRequest.amount), 0.0)).filter(
        PayoutRequest.user_id == current_user.id,
        PayoutRequest.status == PayoutStatus.COMPLETED
    ).scalar()

    pending_payouts = db.query(func.coalesce(func.sum(PayoutRequest.amount), 0.0)).filter(
        PayoutRequest.user_id == current_user.id,
        PayoutRequest.status == PayoutStatus.PENDING
    ).scalar()

    recent_entries = (
        db.query(EarningEntry)
        .filter(EarningEntry.artist_id == current_user.id)
        .order_by(desc(EarningEntry.created_at))
        .limit(20)
        .all()
    )

    return {
        "available_balance_ngn": round(get_available_balance(current_user.id, db), 2),
        "total_lifetime_earnings_ngn": round(total_lifetime_earnings, 2),
        "breakdown": {
            "streaming_ngn": round(streaming_earnings, 2),
            "tips_ngn": round(tips_total, 2),
            "track_sales_ngn": round(sales_total, 2)
        },
        "payouts": {
            "completed_ngn": round(completed_payouts, 2),
            "pending_ngn": round(pending_payouts, 2)
        },
        "recent_activity": [
            {
                "id": e.id,
                "source": e.source,
                "gross_amount_ngn": e.gross_amount_ngn,
                "platform_fee_ngn": e.platform_fee_ngn,
                "net_amount_ngn": e.net_amount_ngn,
                "track_id": e.track_id,
                "created_at": e.created_at
            }
            for e in recent_entries
        ]
    }