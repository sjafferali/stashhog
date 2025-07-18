"""
Tests for database migration utilities.

This module tests the migration runner, version tracking, and rollback functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.migrations import (
    _check_migrations_needed,
    _ensure_alembic_version_table,
    _find_alembic_config,
    _setup_alembic_config,
    run_migrations,
    run_migrations_async,
)


class TestFindAlembicConfig:
    """Test finding alembic configuration file."""

    def test_find_alembic_config_exists(self):
        """Test finding alembic.ini when it exists."""
        # Mock the Path class properly
        with patch("app.core.migrations.Path") as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            MockPath.return_value = mock_path_instance
            MockPath.__name__ = "Path"  # Fix for spec issues

            # Mock __truediv__ for path construction
            mock_path_instance.__truediv__.return_value = mock_path_instance
            mock_path_instance.parent = MagicMock()
            mock_path_instance.parent.parent = MagicMock()
            mock_path_instance.parent.parent.parent.__truediv__.return_value = (
                mock_path_instance
            )

            result = _find_alembic_config()
            assert result == mock_path_instance

    def test_find_alembic_config_not_found(self):
        """Test error when alembic.ini not found."""
        with patch("app.core.migrations.Path") as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            MockPath.return_value = mock_path_instance
            MockPath.__name__ = "Path"

            # Mock __truediv__ for path construction
            mock_path_instance.__truediv__.return_value = mock_path_instance
            mock_path_instance.parent = MagicMock()
            mock_path_instance.parent.parent = MagicMock()
            mock_path_instance.parent.parent.parent.__truediv__.return_value = (
                mock_path_instance
            )

            with pytest.raises(FileNotFoundError, match="alembic.ini not found"):
                _find_alembic_config()


class TestSetupAlembicConfig:
    """Test Alembic configuration setup."""

    def test_setup_alembic_config_docker_path(self):
        """Test setup with Docker container paths."""
        # Create mock path objects with proper structure
        mock_ini_path = MagicMock()
        mock_ini_path.__str__.return_value = "/app/alembic.ini"

        # Create parent mock
        mock_parent = MagicMock()
        mock_alembic_dir = MagicMock()
        mock_alembic_dir.exists.return_value = False
        mock_alembic_dir.__str__.return_value = "/app/alembic"

        # Setup parent relationship
        mock_parent.__truediv__ = MagicMock(return_value=mock_alembic_dir)
        mock_ini_path.parent = mock_parent

        # Mock Path constructor
        with patch("app.core.migrations.Path") as MockPath:
            # Docker path that exists
            docker_path = MagicMock()
            docker_path.exists.return_value = True
            docker_path.__str__.return_value = "/app/alembic"

            MockPath.side_effect = lambda p: (
                docker_path if p == "/app/alembic" else MagicMock()
            )

            with patch("app.core.migrations.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config

                result = _setup_alembic_config(mock_ini_path, "postgresql://test")

                # Verify Config was created
                mock_config_class.assert_called_once_with("/app/alembic.ini")

                # Verify options were set
                mock_config.set_main_option.assert_any_call(
                    "script_location", "/app/alembic"
                )
                mock_config.set_main_option.assert_any_call(
                    "sqlalchemy.url", "postgresql://test"
                )

                assert result == mock_config

    def test_setup_alembic_config_directory_not_found(self):
        """Test error when alembic directory not found."""
        mock_ini_path = MagicMock()
        mock_ini_path.__str__.return_value = "/tmp/alembic.ini"

        # Mock parent and alembic directory
        mock_parent = MagicMock()
        mock_alembic_dir = MagicMock()
        mock_alembic_dir.exists.return_value = False
        mock_parent.__truediv__ = MagicMock(return_value=mock_alembic_dir)
        mock_ini_path.parent = mock_parent

        # Mock docker path that also doesn't exist
        with patch("app.core.migrations.Path") as MockPath:
            docker_path = MagicMock()
            docker_path.exists.return_value = False

            MockPath.side_effect = lambda p: (
                docker_path if p == "/app/alembic" else MagicMock()
            )

            with patch("app.core.migrations.Config"):
                with pytest.raises(
                    FileNotFoundError, match="Alembic directory not found"
                ):
                    _setup_alembic_config(mock_ini_path, "postgresql://test")


class TestEnsureAlembicVersionTable:
    """Test alembic_version table creation."""

    def test_ensure_alembic_version_table_exists(self):
        """Test when alembic_version table already exists."""
        # Mock engine and inspector
        mock_engine = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["alembic_version", "other_table"]

        with patch("app.core.migrations.inspect", return_value=mock_inspector):
            _ensure_alembic_version_table(mock_engine)

            # Should not execute any SQL
            mock_engine.begin.assert_not_called()

    def test_ensure_alembic_version_table_create(self):
        """Test creating alembic_version table when it doesn't exist."""
        # Mock engine and inspector
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_engine.begin.return_value = mock_conn

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["other_table"]

        with patch("sqlalchemy.inspect", return_value=mock_inspector):
            _ensure_alembic_version_table(mock_engine)

            # Should create the table
            mock_engine.begin.assert_called_once()
            mock_conn.execute.assert_called_once()

            # Check SQL contains CREATE TABLE
            call_args = mock_conn.execute.call_args[0][0]
            assert "CREATE TABLE IF NOT EXISTS alembic_version" in str(call_args)


