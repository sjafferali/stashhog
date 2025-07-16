"""
Database configuration and session management.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Create sync engine
# Prepare engine args based on database type
is_sqlite = settings.database.url.startswith("sqlite")
sync_engine_args = {
    "echo": settings.database.echo,
    "pool_recycle": settings.database.pool_recycle,
    "pool_pre_ping": True,
}

# Only add pool settings for non-SQLite databases
if not is_sqlite:
    sync_engine_args.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

sync_engine = create_engine(
    settings.database.url,
    connect_args=({"check_same_thread": False} if is_sqlite else {}),
    **sync_engine_args,
)

# Create async engine
# Convert database URL to async format
async_url = settings.database.url
if async_url.startswith("sqlite://"):
    async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
elif async_url.startswith("postgresql://"):
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
elif async_url.startswith("postgres://"):
    async_url = async_url.replace("postgres://", "postgresql+asyncpg://")

# Check if using SQLite for async engine
is_async_sqlite = async_url.startswith("sqlite+aiosqlite://")
async_engine_args = {
    "echo": settings.database.echo,
    "pool_recycle": settings.database.pool_recycle,
    "pool_pre_ping": True,
}

# Only add pool settings for non-SQLite databases
if not is_async_sqlite:
    async_engine_args.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

async_engine = create_async_engine(async_url, **async_engine_args)

# Create sync session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.

    Yields:
        Async database session
    """
    async with AsyncSessionLocal() as session:
        yield session


# Note: Database initialization is handled by Alembic migrations
# See app.core.migrations for migration management


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
    sync_engine.dispose()


def reset_db_engines() -> None:
    """
    Reset database engines by clearing their connection pools.

    This is useful after migrations to ensure connections use the updated schema.
    """
    # Dispose sync engine connections
    sync_engine.dispose()

    # For async engine, we need to run dispose in an event loop
    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, create a task
        loop.create_task(async_engine.dispose())
    except RuntimeError:
        # No running loop, create a new one
        asyncio.run(async_engine.dispose())
