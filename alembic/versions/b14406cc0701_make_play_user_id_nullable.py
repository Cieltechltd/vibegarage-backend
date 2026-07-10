"""make play user_id nullable

Revision ID: b14406cc0701
Revises: 4f45da8611ef
Create Date: 2026-07-10 11:11:50.471201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b14406cc0701'
down_revision: Union[str, Sequence[str], None] = '4f45da8611ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alter user_id column to be nullable
    op.alter_column(
        'plays', 
        'user_id',
        existing_type=sa.VARCHAR(),
        nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert user_id column back to not nullable
    op.alter_column(
        'plays', 
        'user_id',
        existing_type=sa.VARCHAR(),
        nullable=False
    )