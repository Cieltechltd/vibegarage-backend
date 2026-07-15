from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    excerpt = Column(String, nullable=True)
    content_html = Column(Text, nullable=False)
    cover_image_url = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft | published
    author_id = Column(String, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    author = relationship("User")