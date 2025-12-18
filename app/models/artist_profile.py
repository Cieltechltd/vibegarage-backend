
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class ArtistProfile(Base):
    __tablename__ = "artist_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    stage_name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    avatar = Column(String, nullable=True)  # image path or URL

    user = relationship("User", backref="artist_profile")
