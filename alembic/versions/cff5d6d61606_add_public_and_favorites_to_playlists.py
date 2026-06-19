"""add_public_and_favorites_to_playlists

Revision ID: cff5d6d61606
Revises: 079c2e783e57
Create Date: 2026-06-19 13:34:44.429277

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = 'cff5d6d61606'
down_revision: Union[str, Sequence[str], None] = '079c2e783e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    existing_columns = [col['name'] for col in inspect_obj.get_columns('playlists')]
    
    
    if 'is_public' not in existing_columns:
        op.add_column('playlists', sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False))
        
    if 'is_favorites' not in existing_columns:
        op.add_column('playlists', sa.Column('is_favorites', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('playlists', 'is_favorites')
    op.drop_column('playlists', 'is_public')