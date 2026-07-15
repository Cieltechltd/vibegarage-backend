"""add missing blog post columns

Revision ID: a3d772dea7e0
Revises: 51080dc8128e
Create Date: 2026-07-15 11:47:45.288782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d772dea7e0'
down_revision: Union[str, Sequence[str], None] = '51080dc8128e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add new columns to blog_posts
    op.add_column('blog_posts', sa.Column('excerpt', sa.String(length=500), nullable=True))
    op.add_column('blog_posts', sa.Column('content_html', sa.Text(), nullable=True))
    op.add_column('blog_posts', sa.Column('cover_image_url', sa.String(length=1000), nullable=True))
    op.add_column('blog_posts', sa.Column('status', sa.String(length=50), server_default='draft', nullable=False))
    op.add_column('blog_posts', sa.Column('author_id', sa.String(), nullable=True))
    op.add_column('blog_posts', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))
    op.add_column('blog_posts', sa.Column('published_at', sa.DateTime(), nullable=True))

    # 2. Migrate existing data from "content" to "content_html"
    op.execute("UPDATE blog_posts SET content_html = content WHERE content_html IS NULL AND content IS NOT NULL")

    # 3. Drop the old minimal "content" column
    op.drop_column('blog_posts', 'content')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the old "content" column
    op.add_column('blog_posts', sa.Column('content', sa.Text(), nullable=True))
    
    # Reverse the data migration
    op.execute("UPDATE blog_posts SET content = content_html WHERE content IS NULL AND content_html IS NOT NULL")
    
    # Drop the added columns
    op.drop_column('blog_posts', 'published_at')
    op.drop_column('blog_posts', 'updated_at')
    op.drop_column('blog_posts', 'author_id')
    op.drop_column('blog_posts', 'status')
    op.drop_column('blog_posts', 'cover_image_url')
    op.drop_column('blog_posts', 'content_html')
    op.drop_column('blog_posts', 'excerpt')