from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    stage_name = Column(String, nullable=True)
    is_artist = Column(Boolean, default=False)
    role = Column(String, default="listener")  # listener | artist | admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    
    tracks = relationship("Track", back_populates="artist")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    likes = relationship("Like", backref="user")
    plays = relationship("Play", backref="user")
    

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
