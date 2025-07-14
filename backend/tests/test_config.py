"""Tests for configuration module."""
import os
import pytest
from app.core.config import Settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test default settings are loaded correctly."""
        settings = Settings()
        assert settings.APP_NAME == "StashHog"
        assert settings.DEBUG is False
        assert settings.DATABASE_URL == "sqlite:///./stashhog.db"
        assert settings.STASH_URL == "http://localhost:9999"
        assert settings.OPENAI_MODEL == "gpt-4"

    def test_settings_from_env(self, monkeypatch):
        """Test settings can be loaded from environment variables."""
        # Set environment variables
        monkeypatch.setenv("APP_NAME", "TestApp")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("STASH_API_KEY", "test-key")
        
        # Create new settings instance
        settings = Settings()
        
        assert settings.APP_NAME == "TestApp"
        assert settings.DEBUG is True
        assert settings.DATABASE_URL == "postgresql://test"
        assert settings.STASH_API_KEY == "test-key"

    def test_optional_fields(self):
        """Test optional fields can be None."""
        settings = Settings()
        # These should be None by default unless set in environment
        if not os.getenv("STASH_API_KEY"):
            assert settings.STASH_API_KEY is None
        if not os.getenv("OPENAI_API_KEY"):
            assert settings.OPENAI_API_KEY is None

    @pytest.mark.parametrize(
        "field_name,expected_type",
        [
            ("APP_NAME", str),
            ("DEBUG", bool),
            ("DATABASE_URL", str),
            ("STASH_URL", str),
            ("OPENAI_MODEL", str),
            ("SECRET_KEY", str),
        ],
    )
    def test_field_types(self, field_name, expected_type):
        """Test settings fields have correct types."""
        settings = Settings()
        value = getattr(settings, field_name)
        assert isinstance(value, expected_type)