"""Add a Google OAuth subject to users.

Revision ID: eb1b4b3e9a11
Revises: ba77080fd6ad
Create Date: 2026-08-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "eb1b4b3e9a11"
down_revision: Union[str, Sequence[str], None] = "ba77080fd6ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "google_subject" not in columns:
        op.add_column("users", sa.Column("google_subject", sa.String(), nullable=True))
        op.create_index("ix_users_google_subject", "users", ["google_subject"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "google_subject" in columns:
        op.drop_index("ix_users_google_subject", table_name="users")
        op.drop_column("users", "google_subject")
