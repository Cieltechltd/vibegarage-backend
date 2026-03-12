import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.database import Base, SQLALCHEMY_DATABASE_URL

config = context.config


if config.config_file_name is not None and os.path.exists(config.config_file_name):
    fileConfig(config.config_file_name)


from app.models.user import User
from app.models.track import Track
from app.models.play import Play
from app.models.like import Like
from app.models.follow import Follow
from app.models.album import Album
from app.models.payment import ArtistPaymentSettings


target_metadata = Base.metadata

def get_url():
    
    url = SQLALCHEMY_DATABASE_URL
    
   
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()