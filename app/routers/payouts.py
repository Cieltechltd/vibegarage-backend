import logging
import pyotp
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.payment import ArtistPaymentSettings
from app.schemas.payout import PayoutRequestCreate, PayoutResponse
from app.schemas.payment import ArtistPaymentSettingsCreate, ArtistPaymentSettingsResponse
from app.services.wallet import create_payout_request
from app.services.notifications import send_payout_notification
from app.core.security import generate_vg_id 


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vibe-garage-payouts")

router = APIRouter(prefix="/payouts", tags=["Artist Payouts & Wallet"])

@router.post("/settings", response_model=ArtistPaymentSettingsResponse)
def save_payment_settings(
    settings_in: ArtistPaymentSettingsCreate,
    x_2fa_code: Optional[str] = Header(None, alias="X-2FA-Code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save or update artist bank/PayPal details with targeted 2FA protection."""
    if not current_user.is_artist:
        raise HTTPException(status_code=403, detail="Only artists can configure payout settings")

  
    if getattr(current_user, 'two_factor_enabled', False):
        if not x_2fa_code:
            logger.warning(f"2FA check failed: Missing code for user {current_user.id}")
            raise HTTPException(
                status_code=403, 
                detail="2FA code required to modify payment settings"
            )
        
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if not totp.verify(x_2fa_code):
            logger.warning(f"2FA check failed: Invalid code for user {current_user.id}")
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    existing_settings = db.query(ArtistPaymentSettings).filter(
        ArtistPaymentSettings.user_id == current_user.id
    ).first()

    if existing_settings:
        for key, value in settings_in.dict(exclude_unset=True).items():
            setattr(existing_settings, key, value)
        db.commit()
        db.refresh(existing_settings)
        logger.info(f"Payment settings updated for artist {current_user.id}")
        return existing_settings
    
   
    new_settings = ArtistPaymentSettings(
        id=generate_vg_id("VG-P"),
        user_id=current_user.id,
        **settings_in.dict()
    )
    db.add(new_settings)
    db.commit()
    db.refresh(new_settings)
    logger.info(f"New payment settings created with ID {new_settings.id} for artist {current_user.id}")
    return new_settings

@router.post("/request", response_model=PayoutResponse)
def request_withdrawal(
    data: PayoutRequestCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Submit a request to withdraw earned funds."""
    if not getattr(current_user, 'monetization_eligible', False):
        logger.warning(f"Unauthorized withdrawal attempt by ineligible user {current_user.id}")
        raise HTTPException(
            status_code=403, 
            detail="You must reach the 10k/1k milestone before requesting payouts."
        )

    payout, error = create_payout_request(current_user.id, data.amount, db)
    
    if error:
        logger.error(f"Payout request failed for user {current_user.id}: {error}")
        raise HTTPException(status_code=400, detail=error)
    
    
    background_tasks.add_task(
        send_payout_notification,
        artist_name=current_user.stage_name or current_user.email,
        amount=data.amount
    )

    logger.info(f"Payout of {data.amount} successfully requested by user {current_user.id}")
    return payout