"""Comprehensive tests for settings API routes."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.dependencies import get_db
from app.main import app
from app.models import Setting


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    """Create test client with mocked dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db

    from fastapi.testclient import TestClient

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings_list():
    """Create mock settings list."""
    return [
        Mock(
            spec=Setting,
            key="stash_url",
            value="http://localhost:9999",
            description="Stash URL",
        ),
        Mock(
            spec=Setting,
            key="openai_api_key",
            value="sk-test",
            description="OpenAI API key",
        ),
        Mock(
            spec=Setting,
            key="sync_batch_size",
            value=100,
            description="Sync batch size",
        ),
    ]


@pytest.fixture
def mock_base_settings():
    """Create mock base settings."""
    settings = Mock()
    settings.stash.url = "http://default:9999"
    settings.stash.api_key = "default-key"
    settings.openai.api_key = "sk-default"
    settings.openai.model = "gpt-4"
    settings.openai.base_url = None
    settings.analysis.confidence_threshold = 0.7
    settings.analysis.ai_video_server_url = "http://localhost:8084"
    settings.analysis.frame_interval = 2
    settings.analysis.ai_video_threshold = 0.3
    settings.analysis.server_timeout = 3700
    settings.analysis.create_markers = True
    settings.app.name = "StashHog"
    settings.app.version = "1.0.0"
    return settings


@pytest.fixture
def mock_overridden_settings():
    """Create mock overridden settings."""
    settings = Mock()
    settings.stash.url = "http://override:9999"
    settings.stash.api_key = "override-key"
    settings.openai.api_key = "sk-override"
    settings.openai.model = "gpt-4"
    settings.openai.base_url = None
    settings.analysis.confidence_threshold = 0.8
    settings.analysis.ai_video_server_url = "http://localhost:8084"
    settings.analysis.frame_interval = 2
    settings.analysis.ai_video_threshold = 0.3
    settings.analysis.server_timeout = 3700
    settings.analysis.create_markers = True
    settings.app.name = "StashHog"
    settings.app.version = "1.0.0"
    return settings


