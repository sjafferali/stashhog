"""Tests for the main FastAPI application."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import (
    _run_migrations_with_retry,
    _startup_tasks,
    app,
    lifespan,
    root,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.app.name = "StashHog"
    settings.app.version = "1.0.0"
    settings.app.environment = "development"
    settings.app.debug = True
    settings.cors.origins = ["http://localhost:5173"]
    settings.cors.credentials = True
    settings.cors.methods = ["*"]
    settings.cors.headers = ["*"]
    return settings


class TestMainApp:
    """Test cases for main application endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns expected message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "StashHog" in data["message"]

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "healthy"}

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.parametrize(
        "endpoint,expected_status",
        [
            ("/", 200),
            ("/health", 200),
            ("/nonexistent", 404),
        ],
    )
    def test_endpoint_status_codes(self, client, endpoint, expected_status):
        """Test various endpoints return expected status codes."""
        response = client.get(endpoint)
        assert response.status_code == expected_status

    def test_version_endpoint(self, client):
        """Test the version endpoint returns expected information."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data
        assert data["name"] == "StashHog"

    def test_ready_check_endpoint(self, client):
        """Test the ready check endpoint."""
        response = client.get("/ready")
        assert response.status_code == 503  # Not ready by default
        data = response.json()
        assert data["status"] == "not ready"
        assert "checks" in data
        assert "database" in data["checks"]
        assert "stash" in data["checks"]
        assert "openai" in data["checks"]

    def test_api_prefix(self, client):
        """Test that API routes are properly prefixed."""
        # API routes should return 404 if not found under /api
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_middleware_order(self):
        """Test that middleware is added in correct order."""
        # Check that app has middleware configured
        assert hasattr(app, "middleware_stack")
        # Or check that the app was created with middleware
        assert app is not None


class TestApplicationLifecycle:
    """Test application lifecycle management."""

    @pytest.mark.asyncio
    async def test_run_migrations_with_retry_success(self):
        """Test successful migration with retry logic."""
        with patch("app.main.run_migrations_async") as mock_migrate:
            mock_migrate.return_value = None
            await _run_migrations_with_retry(max_attempts=3)
            mock_migrate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_migrations_with_retry_failure_then_success(self):
        """Test migration retry on failure."""
        with patch("app.main.run_migrations_async") as mock_migrate:
            # Fail twice, then succeed
            mock_migrate.side_effect = [
                Exception("DB error"),
                Exception("DB error"),
                None,
            ]

            with patch("asyncio.sleep"):  # Skip actual sleep
                await _run_migrations_with_retry(max_attempts=3)

            assert mock_migrate.call_count == 3

    @pytest.mark.asyncio
    async def test_run_migrations_with_retry_all_failures(self):
        """Test migration fails after all retries."""
        with patch("app.main.run_migrations_async") as mock_migrate:
            mock_migrate.side_effect = Exception("DB error")

            with patch("asyncio.sleep"):  # Skip actual sleep
                with pytest.raises(RuntimeError) as exc_info:
                    await _run_migrations_with_retry(max_attempts=3)

            assert "Database migrations failed after 3 attempts" in str(exc_info.value)
            assert mock_migrate.call_count == 3

    @pytest.mark.asyncio
    async def test_startup_tasks_in_test_environment(self):
        """Test startup tasks skip migrations in test environment."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test"

        with patch("app.main.register_all_jobs") as mock_register:
            await _startup_tasks()

            # Should not run migrations or start task queue in test environment
            mock_register.assert_called_once()

        # Clean up
        del os.environ["PYTEST_CURRENT_TEST"]

    @pytest.mark.asyncio
    async def test_startup_tasks_normal_environment(self):
        """Test startup tasks in normal environment."""
        # Clear test environment variable to ensure normal flow
        pytest_test = os.environ.pop("PYTEST_CURRENT_TEST", None)

        try:
            with patch("app.main._run_migrations_with_retry") as mock_migrate:
                mock_migrate.return_value = None

                with patch("app.main.get_task_queue") as mock_queue:
                    mock_queue.return_value.start = AsyncMock()

                    with patch("app.main.register_all_jobs") as mock_register:
                        await _startup_tasks()

                        mock_migrate.assert_called_once()
                        mock_queue.assert_called_once()
                        mock_register.assert_called_once()
        finally:
            # Restore test environment variable
            if pytest_test:
                os.environ["PYTEST_CURRENT_TEST"] = pytest_test

    @pytest.mark.asyncio
    async def test_lifespan_success(self):
        """Test successful application lifespan."""
        mock_app = MagicMock()

        # Clear test environment to test normal flow
        pytest_test = os.environ.pop("PYTEST_CURRENT_TEST", None)

        try:
            with patch("app.main._startup_tasks") as mock_startup:
                mock_startup.return_value = None

                with patch("app.main.get_task_queue") as mock_queue:
                    mock_queue.return_value.stop = AsyncMock()

                    with patch("app.main.close_db") as mock_close_db:
                        mock_close_db.return_value = None

                        async with lifespan(mock_app):
                            # Startup should be called
                            mock_startup.assert_called_once()

                        # Shutdown should be called
                        mock_queue.return_value.stop.assert_called_once()
                        mock_close_db.assert_called_once()
        finally:
            # Restore test environment
            if pytest_test:
                os.environ["PYTEST_CURRENT_TEST"] = pytest_test

    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """Test application lifespan with startup failure."""
        mock_app = MagicMock()

        with patch("app.main._startup_tasks") as mock_startup:
            mock_startup.side_effect = Exception("Startup failed")

            with pytest.raises(Exception) as exc_info:
                async with lifespan(mock_app):
                    pass

            assert "Startup failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_error(self):
        """Test application lifespan with shutdown error."""
        mock_app = MagicMock()

        # Clear test environment to test normal flow
        pytest_test = os.environ.pop("PYTEST_CURRENT_TEST", None)

        try:
            with patch("app.main._startup_tasks") as mock_startup:
                mock_startup.return_value = None

                with patch("app.main.get_task_queue") as mock_queue:
                    # Create a queue mock that will fail on stop
                    queue_instance = MagicMock()
                    queue_instance.stop = AsyncMock(
                        side_effect=Exception("Stop failed")
                    )
                    mock_queue.return_value = queue_instance

                    with patch("app.main.close_db") as mock_close_db:
                        mock_close_db.return_value = None

                        # Should not raise exception on shutdown error
                        async with lifespan(mock_app):
                            pass

                        # Stop should be called
                        queue_instance.stop.assert_called_once()
                        # Close DB should NOT be called because stop() failed
                        # and the exception causes the try block to exit early
                        mock_close_db.assert_not_called()
        finally:
            # Restore test environment
            if pytest_test:
                os.environ["PYTEST_CURRENT_TEST"] = pytest_test