class TestCheckMigrationsNeeded:
    """Test migration check functionality."""

    def test_check_migrations_needed_up_to_date(self):
        """Test when database is up to date."""
        mock_engine = MagicMock()
        mock_config = MagicMock()

        # Mock script directory
        mock_script = MagicMock()
        mock_script.get_current_head.return_value = "abc123"

        # Mock migration context
        mock_context = MagicMock()
        mock_context.get_current_revision.return_value = "abc123"

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_engine.begin.return_value = mock_conn

        with patch(
            "alembic.script.ScriptDirectory.from_config", return_value=mock_script
        ):
            with patch(
                "alembic.runtime.migration.MigrationContext.configure",
                return_value=mock_context,
            ):
                result = _check_migrations_needed(mock_engine, mock_config)
                assert result is False

    def test_check_migrations_needed_pending(self):
        """Test when migrations are pending."""
        mock_engine = MagicMock()
        mock_config = MagicMock()

        # Mock script directory
        mock_script = MagicMock()
        mock_script.get_current_head.return_value = "def456"

        # Mock revisions
        mock_rev1 = MagicMock()
        mock_rev1.revision = "def456"
        mock_rev2 = MagicMock()
        mock_rev2.revision = "abc123"
        mock_script.walk_revisions.return_value = [mock_rev1, mock_rev2]

        # Mock migration context
        mock_context = MagicMock()
        mock_context.get_current_revision.return_value = "abc123"

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_engine.begin.return_value = mock_conn

        with patch(
            "alembic.script.ScriptDirectory.from_config", return_value=mock_script
        ):
            with patch(
                "alembic.runtime.migration.MigrationContext.configure",
                return_value=mock_context,
            ):
                result = _check_migrations_needed(mock_engine, mock_config)
                assert result is True


