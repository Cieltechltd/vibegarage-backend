from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.security import generate_vg_id
from app.db.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: generate_vg_id("VG-U"))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    stage_name = Column(String, nullable=True)
    is_artist = Column(Boolean, default=False)
    role = Column(String, default="listener")  # listener | artist | admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    monetization_eligible = Column(Boolean, default=False)  
    total_earned_vcoins = Column(Integer, default=0)
    balance_ngn = Column(Float, default=0.0)      # Used by Artists (Real Money)
    vcoin_balance = Column(Float, default=0.0)      # Used by Listeners (V-Coins)
    subscription_expiry = Column(DateTime, nullable=True)
    is_verified_artist = Column(Boolean, default=False)
    verification_fee_paid = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    verification_amount_paid = Column(Float, nullable=True)

    tracks = relationship("Track", back_populates="artist")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    likes = relationship("Like", backref="user")
    plays = relationship("Play", backref="user")
    albums = relationship("Album", back_populates="artist", overlaps="artist_albums")
    payment_settings = relationship("ArtistPaymentSettings", back_populates="user", uselist=False)
    
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    verification_code = Column(String, nullable=True)
    two_factor_secret = Column(String, nullable=True) 
    two_factor_enabled = Column(Boolean, server_default='false')
    

    followers = relationship(
    "Follow",
    foreign_keys="[Follow.artist_id]",
    backref="artist")

    following = relationship(
    "Follow",
    foreign_keys="[Follow.follower_id]",
    backref="follower")