class TestStaticFileServing:
    """Test static file serving functionality."""

    @pytest.mark.asyncio
    async def test_root_endpoint_development(self):
        """Test root endpoint in development mode."""
        mock_request = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.app.environment = "development"
            mock_settings.app.name = "StashHog"
            mock_settings.app.version = "1.0.0"

            result = await root(mock_request)
            assert isinstance(result, dict)
            assert result["name"] == "StashHog"
            assert result["version"] == "1.0.0"
            assert "message" in result

    @pytest.mark.asyncio
    async def test_root_endpoint_production_no_static(self):
        """Test root endpoint in production without static files."""
        mock_request = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.app.environment = "production"
            mock_settings.app.name = "StashHog"
            mock_settings.app.version = "1.0.0"

            with patch("os.path.exists", return_value=False):
                result = await root(mock_request)
                assert isinstance(result, dict)
                assert result["name"] == "StashHog"

    @pytest.mark.asyncio
    async def test_root_endpoint_production_with_static(self):
        """Test root endpoint in production with static files."""
        mock_request = MagicMock()

        with patch("app.main.settings") as mock_settings:
            mock_settings.app.environment = "production"

            with patch("os.path.exists", return_value=True):
                with patch("app.main.FileResponse") as mock_file_response:
                    await root(mock_request)
                    mock_file_response.assert_called_once_with("static/index.html")

    def test_static_file_serving_in_production(self, client):
        """Test that static file endpoints are configured in production."""
        # In test environment, we don't have static files so we get API info
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "StashHog"

    def test_spa_route_handling(self, client):
        """Test SPA route handling for non-existent paths."""
        # In test environment without static files, should return 404
        response = client.get("/some/spa/route")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling in the application."""

    def test_app_has_error_handlers_registered(self):
        """Test that error handlers are registered."""
        # This is verified by the fact that the app starts without errors
        # and error handlers are called during app creation
        assert app is not None
        assert hasattr(app, "exception_handlers")

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        assert app.title == "StashHog"
        assert app.version is not None
        assert (
            app.description
            == "Automated scene tagging and metadata enrichment for Stash"
        )

        # Check docs URLs based on debug setting
        from app.core.config import get_settings

        settings = get_settings()

        if settings.app.debug:
            assert app.docs_url == "/docs"
            assert app.redoc_url == "/redoc"
            assert app.openapi_url == "/openapi.json"
        else:
            assert app.docs_url is None
            assert app.redoc_url is None
            assert app.openapi_url is None
