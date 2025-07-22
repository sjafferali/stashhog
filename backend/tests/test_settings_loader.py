"""Tests for settings loader module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.settings_loader import (
    _apply_openai_overrides,
    _apply_section_overrides,
    _apply_stash_overrides,
    _apply_video_ai_overrides,
    _parse_db_settings,
    load_settings_with_db_overrides,
)


class TestParseDbSettings:
    """Test database settings parsing."""

    def test_parse_nested_settings(self):
        """Test parsing settings with underscore notation into nested structure."""
        db_settings = [
            Mock(key="stash_url", value="http://localhost:9999"),
            Mock(key="stash_api_key", value="test-key"),
            Mock(key="openai_api_key", value="sk-test"),
            Mock(key="sync_interval", value=60),
        ]

        result = _parse_db_settings(db_settings)

        assert result == {
            "stash": {"url": "http://localhost:9999", "api_key": "test-key"},
            "openai": {"api_key": "sk-test"},
            "sync": {"interval": 60},
        }

    def test_parse_non_nested_settings(self):
        """Test parsing settings without underscores."""
        db_settings = [
            Mock(key="debug", value=True),
            Mock(key="version", value="1.0.0"),
        ]

        result = _parse_db_settings(db_settings)

        assert result == {"debug": True, "version": "1.0.0"}

    def test_parse_empty_settings(self):
        """Test parsing empty settings list."""
        result = _parse_db_settings([])
        assert result == {}


class TestApplySectionOverrides:
    """Test section override application."""

    def test_apply_existing_section(self):
        """Test applying overrides to existing section."""
        settings_dict = {
            "stash": {"url": "http://old-url", "api_key": "old-key", "timeout": 30}
        }
        overrides = {"stash": {"url": "http://new-url", "api_key": "new-key"}}

        _apply_section_overrides(settings_dict, overrides, "stash")

        assert settings_dict["stash"]["url"] == "http://new-url"
        assert settings_dict["stash"]["api_key"] == "new-key"
        assert settings_dict["stash"]["timeout"] == 30  # Unchanged

    def test_apply_non_existing_section(self):
        """Test applying overrides to non-existing section."""
        settings_dict = {"other": {"key": "value"}}
        overrides = {"stash": {"url": "http://test"}}

        # Should not raise error
        _apply_section_overrides(settings_dict, overrides, "stash")

        assert "stash" not in settings_dict

    def test_apply_with_extra_override_keys(self):
        """Test applying overrides with keys not in original settings."""
        settings_dict = {"sync": {"interval": 60}}
        overrides = {
            "sync": {"interval": 120, "new_key": "new_value"}  # Not in original
        }

        _apply_section_overrides(settings_dict, overrides, "sync")

        assert settings_dict["sync"]["interval"] == 120
        assert "new_key" not in settings_dict["sync"]


class TestApplyStashOverrides:
    """Test Stash-specific override application."""

    def test_apply_stash_url_override(self):
        """Test applying Stash URL override."""
        settings_dict = {"stash": {"url": "http://old-url", "api_key": None}}
        overrides = {"stash": {"url": "http://new-url"}}

        _apply_stash_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["url"] == "http://new-url"

    def test_apply_stash_api_key_override(self):
        """Test applying Stash API key override."""
        settings_dict = {"stash": {"url": "http://localhost", "api_key": "old-key"}}
        overrides = {"stash": {"api_key": "new-key"}}

        _apply_stash_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["api_key"] == "new-key"

    def test_skip_null_api_key(self):
        """Test that null API key values are converted to None."""
        settings_dict = {"stash": {"api_key": "old-key"}}
        overrides = {"stash": {"api_key": None}}

        _apply_stash_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["api_key"] is None

    def test_skip_zero_api_key(self):
        """Test that zero API key values are skipped (data error)."""
        settings_dict = {"stash": {"api_key": "old-key"}}
        overrides = {"stash": {"api_key": 0}}

        _apply_stash_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["api_key"] is None

    def test_no_stash_overrides(self):
        """Test when no stash overrides exist."""
        settings_dict = {"stash": {"url": "http://test"}}
        overrides = {"other": {"key": "value"}}

        _apply_stash_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["url"] == "http://test"


class TestApplyOpenAIOverrides:
    """Test OpenAI-specific override application."""

    def test_apply_openai_api_key(self):
        """Test applying OpenAI API key override."""
        settings_dict = {"openai": {"api_key": "old-key", "model": "gpt-3.5-turbo"}}
        overrides = {"openai": {"api_key": "sk-new-key"}}

        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["openai"]["api_key"] == "sk-new-key"
        assert settings_dict["openai"]["model"] == "gpt-3.5-turbo"

    def test_apply_openai_model(self):
        """Test applying OpenAI model override."""
        settings_dict = {"openai": {"model": "gpt-3.5-turbo"}}
        overrides = {"openai": {"model": "gpt-4"}}

        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["openai"]["model"] == "gpt-4"

    def test_apply_openai_base_url(self):
        """Test applying OpenAI base URL override."""
        settings_dict = {"openai": {"base_url": None}}
        overrides = {"openai": {"base_url": "https://custom-api.com"}}

        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["openai"]["base_url"] == "https://custom-api.com"

    def test_skip_null_base_url(self):
        """Test that null base URL values are handled."""
        settings_dict = {"openai": {"base_url": "https://old-url.com"}}
        overrides = {"openai": {"base_url": None}}

        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["openai"]["base_url"] is None

    def test_skip_zero_base_url(self):
        """Test that zero base URL values are skipped."""
        settings_dict = {"openai": {"base_url": "https://old-url.com"}}
        overrides = {"openai": {"base_url": 0}}

        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["openai"]["base_url"] is None


class TestApplyVideoAIOverrides:
    """Test video AI settings override application."""

    def test_apply_video_ai_settings(self):
        """Test applying video AI analysis settings."""
        settings_dict = {
            "analysis": {
                "ai_video_server_url": "http://old-server",
                "frame_interval": 10,
            }
        }

        db_settings = [
            Mock(key="analysis_ai_video_server_url", value="http://new-server"),
            Mock(key="analysis_frame_interval", value=5),
            Mock(key="analysis_ai_video_threshold", value=0.8),
            Mock(key="analysis_server_timeout", value=120),
            Mock(key="analysis_create_markers", value=True),
        ]

        _apply_video_ai_overrides(settings_dict, db_settings)

        assert settings_dict["analysis"]["ai_video_server_url"] == "http://new-server"
        assert settings_dict["analysis"]["frame_interval"] == 5
        assert settings_dict["analysis"]["ai_video_threshold"] == 0.8
        assert settings_dict["analysis"]["server_timeout"] == 120
        assert settings_dict["analysis"]["create_markers"] is True

    def test_apply_video_ai_partial_settings(self):
        """Test applying partial video AI settings."""
        settings_dict = {}

        db_settings = [
            Mock(key="analysis_frame_interval", value=15),
            Mock(key="other_key", value="other_value"),
        ]

        _apply_video_ai_overrides(settings_dict, db_settings)

        assert settings_dict["analysis"]["frame_interval"] == 15
        assert len(settings_dict["analysis"]) == 1

    def test_apply_video_ai_no_matches(self):
        """Test when no video AI settings match."""
        settings_dict = {"analysis": {}}

        db_settings = [
            Mock(key="stash_url", value="http://test"),
            Mock(key="openai_key", value="test"),
        ]

        _apply_video_ai_overrides(settings_dict, db_settings)

        assert settings_dict["analysis"] == {}


class TestEnvironmentVariableParsing:
    """Test environment variable parsing and validation."""

    def test_parse_settings_with_special_env_keys(self):
        """Test parsing settings with environment-specific keys."""
        db_settings = [
            Mock(key="app_debug", value="true"),
            Mock(key="database_url", value="postgresql://localhost/test"),
            Mock(key="sync_enabled", value=True),
            Mock(key="analysis_batch_size", value=10),
        ]

        result = _parse_db_settings(db_settings)

        assert result == {
            "app": {"debug": "true"},
            "database": {"url": "postgresql://localhost/test"},
            "sync": {"enabled": True},
            "analysis": {"batch_size": 10},
        }

    def test_parse_complex_nested_keys(self):
        """Test parsing settings with multiple underscore levels."""
        db_settings = [
            Mock(key="openai_api_key", value="sk-test"),
            Mock(key="openai_base_url", value="https://api.openai.com"),
            Mock(key="analysis_video_ai_enabled", value=True),
            Mock(key="stash_graphql_endpoint", value="/graphql"),
        ]

        result = _parse_db_settings(db_settings)

        # Should only split on first underscore
        assert result == {
            "openai": {"api_key": "sk-test", "base_url": "https://api.openai.com"},
            "analysis": {"video_ai_enabled": True},
            "stash": {"graphql_endpoint": "/graphql"},
        }

    def test_parse_boolean_values(self):
        """Test parsing boolean values from database."""
        db_settings = [
            Mock(key="debug", value=True),
            Mock(key="sync_enabled", value=False),
            Mock(key="analysis_auto_tag", value=True),
        ]

        result = _parse_db_settings(db_settings)

        assert result["debug"] is True
        assert result["sync"]["enabled"] is False
        assert result["analysis"]["auto_tag"] is True

    def test_parse_numeric_values(self):
        """Test parsing numeric values from database."""
        db_settings = [
            Mock(key="sync_interval", value=300),
            Mock(key="analysis_confidence_threshold", value=0.85),
            Mock(key="stash_timeout", value=60),
        ]

        result = _parse_db_settings(db_settings)

        assert result["sync"]["interval"] == 300
        assert result["analysis"]["confidence_threshold"] == 0.85
        assert result["stash"]["timeout"] == 60

    def test_parse_json_values(self):
        """Test parsing JSON/list values from database."""
        db_settings = [
            Mock(key="analysis_tags_to_ignore", value=["test", "demo"]),
            Mock(key="sync_excluded_folders", value=["/tmp", "/cache"]),
        ]

        result = _parse_db_settings(db_settings)

        assert result["analysis"]["tags_to_ignore"] == ["test", "demo"]
        assert result["sync"]["excluded_folders"] == ["/tmp", "/cache"]


class TestSettingsValidation:
    """Test settings validation during override application."""

    def test_validate_url_formats(self):
        """Test URL validation in settings."""
        settings_dict = {
            "stash": {"url": "invalid-url"},
            "openai": {"base_url": "not-a-url"},
        }

        # Valid URLs should be accepted
        valid_overrides = {
            "stash": {"url": "http://localhost:9999"},
            "openai": {"base_url": "https://api.openai.com/v1"},
        }

        _apply_stash_overrides(settings_dict, valid_overrides)
        _apply_openai_overrides(settings_dict, valid_overrides)

        assert settings_dict["stash"]["url"] == "http://localhost:9999"
        assert settings_dict["openai"]["base_url"] == "https://api.openai.com/v1"

    def test_validate_api_key_formats(self):
        """Test API key validation."""
        settings_dict = {"stash": {"api_key": None}, "openai": {"api_key": None}}

        # Test various API key formats
        overrides = {
            "stash": {"api_key": "valid-stash-key-123"},
            "openai": {"api_key": "sk-proj-abcdef123456"},
        }

        _apply_stash_overrides(settings_dict, overrides)
        _apply_openai_overrides(settings_dict, overrides)

        assert settings_dict["stash"]["api_key"] == "valid-stash-key-123"
        assert settings_dict["openai"]["api_key"] == "sk-proj-abcdef123456"

    def test_validate_numeric_ranges(self):
        """Test numeric value validation."""
        settings_dict = {
            "analysis": {
                "confidence_threshold": 0.5,
                "frame_interval": 10,
                "batch_size": 5,
            }
        }

        # Test boundary values
        overrides = {
            "analysis": {
                "confidence_threshold": 0.95,  # Should be between 0 and 1
                "frame_interval": 30,  # Positive integer
                "batch_size": 100,  # Reasonable batch size
            }
        }

        _apply_section_overrides(settings_dict, overrides, "analysis")

        assert settings_dict["analysis"]["confidence_threshold"] == 0.95
        assert settings_dict["analysis"]["frame_interval"] == 30
        assert settings_dict["analysis"]["batch_size"] == 100


class TestLoadSettingsWithDbOverrides:

    @pytest.mark.asyncio
    async def test_load_settings_with_overrides(self):
        """Test loading settings with database overrides."""
        # Mock database settings
        mock_db_settings = [
            Mock(
                id=1,
                key="stash_url",
                value="http://db-override-url",
                description="Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Mock(
                id=2,
                key="openai_api_key",
                value="sk-db-override",
                description="Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Mock(
                id=3,
                key="analysis_frame_interval",
                value=20,
                description="Test",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock the database session and query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_db_settings

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        # Mock AsyncSessionLocal
        with patch("app.core.settings_loader.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock base settings
            with patch("app.core.settings_loader.get_settings") as mock_get_settings:
                mock_base_settings = Mock()
                mock_base_settings.model_dump.return_value = {
                    "stash": {"url": "http://original-url", "api_key": None},
                    "openai": {"api_key": "sk-original", "model": "gpt-3.5-turbo"},
                    "analysis": {"frame_interval": 10, "ai_video_server_url": None},
                }
                mock_get_settings.return_value = mock_base_settings

                # Mock Settings class
                with patch("app.core.settings_loader.Settings") as mock_settings_class:
                    mock_settings_instance = Mock()
                    mock_settings_class.return_value = mock_settings_instance

                    result = await load_settings_with_db_overrides()

                    # Verify the Settings class was called with overridden values
                    called_args = mock_settings_class.call_args[1]
                    assert called_args["stash"]["url"] == "http://db-override-url"
                    assert called_args["openai"]["api_key"] == "sk-db-override"
                    assert called_args["analysis"]["frame_interval"] == 20

                    assert result == mock_settings_instance

    @pytest.mark.asyncio
    async def test_load_settings_no_overrides(self):
        """Test loading settings when no database overrides exist."""
        # Mock empty database settings
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with patch("app.core.settings_loader.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch("app.core.settings_loader.get_settings") as mock_get_settings:
                mock_base_settings = Mock()
                mock_base_settings.model_dump.return_value = {
                    "stash": {"url": "http://original"},
                    "openai": {"api_key": "sk-original"},
                }
                mock_get_settings.return_value = mock_base_settings

                with patch("app.core.settings_loader.Settings") as mock_settings_class:
                    await load_settings_with_db_overrides()

                    # Should be called with original values
                    called_args = mock_settings_class.call_args[1]
                    assert called_args["stash"]["url"] == "http://original"
                    assert called_args["openai"]["api_key"] == "sk-original"

    @pytest.mark.asyncio
    async def test_load_settings_database_error(self):
        """Test handling database errors during settings load."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")

        with patch("app.core.settings_loader.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with pytest.raises(Exception, match="Database error"):
                await load_settings_with_db_overrides()
