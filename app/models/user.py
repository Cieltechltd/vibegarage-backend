from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.security import generate_vg_id
from app.db.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    # --- CORE IDENTITY ---
    id = Column(String, primary_key=True, default=lambda: generate_vg_id("VG-U"))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    dob = Column(Date, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    stage_name = Column(String, nullable=True)
    is_artist = Column(Boolean, default=False)
    role = Column(String, default="listener")  # listener | artist | admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # --- UNIFIED ACCOUNT FIELDS ---
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    instagram_url = Column(String, nullable=True)
    twitter_url = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    language = Column(String, default="en")
    email_notifications = Column(Boolean, default=True)

    # --- MONETIZATION & BILLING ---
    monetization_eligible = Column(Boolean, default=False)  
    total_earned_vcoins = Column(Integer, default=0)
    balance_ngn = Column(Float, default=0.0)     
    vcoin_balance = Column(Float, default=0.0)      
    subscription_expiry = Column(DateTime, nullable=True)
    is_verified_artist = Column(Boolean, default=False) 
    verification_fee_paid = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    verification_amount_paid = Column(Float, nullable=True)

    # --- SECURITY ---
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    verification_code = Column(String, nullable=True)
    two_factor_secret = Column(String, nullable=True) 
    two_factor_enabled = Column(Boolean, server_default='false')
    
    # --- RELATIONSHIPS ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tracks = relationship("Track", back_populates="artist")
    likes = relationship("Like", backref="user")
    plays = relationship("Play", backref="user")
    albums = relationship("Album", back_populates="artist", overlaps="artist_albums")
    payment_settings = relationship("ArtistPaymentSettings", back_populates="user", uselist=False)
    
    followers = relationship(
        "Follow",
        foreign_keys="[Follow.artist_id]",
        backref="artist"
    )

    following = relationship(
        "Follow",
        foreign_keys="[Follow.follower_id]",
        backref="follower"
    )
