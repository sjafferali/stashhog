"""Tests for core dependency injection functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    PaginationParams,
    _apply_setting_override,
    _get_base_settings_dict,
    get_analysis_service,
    get_current_user,
    get_db,
    get_job_service,
    get_openai_client,
    get_stash_client,
    get_stash_service,
    get_sync_service,
    require_auth,
)


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = MagicMock()

    # App settings
    settings.app = MagicMock()
    settings.app.name = "StashHog"
    settings.app.version = "1.0.0"
    settings.app.environment = "test"
    settings.app.debug = True

    # Stash settings
    settings.stash = MagicMock()
    settings.stash.url = "http://localhost:9999"
    settings.stash.api_key = "test-api-key"
    settings.stash.timeout = 30
    settings.stash.max_retries = 3

    # OpenAI settings
    settings.openai = MagicMock()
    settings.openai.api_key = "test-openai-key"
    settings.openai.model = "gpt-4"
    settings.openai.base_url = None
    settings.openai.max_tokens = 500
    settings.openai.temperature = 0.7
    settings.openai.timeout = 60

    # Analysis settings
    settings.analysis = MagicMock()
    settings.analysis.batch_size = 10
    settings.analysis.max_concurrent = 5
    settings.analysis.confidence_threshold = 0.8
    settings.analysis.enable_ai = True
    settings.analysis.create_missing = True
    settings.analysis.ai_video_server_url = "http://localhost:8080"
    settings.analysis.frame_interval = 10
    settings.analysis.ai_video_threshold = 0.9
    settings.analysis.server_timeout = 300
    settings.analysis.create_markers = False

    # Additional settings needed for Settings creation
    settings.database = MagicMock()
    settings.security = MagicMock()
    settings.cors = MagicMock()
    settings.logging = MagicMock()
    settings.redis_url = None  # Still in Settings model but unused
    settings.max_workers = 4
    settings.task_timeout = 3600

    return settings


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestDatabaseDependency:
    """Test database dependency injection."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields a database session."""
        with patch("app.core.dependencies.AsyncSessionLocal") as mock_local:
            mock_session = AsyncMock()
            mock_local.return_value.__aenter__.return_value = mock_session

            async for session in get_db():
                assert session == mock_session

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_closes_on_exception(self):
        """Test get_db closes session even on exception."""
        # The get_db function uses a finally block to ensure session.close()
        # is called even on exception. Let's test this behavior.
        with patch("app.core.dependencies.AsyncSessionLocal") as mock_local:
            mock_session = AsyncMock()
            mock_session.close = AsyncMock()

            # Mock the async context manager
            mock_local.return_value.__aenter__.return_value = mock_session
            mock_local.return_value.__aexit__.return_value = None

            # Use the generator and trigger an exception
            gen = get_db()
            session = await gen.__anext__()

            # Verify we got the session
            assert session == mock_session

            # Now raise an exception and close the generator
            with pytest.raises(Exception):
                await gen.athrow(Exception("Test error"))

            # The session.close() should have been called in the finally block
            mock_session.close.assert_called_once()


class TestSettingsOverrides:
    """Test settings override functionality."""

    def test_get_base_settings_dict(self, mock_settings):
        """Test base settings dictionary creation."""
        result = _get_base_settings_dict(mock_settings)

        assert "stash" in result
        assert result["stash"]["url"] == "http://localhost:9999"
        assert result["stash"]["api_key"] == "test-api-key"

        assert "openai" in result
        assert result["openai"]["api_key"] == "test-openai-key"
        assert result["openai"]["model"] == "gpt-4"

        assert "analysis" in result
        assert result["analysis"]["batch_size"] == 10
        assert result["analysis"]["confidence_threshold"] == 0.8

    def test_apply_setting_override_string(self):
        """Test applying string setting override."""
        settings_dict = {"stash": {"url": "old-url"}}
        _apply_setting_override(settings_dict, "stash_url", "new-url")
        assert settings_dict["stash"]["url"] == "new-url"

    def test_apply_setting_override_float(self):
        """Test applying float setting override."""
        settings_dict = {"analysis": {"confidence_threshold": 0.5}}
        _apply_setting_override(settings_dict, "analysis_confidence_threshold", "0.9")
        assert settings_dict["analysis"]["confidence_threshold"] == 0.9

    def test_apply_setting_override_int(self):
        """Test applying int setting override."""
        settings_dict = {"analysis": {"frame_interval": 5}}
        _apply_setting_override(settings_dict, "video_ai_frame_interval", "20")
        assert settings_dict["analysis"]["frame_interval"] == 20

    def test_apply_setting_override_bool_true(self):
        """Test applying boolean setting override - true values."""
        settings_dict = {"analysis": {"create_markers": False}}

        # Test various true values
        for value in [True, "true", "True", "TRUE", "1", "yes"]:
            settings_dict["analysis"]["create_markers"] = False
            _apply_setting_override(settings_dict, "analysis_create_markers", value)
            assert settings_dict["analysis"]["create_markers"] is True

    def test_apply_setting_override_bool_false(self):
        """Test applying boolean setting override - false values."""
        settings_dict = {"analysis": {"create_markers": True}}

        # Test various false values
        for value in [False, "false", "False", "FALSE", "0", "no"]:
            settings_dict["analysis"]["create_markers"] = True
            _apply_setting_override(settings_dict, "analysis_create_markers", value)
            assert settings_dict["analysis"]["create_markers"] is False

    def test_apply_setting_override_none(self):
        """Test applying None value is ignored."""
        settings_dict = {"stash": {"url": "original"}}
        _apply_setting_override(settings_dict, "stash_url", None)
        assert settings_dict["stash"]["url"] == "original"

    def test_apply_setting_override_unknown_key(self):
        """Test unknown keys are ignored."""
        settings_dict = {"stash": {}}
        _apply_setting_override(settings_dict, "unknown_key", "value")
        # Should not raise error or modify dict
        assert settings_dict == {"stash": {}}

    def test_apply_setting_override_conversion_error(self):
        """Test conversion errors are ignored."""
        settings_dict = {"analysis": {"confidence_threshold": 0.5}}
        _apply_setting_override(
            settings_dict, "analysis_confidence_threshold", "invalid"
        )
        # Should keep original value
        assert settings_dict["analysis"]["confidence_threshold"] == 0.5

    @pytest.mark.skip(reason="Requires complex mocking of pydantic settings")
    @pytest.mark.asyncio
    async def test_get_settings_with_overrides_no_db_settings(
        self, mock_db_session, mock_settings
    ):
        """Test settings with no database overrides."""
        pass

    @pytest.mark.skip(reason="Requires complex mocking of pydantic settings")
    @pytest.mark.asyncio
    async def test_get_settings_with_overrides_with_db_settings(
        self, mock_db_session, mock_settings
    ):
        """Test settings with database overrides."""
        pass


