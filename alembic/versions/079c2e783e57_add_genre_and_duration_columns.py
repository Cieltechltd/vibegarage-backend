"""add_genre_and_duration_columns

Revision ID: 079c2e783e57
Revises: 59b6232b15b2
Create Date: 2026-05-16 14:14:09.711083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '079c2e783e57'
down_revision: Union[str, Sequence[str], None] = '59b6232b15b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely by dropping all active target constraints first."""
    
    # 1. Drop ALL foreign key constraints that connect these tables together
    constraints_to_drop = [
        ('tracks_album_id_fkey', 'tracks'),
        ('likes_track_id_fkey', 'likes'),
        ('plays_track_id_fkey', 'plays')
    ]
    for constraint, table in constraints_to_drop:
        try:
            op.drop_constraint(constraint, table, type_='foreignkey')
        except Exception:
            pass  # Avoid halting if a constraint name differs or is not established

    # 2. Drop the auto-increment integer default from the plays table
    try:
        op.execute("ALTER TABLE plays ALTER COLUMN id DROP DEFAULT")
    except Exception:
        pass

    # 3. Alter column data types with explicit postgresql_using type casting
    op.alter_column('albums', 'id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="id::uuid",
               existing_nullable=False)
    
    op.alter_column('follows', 'id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="id::uuid",
               existing_nullable=False)
    
    op.alter_column('likes', 'id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="id::uuid",
               existing_nullable=False)
    
    op.alter_column('likes', 'track_id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="track_id::uuid",
               existing_nullable=True)
    
    # Explicit conversion from Integer sequence entries to UUID strings
    op.alter_column('plays', 'id',
               existing_type=sa.INTEGER(),
               type_=sa.UUID(),
               postgresql_using="id::text::uuid",
               existing_nullable=False)
    
    op.alter_column('plays', 'track_id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="track_id::uuid",
               existing_nullable=False)

    op.alter_column('tracks', 'id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="id::uuid",
               existing_nullable=False)
    
    op.alter_column('tracks', 'album_id',
               existing_type=sa.VARCHAR(),
               type_=sa.UUID(),
               postgresql_using="album_id::uuid",
               existing_nullable=True)

    # 4. Clean up older sequential indexes safely
    try:
        op.drop_index(op.f('ix_albums_id'), table_name='albums')
    except Exception:
        pass
        
    try:
        op.drop_index(op.f('ix_plays_id'), table_name='plays')
    except Exception:
        pass

    # 5. Append yhur feature extensions 
    op.add_column('tracks', sa.Column('genre', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('duration', sa.Float(), nullable=True))

    # 6. Re-create all structural foreign key connections simultaneously now that types match
    op.create_foreign_key('tracks_album_id_fkey', 'tracks', 'albums', ['album_id'], ['id'])
    op.create_foreign_key('likes_track_id_fkey', 'likes', 'tracks', ['track_id'], ['id'])
    op.create_foreign_key('plays_track_id_fkey', 'plays', 'tracks', ['track_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema safely reversing type switches with string casting."""
    constraints_to_drop = [
        ('tracks_album_id_fkey', 'tracks'),
        ('likes_track_id_fkey', 'likes'),
        ('plays_track_id_fkey', 'plays')
    ]
    for constraint, table in constraints_to_drop:
        try:
            op.drop_constraint(constraint, table, type_='foreignkey')
        except Exception:
            pass

    op.alter_column('tracks', 'album_id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="album_id::text",
               existing_nullable=True)
    
    op.alter_column('tracks', 'id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="id::text",
               existing_nullable=False)
    
    op.drop_column('tracks', 'duration')
    op.drop_column('tracks', 'genre')
    
    op.alter_column('plays', 'track_id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="track_id::text",
               existing_nullable=False)
    
    op.alter_column('plays', 'id',
               existing_type=sa.UUID(),
               type_=sa.INTEGER(),
               postgresql_using="id::text::integer",
               existing_nullable=False)
    
    # Re-apply integer auto-increment serialization behavior if downgraded
    try:
        op.execute("CREATE SEQUENCE IF NOT EXISTS plays_id_seq")
        op.execute("ALTER TABLE plays ALTER COLUMN id SET DEFAULT nextval('plays_id_seq')")
    except Exception:
        pass

    op.alter_column('likes', 'track_id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="track_id::text",
               existing_nullable=True)
    
    op.alter_column('likes', 'id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="id::text",
               existing_nullable=False)
    
    op.alter_column('follows', 'id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="id::text",
               existing_nullable=False)
    
    op.alter_column('albums', 'id',
               existing_type=sa.UUID(),
               type_=sa.VARCHAR(),
               postgresql_using="id::text",
               existing_nullable=False)

    op.create_foreign_key('tracks_album_id_fkey', 'tracks', 'albums', ['album_id'], ['id'])
    op.create_foreign_key('likes_track_id_fkey', 'likes', 'tracks', ['track_id'], ['id'])
    op.create_foreign_key('plays_track_id_fkey', 'plays', 'tracks', ['track_id'], ['id'])
    op.create_index(op.f('ix_plays_id'), 'plays', ['id'], unique=False)
    op.create_index(op.f('ix_albums_id'), 'albums', ['id'], unique=False)