"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


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
