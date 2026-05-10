from sqlalchemy import Column, String, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.database import Base


# class LyricType(str, enum.Enum):
#     PLAIN = "PLAIN"
#     SYNCED = "SYNCED"

class Lyric(Base):
    __tablename__ = "lyrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), unique=True)
    # lyric_type = Column(Enum(LyricType), default=LyricType.PLAIN)
    content = Column(Text, nullable=False) 