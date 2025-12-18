from sqlalchemy import Column, String, ForeignKey
from app.db.database import Base
import uuid

class Like(Base):
    __tablename__ = "likes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    track_id = Column(String, ForeignKey("tracks.id"))
