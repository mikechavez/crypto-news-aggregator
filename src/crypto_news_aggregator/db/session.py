from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from functools import lru_cache

from ..core.config import get_settings


@lru_cache()
def get_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )


@lru_cache()
def get_sessionmaker():
    return sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session():
    SessionLocal = get_sessionmaker()
    async with SessionLocal() as session:
        yield session
