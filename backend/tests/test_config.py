"""Tests for configuration module."""

import os

import pytest

from app.core.config import Settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test default settings are loaded correctly."""
        settings = Settings()
        assert settings.app.name == "StashHog"
        # Check debug state (may be overridden by .env file)
        assert isinstance(settings.app.debug, bool)
        assert settings.database.url == "sqlite:///./stashhog.db"
        assert settings.stash.url == "http://localhost:9999"
        assert settings.openai.model == "gpt-4"

    def test_settings_from_env(self, monkeypatch):
        """Test settings can be loaded from environment variables."""
        # Set environment variables
        monkeypatch.setenv("APP_NAME", "TestApp")
        monkeypatch.setenv("APP_DEBUG", "true")
        monkeypatch.setenv("DATABASE__URL", "postgresql://test")
        monkeypatch.setenv("STASH__API_KEY", "test-key")

        # Create new settings instance
        settings = Settings()

        assert settings.app.name == "TestApp"
        assert settings.app.debug is True
        assert settings.database.url == "postgresql://test"
        assert settings.stash.api_key == "test-key"

    def test_optional_fields(self):
        """Test optional fields can be None."""
        settings = Settings()
        # These should be None by default unless set in environment
        if not os.getenv("STASH_API_KEY"):
            # Empty string is returned instead of None for unset optional fields
            assert settings.stash.api_key == "" or settings.stash.api_key is None
        if not os.getenv("OPENAI__API_KEY"):
            assert settings.openai.api_key == "" or settings.openai.api_key is None

    @pytest.mark.parametrize(
        "field_path,expected_type",
        [
            ("app.name", str),
            ("app.debug", bool),
            ("database.url", str),
            ("stash.url", str),
            ("openai.model", str),
            ("security.secret_key", str),
        ],
    )
    def test_field_types(self, field_path, expected_type):
        """Test settings fields have correct types."""
        settings = Settings()
        # Navigate nested attributes
        value = settings
        for attr in field_path.split("."):
            value = getattr(value, attr)
        assert isinstance(value, expected_type)
