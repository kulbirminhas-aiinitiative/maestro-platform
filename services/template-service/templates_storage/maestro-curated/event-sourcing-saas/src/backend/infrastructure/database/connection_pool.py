"""Database connection pool management."""
import asyncpg
from asyncpg.pool import Pool
import os


async def create_connection_pool() -> Pool:
    """Create PostgreSQL connection pool."""
    return await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "eventsourcing"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        min_size=10,
        max_size=50,
        command_timeout=60
    )