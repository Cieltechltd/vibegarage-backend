import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.db.database import Base, SQLALCHEMY_DATABASE_URL

# Access the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models for 'autogenerate' support
from app.models.user import User
from app.models.track import Track
from app.models.play import Play
from app.models.like import Like
from app.models.follow import Follow
from app.models.album import Album

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Ensure the URL is pulled from the environment for offline mode as well
    url = SQLALCHEMY_DATABASE_URL 
    
    # Fix for Render's postgres:// vs postgresql://
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Use the existing logic to override the .ini URL with your DB module's URL
    db_url = SQLALCHEMY_DATABASE_URL
    
    # Fix for Render's postgres:// vs postgresql:// logic
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    alembic_config = config.get_section(config.config_ini_section, {})
    alembic_config["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()