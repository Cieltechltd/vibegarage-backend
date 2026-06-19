"""add_is_published_to_albums

Revision ID: 4f45da8611ef
Revises: cff5d6d61606
Create Date: 2026-06-19 14:15:42.576389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = '4f45da8611ef'
down_revision: Union[str, Sequence[str], None] = 'cff5d6d61606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    existing_columns = [col['name'] for col in inspect_obj.get_columns('albums')]
    
    
    if 'is_published' not in existing_columns:
        op.add_column(
            'albums', 
            sa.Column('is_published', sa.Boolean(), server_default='false', nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('albums', 'is_published')