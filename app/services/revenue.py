import logging
from sqlalchemy.orm import Session
from app.models.user import User

logger = logging.getLogger("vibe-garage-revenue")


PLATFORM_FEE_PERCENTAGE = 0.15


def apply_platform_fee_and_credit(
    db: Session,
    artist: User,
    gross_amount_ngn: float,
    source: str,
    reference: str
) -> float:
    
    platform_fee = round(gross_amount_ngn * PLATFORM_FEE_PERCENTAGE, 2)
    net_amount = round(gross_amount_ngn - platform_fee, 2)

    artist.balance_ngn = round((artist.balance_ngn or 0) + net_amount, 2)

    logger.info(
        f"[{source}] ref={reference}: gross=NGN{gross_amount_ngn:.2f}, "
        f"platform_fee=NGN{platform_fee:.2f} ({PLATFORM_FEE_PERCENTAGE:.0%}), "
        f"net_credited=NGN{net_amount:.2f} to artist {artist.id}"
    )

    return net_amount