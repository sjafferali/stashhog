"""Tests for database utility functions."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.db_utils import check_db_health, drop_db, init_db, reset_db, seed_db


class TestDBUtils:
    """Test database utility functions."""

    @patch("app.core.db_utils.Base.metadata.create_all")
    @patch("app.core.db_utils.logger")
    def test_init_db_success(self, mock_logger, mock_create_all):
        """Test successful database initialization."""
        init_db()

        mock_create_all.assert_called_once()
        mock_logger.info.assert_any_call("Initializing database...")
        mock_logger.info.assert_any_call("Database initialized successfully")

    @patch("app.core.db_utils.Base.metadata.create_all")
    @patch("app.core.db_utils.logger")
    def test_init_db_failure(self, mock_logger, mock_create_all):
        """Test database initialization failure."""
        mock_create_all.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            init_db()

        mock_logger.error.assert_called_once_with(
            "Failed to initialize database: DB error"
        )

    @patch("app.core.db_utils.get_settings")
    @patch("app.core.db_utils.Base.metadata.drop_all")
    @patch("app.core.db_utils.logger")
    def test_drop_db_success(self, mock_logger, mock_drop_all, mock_get_settings):
        """Test successful database drop in non-production."""
        mock_settings = Mock()
        mock_settings.app.environment = "development"
        mock_get_settings.return_value = mock_settings

        drop_db()

        mock_drop_all.assert_called_once()
        mock_logger.warning.assert_any_call("Dropping all database tables...")
        mock_logger.warning.assert_any_call("All database tables dropped")

    @patch("app.core.db_utils.get_settings")
    def test_drop_db_production_error(self, mock_get_settings):
        """Test database drop is prevented in production."""
        mock_settings = Mock()
        mock_settings.app.environment = "production"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(
            RuntimeError, match="Cannot drop database in production environment"
        ):
            drop_db()

    @patch("app.core.db_utils.get_settings")
    @patch("app.core.db_utils.Base.metadata.drop_all")
    @patch("app.core.db_utils.logger")
    def test_drop_db_failure(self, mock_logger, mock_drop_all, mock_get_settings):
        """Test database drop failure."""
        mock_settings = Mock()
        mock_settings.app.environment = "development"
        mock_get_settings.return_value = mock_settings
        mock_drop_all.side_effect = Exception("Drop error")

        with pytest.raises(Exception, match="Drop error"):
            drop_db()

        mock_logger.error.assert_called_once_with("Failed to drop database: Drop error")

    @patch("app.core.db_utils.logger")
    def test_seed_db_success(self, mock_logger):
        """Test successful database seeding."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None

        seed_db(mock_db)

        # Check that settings were added
        assert mock_db.add.call_count >= 4  # At least 4 default settings
        assert mock_db.commit.called
        mock_logger.info.assert_any_call("Seeding database...")
        mock_logger.info.assert_any_call("Database seeded successfully")

    @patch("app.core.db_utils.logger")
    def test_seed_db_existing_data(self, mock_logger):
        """Test seeding with existing data (should skip)."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        # Return existing objects for all queries
        mock_query.filter_by.return_value.first.return_value = Mock()

        seed_db(mock_db)

        # Should not add any new objects
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    @patch("app.core.db_utils.logger")
    def test_seed_db_failure(self, mock_logger):
        """Test database seeding failure."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Query error")

        with pytest.raises(Exception, match="Query error"):
            seed_db(mock_db)

        mock_db.rollback.assert_called_once()
        mock_logger.error.assert_called_once()

    @patch("app.core.db_utils.inspect")
    @patch("app.core.db_utils.sync_engine")
    @patch("app.core.db_utils.logger")
    def test_check_db_health_success(self, mock_logger, mock_engine, mock_inspect):
        """Test successful database health check."""
        # Mock connection and inspector
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock SELECT 1 result
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result

        # Mock inspector
        mock_inspector = Mock()
        mock_inspect.return_value = mock_inspector
        expected_tables = [
            "scene",
            "performer",
            "tag",
            "studio",
            "scene_performer",
            "scene_tag",
            "analysis_plan",
            "plan_change",
            "job",
            "setting",
            "scheduled_task",
            "alembic_version",
        ]
        mock_inspector.get_table_names.return_value = expected_tables

        # Mock alembic version
        mock_version_result = Mock()
        mock_version_result.first.return_value = ["abc123"]
        mock_conn.execute.side_effect = [mock_result, mock_version_result]

        health = check_db_health()

        assert health["connected"] is True
        assert health["tables_exist"] is True
        assert health["version"] == "abc123"
        assert health["error"] is None

    @patch("app.core.db_utils.sync_engine")
    @patch("app.core.db_utils.logger")
    def test_check_db_health_connection_failure(self, mock_logger, mock_engine):
        """Test database health check with connection failure."""
        mock_engine.connect.side_effect = Exception("Connection failed")

        health = check_db_health()

        assert health["connected"] is False
        assert health["tables_exist"] is False
        assert health["version"] is None
        assert health["error"] == "Connection failed"
        mock_logger.error.assert_called_once()

    @patch("app.core.db_utils.inspect")
    @patch("app.core.db_utils.sync_engine")
    def test_check_db_health_missing_tables(self, mock_engine, mock_inspect):
        """Test database health check with missing tables."""
        # Mock connection and inspector
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock SELECT 1 result
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_conn.execute.return_value = mock_result

        # Mock inspector with missing tables
        mock_inspector = Mock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = [
            "scene",
            "performer",
        ]  # Missing tables

        health = check_db_health()

        assert health["connected"] is True
        assert health["tables_exist"] is False
        assert len(health["existing_tables"]) == 2

    @patch("app.core.db_utils.get_settings")
    @patch("app.core.db_utils.drop_db")
    @patch("app.core.db_utils.init_db")
    @patch("app.core.db_utils.seed_db")
    @patch("app.core.db_utils.logger")
    def test_reset_db_success(
        self, mock_logger, mock_seed, mock_init, mock_drop, mock_get_settings
    ):
        """Test successful database reset."""
        mock_settings = Mock()
        mock_settings.app.environment = "development"
        mock_get_settings.return_value = mock_settings
        mock_db = Mock(spec=Session)

        reset_db(mock_db)

        mock_drop.assert_called_once()
        mock_init.assert_called_once()
        mock_seed.assert_called_once_with(mock_db)
        mock_logger.warning.assert_called_once_with("Resetting database...")
        mock_logger.info.assert_called_once_with("Database reset complete")

    @patch("app.core.db_utils.get_settings")
    def test_reset_db_production_error(self, mock_get_settings):
        """Test database reset is prevented in production."""
        mock_settings = Mock()
        mock_settings.app.environment = "production"
        mock_get_settings.return_value = mock_settings
        mock_db = Mock(spec=Session)

        with pytest.raises(
            RuntimeError, match="Cannot reset database in production environment"
        ):
            reset_db(mock_db)
