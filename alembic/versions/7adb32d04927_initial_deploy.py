"""initial_deploy

Revision ID: 7adb32d04927
Revises: 
Create Date: 2026-03-09 11:57:42.107885

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7adb32d04927'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create Users Table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_artist', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # 2. Create Albums Table
    op.create_table('albums',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('artist_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['artist_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create Tracks Table
    op.create_table('tracks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('album_id', sa.String(), nullable=True),
        sa.Column('artist_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['album_id'], ['albums.id'], ),
        sa.ForeignKeyConstraint(['artist_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Create Interaction Tables (Likes, Plays, Follows)
    op.create_table('likes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id')),
        sa.Column('track_id', sa.String(), sa.ForeignKey('tracks.id')),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('likes')
    op.drop_table('tracks')
    op.drop_table('albums')
    op.drop_table('users')
