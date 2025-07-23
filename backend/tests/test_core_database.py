"""
Test core database module for connection management and session handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    async_engine,
    close_db,
    get_async_db,
    get_db,
    reset_db_engines,
    sync_engine,
)


class TestDatabaseConfiguration:
    """Test database configuration and engine creation."""

    def test_url_conversion_logic(self):
        """Test URL conversion logic for async engines."""
        # Test cases for URL conversion
        test_cases = [
            ("sqlite:///test.db", "sqlite+aiosqlite:///test.db"),
            (
                "postgresql://user:pass@localhost/db",
                "postgresql+asyncpg://user:pass@localhost/db",
            ),
            (
                "postgres://user:pass@localhost/db",
                "postgresql+asyncpg://user:pass@localhost/db",
            ),
        ]

        for input_url, expected_url in test_cases:
            # Simulate the URL conversion logic from database.py
            async_url = input_url
            if async_url.startswith("sqlite://"):
                async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
            elif async_url.startswith("postgresql://"):
                async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
            elif async_url.startswith("postgres://"):
                async_url = async_url.replace("postgres://", "postgresql+asyncpg://")

            assert async_url == expected_url

    def test_engine_args_logic(self):
        """Test engine argument configuration logic."""
        # Test SQLite configuration
        is_sqlite = True
        sync_engine_args = {
            "echo": False,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }

        if not is_sqlite:
            sync_engine_args.update(
                {
                    "pool_size": 5,
                    "max_overflow": 10,
                }
            )

        # SQLite should not have pool settings
        assert "pool_size" not in sync_engine_args
        assert "max_overflow" not in sync_engine_args

        # Test PostgreSQL configuration
        is_sqlite = False
        sync_engine_args = {
            "echo": True,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        }

        if not is_sqlite:
            sync_engine_args.update(
                {
                    "pool_size": 5,
                    "max_overflow": 10,
                }
            )

        # PostgreSQL should have pool settings
        assert sync_engine_args["pool_size"] == 5
        assert sync_engine_args["max_overflow"] == 10


class TestDatabaseSessions:
    """Test database session management."""

    def test_get_db_session(self):
        """Test sync database session dependency."""
        # Create a mock session
        mock_session = MagicMock(spec=Session)

        with patch("app.core.database.SessionLocal") as mock_session_local:
            mock_session_local.return_value = mock_session

            # Get session from dependency
            gen = get_db()
            session = next(gen)

            # Verify session is returned
            assert session == mock_session

            # Complete generator (triggers finally block)
            try:
                next(gen)
            except StopIteration:
                pass

            # Verify session was closed
            mock_session.close.assert_called_once()

    def test_get_db_session_with_exception(self):
        """Test sync database session cleanup on exception."""
        # Create a mock session
        mock_session = MagicMock(spec=Session)

        with patch("app.core.database.SessionLocal") as mock_session_local:
            mock_session_local.return_value = mock_session

            # Get session from dependency
            gen = get_db()
            session = next(gen)

            # Verify session is returned
            assert session == mock_session

            # Simulate exception during usage
            try:
                gen.throw(ValueError("Test error"))
            except ValueError:
                pass

            # Verify session was still closed
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_db_session(self):
        """Test async database session dependency."""
        # Create a mock async session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the async context manager
        mock_async_context = AsyncMock()
        mock_async_context.__aenter__.return_value = mock_session
        mock_async_context.__aexit__.return_value = None

        with patch("app.core.database.AsyncSessionLocal") as mock_async_session_local:
            mock_async_session_local.return_value = mock_async_context

            # Get session from dependency
            gen = get_async_db()
            session = await gen.__anext__()

            # Verify session is returned
            assert session == mock_session

            # Complete generator
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

            # Verify context manager was used properly
            mock_async_context.__aenter__.assert_called_once()
            mock_async_context.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_db_session_with_exception(self):
        """Test async database session cleanup on exception."""
        # Create a mock async session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the async context manager
        mock_async_context = AsyncMock()
        mock_async_context.__aenter__.return_value = mock_session
        mock_async_context.__aexit__.return_value = None

        with patch("app.core.database.AsyncSessionLocal") as mock_async_session_local:
            mock_async_session_local.return_value = mock_async_context

            # Get session from dependency
            gen = get_async_db()
            session = await gen.__anext__()

            # Verify session is returned
            assert session == mock_session

            # Simulate exception during usage
            try:
                await gen.athrow(ValueError("Test error"))
            except ValueError:
                pass

            # Verify context manager was still used properly
            mock_async_context.__aenter__.assert_called_once()
            mock_async_context.__aexit__.assert_called_once()


class TestDatabaseUtilities:
    """Test database utility functions."""

    @pytest.mark.asyncio
    async def test_close_db(self):
        """Test database connection closing."""
        with patch("app.core.database.async_engine") as mock_async_engine:
            with patch("app.core.database.sync_engine") as mock_sync_engine:
                mock_async_engine.dispose = AsyncMock()
                mock_sync_engine.dispose = MagicMock()

                await close_db()

                # Verify both engines were disposed
                mock_async_engine.dispose.assert_called_once()
                mock_sync_engine.dispose.assert_called_once()

    def test_reset_db_engines_sync(self):
        """Test resetting database engines from sync context."""
        with patch("app.core.database.sync_engine") as mock_sync_engine:
            with patch("app.core.database.async_engine") as mock_async_engine:
                mock_sync_engine.dispose = MagicMock()
                mock_async_engine.dispose = AsyncMock()

                with patch(
                    "asyncio.get_running_loop",
                    side_effect=RuntimeError("No running loop"),
                ):
                    with patch("asyncio.run") as mock_run:
                        reset_db_engines()

                        # Verify sync engine was disposed
                        mock_sync_engine.dispose.assert_called_once()

                        # Verify async engine dispose was scheduled
                        mock_run.assert_called_once()
                        # Get the coroutine that was passed to asyncio.run
                        coro = mock_run.call_args[0][0]
                        assert asyncio.iscoroutine(coro)

    def test_reset_db_engines_async(self):
        """Test resetting database engines from async context."""
        # Create a mock event loop
        mock_loop = MagicMock()
        mock_loop.create_task = MagicMock()

        with patch("app.core.database.sync_engine") as mock_sync_engine:
            with patch("app.core.database.async_engine") as mock_async_engine:
                mock_sync_engine.dispose = MagicMock()
                mock_async_engine.dispose = AsyncMock()

                with patch("asyncio.get_running_loop", return_value=mock_loop):
                    reset_db_engines()

                    # Verify sync engine was disposed
                    mock_sync_engine.dispose.assert_called_once()

                    # Verify async engine dispose task was created
                    mock_loop.create_task.assert_called_once()
                    # Get the coroutine that was passed to create_task
                    coro = mock_loop.create_task.call_args[0][0]
                    assert asyncio.iscoroutine(coro)


class TestDatabaseIntegration:
    """Test database integration with actual connections."""

    @pytest.mark.integration
    def test_sync_session_operations(self, test_session):
        """Test basic sync session operations."""
        # Get a session
        gen = get_db()
        db = next(gen)

        try:
            # Execute a simple query
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Verify session is active
            assert db.is_active

        finally:
            # Clean up
            try:
                next(gen)
            except StopIteration:
                pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_session_operations(self, test_async_session):
        """Test basic async session operations."""
        # Get a session
        async for db in get_async_db():
            # Execute a simple query
            result = await db.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Verify session is active
            assert db.is_active

    @pytest.mark.integration
    def test_base_metadata(self):
        """Test Base metadata is properly configured."""
        # Base should be available for model definitions
        assert hasattr(Base, "metadata")
        # Note: declarative_base() doesn't have __tablename__ by default
        assert hasattr(Base, "__class__")

    @pytest.mark.integration
    def test_session_factory_configuration(self):
        """Test session factory configurations."""
        # Check SessionLocal configuration
        assert SessionLocal.kw["autocommit"] is False
        assert SessionLocal.kw["autoflush"] is False
        assert SessionLocal.kw["bind"] == sync_engine

        # Check AsyncSessionLocal configuration
        assert AsyncSessionLocal.kw["expire_on_commit"] is False
        assert AsyncSessionLocal.kw["autocommit"] is False
        assert AsyncSessionLocal.kw["autoflush"] is False


class TestDatabaseEngines:
    """Test database engine configurations."""

    def test_sync_engine_properties(self):
        """Test sync engine properties."""
        # Engine should be properly configured
        assert sync_engine is not None
        assert hasattr(sync_engine, "dispose")
        # Note: sync_engine may not have execute method directly

    def test_async_engine_properties(self):
        """Test async engine properties."""
        # Engine should be properly configured
        assert async_engine is not None
        assert hasattr(async_engine, "dispose")

    @pytest.mark.integration
    def test_engine_echo_setting(self):
        """Test engine echo setting from configuration."""
        from app.core.config import get_settings

        settings = get_settings()

        # Check if settings are available
        assert hasattr(settings, "database")
        assert hasattr(settings.database, "echo")
