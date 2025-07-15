"""
Database configuration and session management.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Create sync engine
sync_engine = create_engine(
    settings.database.url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database.url.startswith("sqlite")
        else {}
    ),
    echo=settings.database.echo,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=True,
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

async_engine = create_async_engine(
    async_url,
    echo=settings.database.echo,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=True,
)

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
