"""
Database configuration and session management.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import get_settings

settings = get_settings()

# Create sync engine
sync_engine = create_engine(
    settings.database.url,
    connect_args={"check_same_thread": False} if settings.database.url.startswith("sqlite") else {},
    echo=settings.database.echo,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=True,
)

# Create async engine
async_engine = create_async_engine(
    settings.database.url.replace("sqlite://", "sqlite+aiosqlite://"),  # Convert to async URL
    echo=settings.database.echo,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=True,
)

# Create sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

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


async def get_async_db() -> AsyncSession:
    """
    Dependency to get async database session.
    
    Yields:
        Async database session
    """
    async with AsyncSessionLocal() as session:
        yield session


def init_database() -> None:
    """
    Initialize database by creating all tables.
    
    This should be called on application startup.
    """
    Base.metadata.create_all(bind=sync_engine)


async def init_db():
    """Initialize database tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await async_engine.dispose()
    sync_engine.dispose()