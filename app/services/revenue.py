import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.user import User
from app.models.earning import EarningEntry
from app.models.payout import PayoutRequest, PayoutStatus

logger = logging.getLogger("vibe-garage-revenue")


PLATFORM_FEE_PERCENTAGE = 0.15


def apply_platform_fee_and_credit(
    db: Session,
    artist: User,
    gross_amount_ngn: float,
    source: str,
    reference: str,
    track_id: str = None
) -> float:
    
    platform_fee = round(gross_amount_ngn * PLATFORM_FEE_PERCENTAGE, 2)
    net_amount = round(gross_amount_ngn - platform_fee, 2)

    artist.balance_ngn = round((artist.balance_ngn or 0) + net_amount, 2)

    entry = EarningEntry(
        id=str(uuid.uuid4()),
        artist_id=artist.id,
        source=source,
        gross_amount_ngn=gross_amount_ngn,
        platform_fee_ngn=platform_fee,
        net_amount_ngn=net_amount,
        reference=reference,
        track_id=track_id
    )
    db.add(entry)

    logger.info(
        f"[{source}] ref={reference}: gross=NGN{gross_amount_ngn:.2f}, "
        f"platform_fee=NGN{platform_fee:.2f} ({PLATFORM_FEE_PERCENTAGE:.0%}), "
        f"net_credited=NGN{net_amount:.2f} to artist {artist.id}"
    )

    return net_amount


def get_earnings_summary(artist_id: str, db: Session) -> dict:
    from app.services.monetization import calculate_artist_earnings
    from app.services.wallet import get_available_balance

    streaming_earnings = calculate_artist_earnings(artist_id, db)

    tips_total = db.query(func.coalesce(func.sum(EarningEntry.net_amount_ngn), 0.0)).filter(
        EarningEntry.artist_id == artist_id,
        EarningEntry.source == "tip"
    ).scalar()

    sales_total = db.query(func.coalesce(func.sum(EarningEntry.net_amount_ngn), 0.0)).filter(
        EarningEntry.artist_id == artist_id,
        EarningEntry.source == "track_sale"
    ).scalar()

    total_lifetime_earnings = streaming_earnings + tips_total + sales_total

    completed_payouts = db.query(func.coalesce(func.sum(PayoutRequest.amount), 0.0)).filter(
        PayoutRequest.user_id == artist_id,
        PayoutRequest.status == PayoutStatus.COMPLETED
    ).scalar()

    pending_payouts = db.query(func.coalesce(func.sum(PayoutRequest.amount), 0.0)).filter(
        PayoutRequest.user_id == artist_id,
        PayoutRequest.status == PayoutStatus.PENDING
    ).scalar()

    recent_entries = (
        db.query(EarningEntry)
        .filter(EarningEntry.artist_id == artist_id)
        .order_by(desc(EarningEntry.created_at))
        .limit(20)
        .all()
    )

    return {
        "available_balance_ngn": round(get_available_balance(artist_id, db), 2),
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