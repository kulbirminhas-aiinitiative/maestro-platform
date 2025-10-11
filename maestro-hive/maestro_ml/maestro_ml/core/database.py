#!/usr/bin/env python3
"""
Database connection and session management for Maestro ML Platform
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from maestro_ml.config.settings import get_settings
from maestro_ml.models.database import Base

settings = get_settings()


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database (create tables)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables (use with caution!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_session() as session:
        yield session
