from logging.config import fileConfig
import asyncio
import sys
import os

# Add src directory to Python path for src layout
alembic_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(alembic_dir)
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and models (should work now with correct path)
from crypto_news_aggregator.db import Base
from crypto_news_aggregator.db.models import Source, Article, Sentiment, Trend

target_metadata = Base.metadata

# Set up the database URL
from crypto_news_aggregator.core.config import get_settings
settings = get_settings()
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# Debug logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    print(f"Tables in metadata: {list(target_metadata.tables.keys())}")
    
    if not target_metadata.tables:
        print("WARNING: No tables found in metadata!")
        return
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()