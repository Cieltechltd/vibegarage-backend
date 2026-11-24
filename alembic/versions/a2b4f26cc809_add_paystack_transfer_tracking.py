"""add Paystack transfer tracking to payouts

Revision ID: a2b4f26cc809
Revises: eb1b4b3e9a11
Create Date: 2026-11-24 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b4f26cc809"
down_revision: Union[str, Sequence[str], None] = "eb1b4b3e9a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("payout_requests"):
        return

    columns = {column["name"] for column in inspector.get_columns("payout_requests")}
    if "transfer_reference" not in columns:
        op.add_column("payout_requests", sa.Column("transfer_reference", sa.String(), nullable=True))
    if "transfer_status" not in columns:
        op.add_column("payout_requests", sa.Column("transfer_status", sa.String(), nullable=True))

    index_names = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("payout_requests")}
    if "ix_payout_requests_transfer_reference" not in index_names:
        op.create_index(
            op.f("ix_payout_requests_transfer_reference"),
            "payout_requests",
            ["transfer_reference"],
            unique=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("payout_requests"):
        return

    index_names = {index["name"] for index in inspector.get_indexes("payout_requests")}
    if "ix_payout_requests_transfer_reference" in index_names:
        op.drop_index(op.f("ix_payout_requests_transfer_reference"), table_name="payout_requests")

    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("payout_requests")}
    if "transfer_status" in columns:
        op.drop_column("payout_requests", "transfer_status")
    if "transfer_reference" in columns:
        op.drop_column("payout_requests", "transfer_reference")
