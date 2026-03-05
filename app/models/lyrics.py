from sqlalchemy import Column, String, Text, ForeignKey, Enum
import enum
from app.db.database import Base


# class LyricType(str, enum.Enum):
#     PLAIN = "PLAIN"
#     SYNCED = "SYNCED"

class Lyric(Base):
    __tablename__ = "lyrics"

    id = Column(String, primary_key=True, index=True)
    track_id = Column(String, ForeignKey("tracks.id"), unique=True)
    # lyric_type = Column(Enum(LyricType), default=LyricType.PLAIN)
    content = Column(Text, nullable=False) 