class TestServiceDependencies:
    """Test service dependency injection."""

    def test_get_stash_client(self, mock_settings):
        """Test Stash client creation."""
        with patch("app.core.dependencies.get_settings_with_overrides") as mock_get:
            mock_get.return_value = mock_settings

            client = get_stash_client(settings=mock_settings)

            assert client is not None
            # Client should be initialized with settings

    def test_get_openai_client_with_key(self, mock_settings):
        """Test OpenAI client creation with API key."""
        with patch("app.core.dependencies.get_settings_with_overrides") as mock_get:
            mock_get.return_value = mock_settings

            client = get_openai_client(settings=mock_settings)

            assert client is not None

    def test_get_openai_client_without_key(self, mock_settings):
        """Test OpenAI client returns None without API key."""
        mock_settings.openai.api_key = ""

        with patch("app.core.dependencies.get_settings_with_overrides") as mock_get:
            mock_get.return_value = mock_settings

            client = get_openai_client(settings=mock_settings)

            assert client is None

    def test_get_stash_service(self, mock_settings):
        """Test Stash service creation."""
        client = get_stash_service(settings=mock_settings)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_sync_service(self, mock_db_session):
        """Test Sync service creation."""
        mock_stash = MagicMock()

        service = await get_sync_service(stash_service=mock_stash, db=mock_db_session)

        assert service is not None

    def test_get_analysis_service(self, mock_settings):
        """Test Analysis service creation."""
        mock_openai = MagicMock()
        mock_stash = MagicMock()

        service = get_analysis_service(
            openai_client=mock_openai, stash_service=mock_stash, settings=mock_settings
        )

        assert service is not None

    def test_get_analysis_service_no_openai(self, mock_settings):
        """Test Analysis service raises error without OpenAI client."""
        mock_stash = MagicMock()

        with pytest.raises(ValueError, match="OpenAI client is required"):
            get_analysis_service(
                openai_client=None, stash_service=mock_stash, settings=mock_settings
            )

    def test_get_job_service(self):
        """Test Job service retrieval."""
        with patch("app.services.job_service.job_service") as mock_service:
            result = get_job_service()
            assert result == mock_service


class TestAuthenticationDependencies:
    """Test authentication dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_no_credentials(self, mock_settings):
        """Test get_current_user without credentials."""
        result = await get_current_user(credentials=None, settings=mock_settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_with_credentials(self, mock_settings):
        """Test get_current_user with credentials (placeholder)."""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "test-token"

        result = await get_current_user(
            credentials=mock_credentials, settings=mock_settings
        )

        # Currently returns None (no auth implemented)
        assert result is None

    @pytest.mark.asyncio
    async def test_require_auth_no_user(self):
        """Test require_auth raises exception without user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(user=None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication required"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_require_auth_with_user(self):
        """Test require_auth passes with user."""
        user = {"id": 1, "username": "test"}
        result = await require_auth(user=user)
        assert result == user


class TestPaginationParams:
    """Test pagination parameter handling."""

    def test_pagination_defaults(self):
        """Test default pagination parameters."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20
        assert params.sort is None
        assert params.offset == 0

    def test_pagination_custom_values(self):
        """Test custom pagination parameters."""
        params = PaginationParams(page=3, size=50, sort="-created_at")
        assert params.page == 3
        assert params.size == 50
        assert params.sort == "-created_at"
        assert params.offset == 100  # (3-1) * 50

    def test_pagination_min_page(self):
        """Test page number is at least 1."""
        params = PaginationParams(page=0)
        assert params.page == 1
        assert params.offset == 0

    def test_pagination_min_size(self):
        """Test size is at least 1."""
        params = PaginationParams(size=0)
        assert params.size == 1

    def test_pagination_max_size(self):
        """Test size is capped at 100."""
        params = PaginationParams(size=200)
        assert params.size == 100

    def test_pagination_offset_calculation(self):
        """Test offset calculation for various pages."""
        # Page 1
        params = PaginationParams(page=1, size=10)
        assert params.offset == 0

        # Page 2
        params = PaginationParams(page=2, size=10)
        assert params.offset == 10

        # Page 5 with size 25
        params = PaginationParams(page=5, size=25)
        assert params.offset == 100
