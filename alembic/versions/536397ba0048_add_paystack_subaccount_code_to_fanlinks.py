"""add paystack_subaccount_code to fanlinks

Revision ID: 536397ba0048
Revises: 29d0da2d3655
Create Date: 2026-07-16 16:03:20.041453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '536397ba0048'
down_revision: Union[str, Sequence[str], None] = '29d0da2d3655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('fanlinks', sa.Column('paystack_subaccount_code', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fanlinks', 'paystack_subaccount_code')