class TestSettingsRoutes:
    """Test settings API routes."""

    def test_list_settings(
        self,
        client,
        mock_db,
        mock_settings_list,
        mock_base_settings,
        mock_overridden_settings,
    ):
        """Test listing all settings with source information."""
        # Mock database query
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_settings_list
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        # Mock dependencies
        from app.core.dependencies import get_settings, get_settings_with_overrides

        app.dependency_overrides[get_settings] = lambda: mock_base_settings
        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.get("/api/settings/")
            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert isinstance(data, list)
            assert len(data) > 0

            # Find specific settings
            stash_url_setting = next((s for s in data if s["key"] == "stash.url"), None)
            assert stash_url_setting is not None
            assert stash_url_setting["source"] == "database"
            assert stash_url_setting["db_value"] == "http://localhost:9999"
            assert stash_url_setting["editable"] is True

            # Check secret masking
            api_key_setting = next(
                (s for s in data if s["key"] == "openai.api_key"), None
            )
            assert api_key_setting is not None
            assert api_key_setting["value"] == "********"  # Should be masked

            # Check read-only settings
            app_name_setting = next((s for s in data if s["key"] == "app.name"), None)
            assert app_name_setting is not None
            assert app_name_setting["source"] == "config"
            assert app_name_setting["editable"] is False
            assert app_name_setting["value"] == "StashHog"

        finally:
            # Clean up overrides
            app.dependency_overrides.pop(get_settings, None)
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    def test_get_setting_success(self, client, mock_db):
        """Test getting a single setting successfully."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "sync_batch_size"
        mock_setting.value = 100
        mock_setting.description = "Sync batch size"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        response = client.get("/api/settings/sync_batch_size")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "sync_batch_size"
        assert data["value"] == 100
        assert data["description"] == "Sync batch size"

    def test_get_setting_not_found(self, client, mock_db):
        """Test getting a non-existent setting."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/settings/non_existent")
        assert response.status_code == 404
        data = response.json()
        assert "Setting not found" in data["detail"]

    def test_update_single_setting_existing(self, client, mock_db):
        """Test updating an existing setting."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "sync_batch_size"
        mock_setting.value = 100

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        response = client.put("/api/settings/sync_batch_size", json={"value": 200})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["key"] == "sync_batch_size"
        assert mock_setting.value == 200
        mock_db.commit.assert_called_once()

    def test_update_single_setting_create_new(self, client, mock_db):
        """Test creating a new setting via update."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.put("/api/settings/new_setting", json={"value": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["key"] == "new_setting"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_update_single_setting_plain_value(self, client, mock_db):
        """Test updating setting with plain value (not JSON object)."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "sync_batch_size"
        mock_setting.value = 100

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        # Send plain value instead of object
        response = client.put("/api/settings/sync_batch_size", json=300)
        assert response.status_code == 200
        assert mock_setting.value == 300

    def test_update_multiple_settings_success(self, client, mock_db):
        """Test updating multiple settings at once."""
        # Mock existing settings
        mock_settings = {
            "sync_batch_size": Mock(spec=Setting, key="sync_batch_size", value=100),
            "openai_model": Mock(
                spec=Setting, key="openai_model", value="gpt-3.5-turbo"
            ),
        }

        async def mock_execute(query):
            result = Mock()
            # Check which setting is being queried
            query_str = str(query)
            if "sync_batch_size" in query_str:
                result.scalar_one_or_none.return_value = mock_settings[
                    "sync_batch_size"
                ]
            elif "openai_model" in query_str:
                result.scalar_one_or_none.return_value = mock_settings["openai_model"]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        update_data = {
            "sync_batch_size": 200,
            "openai_model": "gpt-4",
            "analysis_confidence_threshold": 0.9,  # New setting
        }

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["updated_fields"]) == 3
        assert "sync_batch_size" in data["updated_fields"]
        assert "openai_model" in data["updated_fields"]
        assert "analysis_confidence_threshold" in data["updated_fields"]
        assert data["requires_restart"] is False  # None of these require restart

    def test_update_multiple_settings_delete(self, client, mock_db):
        """Test deleting settings by setting them to null."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "sync_batch_size"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        update_data = {
            "sync_batch_size": None,  # Delete this setting
        }

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["deleted_fields"]) == 1
        assert "sync_batch_size" in data["deleted_fields"]
        mock_db.delete.assert_called_once_with(mock_setting)

    def test_update_multiple_settings_requires_restart(self, client, mock_db):
        """Test that updating certain settings triggers restart requirement."""
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "stash_url"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        update_data = {
            "stash_url": "http://new-url:9999",
        }

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["requires_restart"] is True  # stash_url changes require restart

    def test_update_multiple_settings_invalid_key(self, client, mock_db):
        """Test updating with invalid setting key."""
        update_data = {
            "invalid_key": "value",
        }

        response = client.put("/api/settings/", json=update_data)
        assert response.status_code == 400
        data = response.json()
        assert "Unknown setting key: invalid_key" in data["detail"]

    @patch("app.services.stash_service.StashService")
    def test_test_stash_connection_success(
        self, mock_stash_class, client, mock_overridden_settings
    ):
        """Test successful Stash connection test."""
        # Mock StashService instance
        mock_stash_instance = Mock()
        mock_stash_instance.test_connection = AsyncMock(return_value=True)
        mock_stash_class.return_value = mock_stash_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post(
                "/api/settings/test-stash",
                json={"url": "http://test:9999", "api_key": "test-key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "stash"
            assert data["success"] is True
            assert "Successfully connected" in data["message"]

            # Verify StashService was created with test credentials
            mock_stash_class.assert_called_with(
                stash_url="http://test:9999", api_key="test-key"
            )
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    @patch("app.services.stash_service.StashService")
    def test_test_stash_connection_failure(
        self, mock_stash_class, client, mock_overridden_settings
    ):
        """Test failed Stash connection test."""
        # Mock StashService instance that fails
        mock_stash_instance = Mock()
        mock_stash_instance.test_connection = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_stash_class.return_value = mock_stash_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post("/api/settings/test-stash", json={})
            assert response.status_code == 200  # Endpoint returns 200 even on failure
            data = response.json()
            assert data["service"] == "stash"
            assert data["success"] is False
            assert "Connection refused" in data["message"]
            assert "Connection refused" in data["details"]["error"]
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    def test_test_stash_connection_no_url(self, client):
        """Test Stash connection test with no URL configured."""
        # Mock settings with no URL
        mock_settings = Mock()
        mock_settings.stash.url = None
        mock_settings.stash.api_key = None

        # Also mock stash service to prevent import issues
        mock_stash_service = Mock()

        from app.core.dependencies import get_settings_with_overrides, get_stash_service

        app.dependency_overrides[get_settings_with_overrides] = lambda: mock_settings
        app.dependency_overrides[get_stash_service] = lambda: mock_stash_service

        try:
            response = client.post("/api/settings/test-stash", json={})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "No Stash URL configured" in data["message"]
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)
            app.dependency_overrides.pop(get_stash_service, None)

    @patch("openai.OpenAI")
    def test_test_openai_connection_success(
        self, mock_openai_class, client, mock_overridden_settings
    ):
        """Test successful OpenAI connection test."""
        # Mock OpenAI client
        mock_openai_instance = Mock()
        mock_model = Mock()
        mock_model.id = "gpt-4"
        mock_models_response = Mock()
        mock_models_response.data = [mock_model]
        mock_openai_instance.models.list.return_value = mock_models_response
        mock_openai_class.return_value = mock_openai_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post(
                "/api/settings/test-openai",
                json={"api_key": "sk-test-key", "model": "gpt-4"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "openai"
            assert data["success"] is True
            assert "Successfully connected" in data["message"]
            assert data["details"]["model"] == "gpt-4"
            assert len(data["details"]["available_models"]) > 0

            # Verify OpenAI client was created with test key
            mock_openai_class.assert_called_with(api_key="sk-test-key")
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    @patch("openai.OpenAI")
    def test_test_openai_connection_with_base_url(
        self, mock_openai_class, client, mock_overridden_settings
    ):
        """Test OpenAI connection test with custom base URL."""
        # Mock OpenAI client
        mock_openai_instance = Mock()
        mock_model = Mock()
        mock_model.id = "custom-model"
        mock_models_response = Mock()
        mock_models_response.data = [mock_model]
        mock_openai_instance.models.list.return_value = mock_models_response
        mock_openai_class.return_value = mock_openai_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post(
                "/api/settings/test-openai",
                json={
                    "api_key": "sk-test-key",
                    "model": "custom-model",
                    "base_url": "https://custom.openai.com/v1",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["details"]["base_url"] == "https://custom.openai.com/v1"

            # Verify OpenAI client was created with custom base URL
            mock_openai_class.assert_called_with(
                api_key="sk-test-key", base_url="https://custom.openai.com/v1"
            )
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    @patch("openai.OpenAI")
    def test_test_openai_connection_model_not_available(
        self, mock_openai_class, client, mock_overridden_settings
    ):
        """Test OpenAI connection test when model is not available."""
        # Mock OpenAI client with different model
        mock_openai_instance = Mock()
        mock_model = Mock()
        mock_model.id = "gpt-3.5-turbo"
        mock_models_response = Mock()
        mock_models_response.data = [mock_model]
        mock_openai_instance.models.list.return_value = mock_models_response
        mock_openai_class.return_value = mock_openai_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post(
                "/api/settings/test-openai",
                json={
                    "api_key": "sk-test-key",
                    "model": "gpt-4",  # Not in available models
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "openai"
            assert data["success"] is False
            assert "Model gpt-4 not available" in data["message"]
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    def test_test_openai_connection_no_api_key(self, client):
        """Test OpenAI connection test with no API key configured."""
        # Mock settings with no API key
        mock_settings = Mock()
        mock_settings.openai.api_key = None
        mock_settings.openai.model = "gpt-4"
        mock_settings.openai.base_url = None

        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = lambda: mock_settings

        try:
            response = client.post("/api/settings/test-openai", json={})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "No OpenAI API key configured" in data["message"]
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    @patch("openai.OpenAI")
    def test_test_openai_connection_api_error(
        self, mock_openai_class, client, mock_overridden_settings
    ):
        """Test OpenAI connection test with API error."""
        # Mock OpenAI client that raises exception
        mock_openai_instance = Mock()
        mock_openai_instance.models.list.side_effect = Exception("Invalid API key")
        mock_openai_class.return_value = mock_openai_instance

        # Mock dependencies
        from app.core.dependencies import get_settings_with_overrides

        app.dependency_overrides[get_settings_with_overrides] = (
            lambda: mock_overridden_settings
        )

        try:
            response = client.post(
                "/api/settings/test-openai", json={"api_key": "sk-invalid"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Invalid API key" in data["message"]
            assert "Invalid API key" in data["details"]["error"]
        finally:
            app.dependency_overrides.pop(get_settings_with_overrides, None)

    def test_settings_persistence(self, client, mock_db):
        """Test that settings changes persist across requests."""
        # First update a setting
        mock_setting = Mock(spec=Setting)
        mock_setting.key = "sync_batch_size"
        mock_setting.value = 100

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result

        response = client.put("/api/settings/sync_batch_size", json={"value": 250})
        assert response.status_code == 200
        assert mock_setting.value == 250

        # Verify it was saved
        mock_db.commit.assert_called_once()

    def test_concurrent_settings_updates(self, client, mock_db):
        """Test handling concurrent setting updates."""
        # This would test transaction isolation in a real database
        # For now, just verify the endpoint handles multiple updates correctly
        mock_settings = {
            "setting1": Mock(spec=Setting, key="sync_batch_size", value=100),
            "setting2": Mock(spec=Setting, key="openai_model", value="gpt-3.5"),
        }

        async def mock_execute(query):
            result = Mock()
            query_str = str(query)
            if "sync_batch_size" in query_str:
                result.scalar_one_or_none.return_value = mock_settings["setting1"]
            elif "openai_model" in query_str:
                result.scalar_one_or_none.return_value = mock_settings["setting2"]
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Update multiple settings
        response = client.put(
            "/api/settings/", json={"sync_batch_size": 200, "openai_model": "gpt-4"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["updated_fields"]) == 2
        assert "sync_batch_size" in data["updated_fields"]
        assert "openai_model" in data["updated_fields"]
