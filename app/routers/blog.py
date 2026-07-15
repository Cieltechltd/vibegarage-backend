from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.db.database import get_db
from app.models.blog import BlogPost
from app.schemas.blog import BlogPostOut, BlogPostListItem

router = APIRouter(prefix="/blog", tags=["Blog"])


def _author_name(post: BlogPost) -> str | None:
    if not post.author:
        return None
    return post.author.stage_name or post.author.username


@router.get("/", response_model=List[BlogPostListItem])
def list_published_posts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    posts = (
        db.query(BlogPost)
        .filter(BlogPost.status == "published")
        .order_by(desc(BlogPost.published_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        BlogPostListItem(
            id=p.id,
            title=p.title,
            slug=p.slug,
            excerpt=p.excerpt,
            cover_image_url=p.cover_image_url,
            author_name=_author_name(p),
            status=p.status,
            published_at=p.published_at,
            created_at=p.created_at
        )
        for p in posts
    ]


@router.get("/{slug}", response_model=BlogPostOut)
def get_post_by_slug(slug: str, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.status == "published").first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return BlogPostOut(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content_html=post.content_html,
        cover_image_url=post.cover_image_url,
        status=post.status,
        author_name=_author_name(post),
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at
    )