"""initial_deploy

Revision ID: 7adb32d04927
Revises: 
Create Date: 2026-03-09 12:45:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7adb32d04927'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create Users Table with ALL necessary columns
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('stage_name', sa.String(), nullable=True),
        sa.Column('is_artist', sa.Boolean(), server_default='false'),
        sa.Column('role', sa.String(), server_default='user'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('monetization_eligible', sa.Boolean(), server_default='false'),
        sa.Column('total_earned_vcoins', sa.Float(), server_default='0.0'),
        sa.Column('balance_ngn', sa.Float(), server_default='0.0'),
        sa.Column('vcoin_balance', sa.Integer(), server_default='0'),
        sa.Column('subscription_expiry', sa.DateTime(), nullable=True),
        sa.Column('is_verified_artist', sa.Boolean(), server_default='false'),
        sa.Column('verification_fee_paid', sa.Boolean(), server_default='false'),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verification_amount_paid', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('reset_token', sa.String(), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
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

def downgrade() -> None:
    op.drop_table('tracks')
    op.drop_table('albums')
    op.drop_table('users')