class TestRunMigrations:
    """Test the main migration runner."""

    @patch("app.core.database.reset_db_engines")
    @patch("app.core.migrations.command")
    @patch("app.core.migrations.create_engine")
    @patch("app.core.migrations._check_migrations_needed")
    @patch("app.core.migrations._ensure_alembic_version_table")
    @patch("app.core.migrations._setup_alembic_config")
    @patch("app.core.migrations._find_alembic_config")
    @patch("app.core.migrations.get_settings")
    def test_run_migrations_no_migrations_needed(
        self,
        mock_get_settings,
        mock_find_config,
        mock_setup_config,
        mock_ensure_table,
        mock_check_migrations,
        mock_create_engine,
        mock_command,
        mock_reset_db,
    ):
        """Test run_migrations when no migrations are needed."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.database.url = "sqlite:///test.db"
        mock_get_settings.return_value = mock_settings

        mock_find_config.return_value = Path("/tmp/alembic.ini")
        mock_alembic_cfg = Mock()
        mock_setup_config.return_value = mock_alembic_cfg

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_check_migrations.return_value = False  # No migrations needed

        # Run function
        run_migrations()

        # Verify flow
        mock_get_settings.assert_called_once()
        mock_find_config.assert_called_once()
        mock_setup_config.assert_called_once_with(
            Path("/tmp/alembic.ini"), "sqlite:///test.db"
        )
        mock_create_engine.assert_called_once_with("sqlite:///test.db")
        mock_ensure_table.assert_called_once_with(mock_engine)
        mock_check_migrations.assert_called_once_with(mock_engine, mock_alembic_cfg)

        # Should not run upgrade
        mock_command.upgrade.assert_not_called()

        # Should still dispose engine
        mock_engine.dispose.assert_called_once()

        # Should not reset db engines when no migrations run
        mock_reset_db.assert_not_called()

    @patch("app.core.database.reset_db_engines")
    @patch("app.core.migrations.command")
    @patch("app.core.migrations.create_engine")
    @patch("app.core.migrations._check_migrations_needed")
    @patch("app.core.migrations._ensure_alembic_version_table")
    @patch("app.core.migrations._setup_alembic_config")
    @patch("app.core.migrations._find_alembic_config")
    @patch("app.core.migrations.get_settings")
    def test_run_migrations_success(
        self,
        mock_get_settings,
        mock_find_config,
        mock_setup_config,
        mock_ensure_table,
        mock_check_migrations,
        mock_create_engine,
        mock_command,
        mock_reset_db,
    ):
        """Test successful migration run."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.database.url = "sqlite:///test.db"
        mock_get_settings.return_value = mock_settings

        mock_find_config.return_value = Path("/tmp/alembic.ini")
        mock_alembic_cfg = Mock()
        mock_setup_config.return_value = mock_alembic_cfg

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_check_migrations.return_value = True  # Migrations needed
        mock_command.upgrade.return_value = None

        # Run function
        run_migrations()

        # Verify migrations were run
        mock_command.upgrade.assert_called_once_with(mock_alembic_cfg, "head")

        # Verify cleanup
        mock_engine.dispose.assert_called_once()
        mock_reset_db.assert_called_once()

    @patch("app.core.database.reset_db_engines")
    @patch("app.core.migrations.command")
    @patch("app.core.migrations.create_engine")
    @patch("app.core.migrations._check_migrations_needed")
    @patch("app.core.migrations._ensure_alembic_version_table")
    @patch("app.core.migrations._setup_alembic_config")
    @patch("app.core.migrations._find_alembic_config")
    @patch("app.core.migrations.get_settings")
    def test_run_migrations_postgresql_timeout(
        self,
        mock_get_settings,
        mock_find_config,
        mock_setup_config,
        mock_ensure_table,
        mock_check_migrations,
        mock_create_engine,
        mock_command,
        mock_reset_db,
    ):
        """Test PostgreSQL statement timeout is set."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.database.url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_find_config.return_value = Path("/tmp/alembic.ini")
        mock_alembic_cfg = Mock()
        mock_setup_config.return_value = mock_alembic_cfg

        # Mock engine with connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        mock_check_migrations.return_value = True
        mock_command.upgrade.return_value = None

        # Run function
        run_migrations()

        # Verify timeout was set
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "SET statement_timeout" in str(call_args)

    @patch("app.core.database.reset_db_engines")
    @patch("app.core.migrations.command")
    @patch("app.core.migrations.create_engine")
    @patch("app.core.migrations._check_migrations_needed")
    @patch("app.core.migrations._ensure_alembic_version_table")
    @patch("app.core.migrations._setup_alembic_config")
    @patch("app.core.migrations._find_alembic_config")
    @patch("app.core.migrations.get_settings")
    def test_run_migrations_failure(
        self,
        mock_get_settings,
        mock_find_config,
        mock_setup_config,
        mock_ensure_table,
        mock_check_migrations,
        mock_create_engine,
        mock_command,
        mock_reset_db,
    ):
        """Test migration failure handling."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.database.url = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_find_config.return_value = Path("/tmp/alembic.ini")
        mock_alembic_cfg = Mock()
        mock_setup_config.return_value = mock_alembic_cfg

        # Mock engine with connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        mock_check_migrations.return_value = True

        # Mock migration failure
        mock_command.upgrade.side_effect = Exception("Migration failed")

        # Run function and expect exception
        with pytest.raises(Exception, match="Migration failed"):
            run_migrations()

        # Verify cleanup still happens
        mock_engine.dispose.assert_called_once()
        mock_reset_db.assert_called_once()


class TestRunMigrationsAsync:
    """Test async migration runner."""

    @pytest.mark.asyncio
    async def test_run_migrations_async(self):
        """Test async wrapper calls sync function."""
        with patch("app.core.migrations.run_migrations") as mock_run:
            await run_migrations_async()
            mock_run.assert_called_once()
