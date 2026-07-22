"""Add earning_entries table and paystack_recipient_code column

Revision ID: ba77080fd6ad
Revises: dc83d7c901f0
Create Date: 2026-07-22 22:47:17.786784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ba77080fd6ad'
down_revision: Union[str, Sequence[str], None] = 'dc83d7c901f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Create table only if it does NOT exist yet
    if not inspector.has_table('earning_entries'):
        op.create_table(
            'earning_entries',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('artist_id', sa.String(), nullable=False),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('gross_amount_ngn', sa.Float(), nullable=False),
            sa.Column('platform_fee_ngn', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('net_amount_ngn', sa.Float(), nullable=False),
            sa.Column('reference', sa.String(), nullable=True),
            sa.Column('track_id', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['artist_id'], ['users.id'], name=op.f('earning_entries_artist_id_fkey')),
            sa.PrimaryKeyConstraint('id', name=op.f('earning_entries_pkey'))
        )
        op.create_index(op.f('ix_earning_entries_id'), 'earning_entries', ['id'], unique=False)
        op.create_index(op.f('ix_earning_entries_artist_id'), 'earning_entries', ['artist_id'], unique=False)

    # 2. Add paystack_recipient_code column if missing
    columns = [c['name'] for c in inspector.get_columns('artist_payment_settings')]
    if 'paystack_recipient_code' not in columns:
        op.add_column(
            'artist_payment_settings', 
            sa.Column('paystack_recipient_code', sa.String(), nullable=True)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = [c['name'] for c in inspector.get_columns('artist_payment_settings')]
    if 'paystack_recipient_code' in columns:
        op.drop_column('artist_payment_settings', 'paystack_recipient_code')

    if inspector.has_table('earning_entries'):
        op.drop_index(op.f('ix_earning_entries_artist_id'), table_name='earning_entries')
        op.drop_index(op.f('ix_earning_entries_id'), table_name='earning_entries')
        op.drop_table('earning_entries')