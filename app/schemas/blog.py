from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlogPostCreate(BaseModel):
    title: str
    content_html: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    content_html: Optional[str] = None
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None


class BlogPostListItem(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    author_name: Optional[str] = None
    status: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class BlogPostOut(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    content_html: str
    cover_image_url: Optional[str] = None
    status: str
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None