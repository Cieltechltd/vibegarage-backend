from sqlalchemy import Column, String, ForeignKey
from app.db.database import Base
import uuid

class Follow(Base):
    __tablename__ = "follows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String, ForeignKey("users.id"))
    artist_id = Column(String, ForeignKey("users.id"))
