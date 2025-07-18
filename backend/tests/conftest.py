"""Shared pytest fixtures and configuration."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    # Use a temporary file for SQLite database to support migrations
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    test_db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Run migrations on the test database
    from alembic import command
    from alembic.config import Config

    # Create alembic config
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    try:
        # Run migrations
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        # If migrations fail, use create_all as fallback
        import logging

        logging.warning(f"Migration failed in test: {e}. Using create_all fallback.")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    yield engine
    engine.dispose()

    # Clean up temp file
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def test_async_engine():
    """Create test async database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine


@pytest.fixture
async def test_async_session(test_async_engine):
    """Create test async database session."""
    async_session_maker = async_sessionmaker(
        test_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # For in-memory SQLite, we need to ensure tables exist
    # Since we can't run Alembic migrations on in-memory databases easily
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Clean up tables after test
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()

    # Clean up all data after each test
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    # Create a new engine for each test
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with async_session_maker() as session:
            yield session

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create tables synchronously
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_test_db(engine))

    with TestClient(app) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
    loop.run_until_complete(engine.dispose())
    loop.close()


async def init_test_db(engine):
    """Initialize test database."""
    async with engine.begin() as conn:
        # Drop all tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Return test database URL."""
    return TEST_DATABASE_URL


@pytest.fixture
def anyio_backend():
    """Configure anyio for pytest-asyncio."""
    return "asyncio"
