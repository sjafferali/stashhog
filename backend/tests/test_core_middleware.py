"""
Tests for custom middleware components.
"""

import time
import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.middleware import (
    CORSMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    @app.get("/slow")
    async def slow_endpoint():
        time.sleep(0.1)  # Simulate slow endpoint
        return {"message": "slow"}

    return app


class TestRequestIDMiddleware:
    """Test RequestIDMiddleware."""

    def test_request_id_generation(self, test_app):
        """Test that request ID is generated when not provided."""
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        # Verify it's a valid UUID
        uuid.UUID(response.headers["X-Request-ID"])

    def test_request_id_passthrough(self, test_app):
        """Test that existing request ID is passed through."""
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        request_id = str(uuid.uuid4())
        response = client.get("/test", headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == request_id

    def test_request_state_storage(self, test_app):
        """Test that request ID is stored in request state."""
        test_app.add_middleware(RequestIDMiddleware)

        @test_app.get("/check-state")
        async def check_state(request: Request):
            return {"request_id": getattr(request.state, "request_id", None)}

        client = TestClient(test_app)
        request_id = str(uuid.uuid4())
        response = client.get("/check-state", headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        assert response.json()["request_id"] == request_id


class TestLoggingMiddleware:
    """Test LoggingMiddleware."""

    @patch("app.core.middleware.logger")
    def test_request_logging(self, mock_logger, test_app):
        """Test that requests are logged."""
        test_app.add_middleware(LoggingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200

        # Check that logger.info was called twice (start and end)
        assert mock_logger.info.call_count == 2

        # Check start log
        start_call = mock_logger.info.call_args_list[0]
        assert start_call[0][0] == "Request started"
        assert start_call[1]["extra"]["method"] == "GET"
        assert start_call[1]["extra"]["path"] == "/test"

        # Check end log
        end_call = mock_logger.info.call_args_list[1]
        assert end_call[0][0] == "Request completed"
        assert end_call[1]["extra"]["status_code"] == 200
        assert "process_time" in end_call[1]["extra"]

    @patch("app.core.middleware.logger")
    def test_request_id_logging(self, mock_logger, test_app):
        """Test that request ID is included in logs."""
        # Middleware order matters - LoggingMiddleware must be added first, then RequestIDMiddleware
        test_app.add_middleware(LoggingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        request_id = str(uuid.uuid4())
        response = client.get("/test", headers={"X-Request-ID": request_id})
        assert response.status_code == 200

        # Check that request ID is in logs
        for call in mock_logger.info.call_args_list:
            assert call[1]["extra"]["request_id"] == request_id

    @patch("app.core.middleware.logger")
    def test_error_response_logging(self, mock_logger, test_app):
        """Test that error responses are logged."""
        test_app.add_middleware(LoggingMiddleware)
        client = TestClient(test_app)

        with pytest.raises(ValueError):
            client.get("/error")

        # When an exception is raised, the logging middleware still logs the request start
        assert mock_logger.info.call_count >= 1
        start_call = mock_logger.info.call_args_list[0]
        assert start_call[0][0] == "Request started"

    @patch("app.core.middleware.logger")
    def test_client_host_logging(self, mock_logger, test_app):
        """Test that client host is logged."""
        test_app.add_middleware(LoggingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200

        # Check that client host is logged
        start_call = mock_logger.info.call_args_list[0]
        assert "client" in start_call[1]["extra"]


class TestTimingMiddleware:
    """Test TimingMiddleware."""

    def test_process_time_header(self, test_app):
        """Test that process time is added to response headers."""
        test_app.add_middleware(TimingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        # Verify it's a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0

    def test_slow_endpoint_timing(self, test_app):
        """Test timing for slow endpoint."""
        test_app.add_middleware(TimingMiddleware)
        client = TestClient(test_app)

        response = client.get("/slow")
        assert response.status_code == 200
        process_time = float(response.headers["X-Process-Time"])
        # Should take at least 0.1 seconds
        assert process_time >= 0.1

    def test_multiple_middleware_timing(self, test_app):
        """Test timing with multiple middleware."""
        test_app.add_middleware(TimingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)
        test_app.add_middleware(LoggingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware."""

    def test_successful_request(self, test_app):
        """Test that successful requests pass through."""
        test_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    def test_error_propagation(self, test_app):
        """Test that errors are propagated to FastAPI error handlers."""
        test_app.add_middleware(ErrorHandlingMiddleware)
        client = TestClient(test_app)

        # Errors should be re-raised by the middleware
        with pytest.raises(ValueError):
            client.get("/error")

    def test_middleware_order(self, test_app):
        """Test error handling with multiple middleware."""
        test_app.add_middleware(ErrorHandlingMiddleware)
        test_app.add_middleware(TimingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)
        client = TestClient(test_app)

        # Since ErrorHandlingMiddleware re-raises exceptions,
        # the exception will be raised before other middleware can add headers
        with pytest.raises(ValueError):
            client.get("/error")


class TestCORSMiddleware:
    """Test CORSMiddleware."""

    def test_cors_headers_allowed_origin(self, test_app):
        """Test CORS headers for allowed origin."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["http://localhost:3000", "http://localhost:8080"],
            credentials=True,
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.get("/test", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert (
            response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        )
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_cors_headers_disallowed_origin(self, test_app):
        """Test CORS headers for disallowed origin."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["http://localhost:3000"],
            credentials=True,
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.get("/test", headers={"Origin": "http://evil.com"})
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_cors_wildcard_origin(self, test_app):
        """Test CORS with wildcard origin."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["*"],
            credentials=False,
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.get("/test", headers={"Origin": "http://example.com"})
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://example.com"

    def test_cors_preflight_request(self, test_app):
        """Test CORS preflight OPTIONS request."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["http://localhost:3000"],
            credentials=True,
            methods=["GET", "POST", "PUT", "DELETE"],
            headers=["Content-Type", "Authorization"],
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.options("/test", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert (
            response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        )
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert (
            response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE"
        )
        assert (
            response.headers["Access-Control-Allow-Headers"]
            == "Content-Type, Authorization"
        )
        assert response.headers["Access-Control-Max-Age"] == "86400"

    def test_cors_no_origin_header(self, test_app):
        """Test CORS when no origin header is present."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["*"],
            credentials=False,
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.get("/test")
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_custom_configuration(self, test_app):
        """Test CORS with custom configuration."""
        cors_middleware = CORSMiddleware(
            test_app,
            origins=["http://app.example.com"],
            credentials=True,
            methods=["GET", "POST"],
            headers=["X-Custom-Header"],
        )
        test_app.middleware("http")(cors_middleware)
        client = TestClient(test_app)

        response = client.options("/test", headers={"Origin": "http://app.example.com"})
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Methods"] == "GET, POST"
        assert response.headers["Access-Control-Allow-Headers"] == "X-Custom-Header"


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    def test_all_middleware_together(self, test_app):
        """Test all middleware working together."""
        # Add all middleware
        test_app.add_middleware(ErrorHandlingMiddleware)
        test_app.add_middleware(TimingMiddleware)
        test_app.add_middleware(LoggingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)

        cors_middleware = CORSMiddleware(
            test_app,
            origins=["http://localhost:3000"],
            credentials=True,
        )
        test_app.middleware("http")(cors_middleware)

        client = TestClient(test_app)

        # Test successful request
        request_id = str(uuid.uuid4())
        response = client.get(
            "/test",
            headers={
                "X-Request-ID": request_id,
                "Origin": "http://localhost:3000",
            },
        )
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == request_id
        assert "X-Process-Time" in response.headers
        assert (
            response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        )

    @patch("app.core.middleware.logger")
    def test_middleware_error_handling(self, mock_logger, test_app):
        """Test middleware behavior with errors."""
        test_app.add_middleware(ErrorHandlingMiddleware)
        test_app.add_middleware(TimingMiddleware)
        test_app.add_middleware(LoggingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)

        client = TestClient(test_app)

        # Since ErrorHandlingMiddleware re-raises exceptions,
        # we expect the exception to be raised
        with pytest.raises(ValueError):
            client.get("/error")

        # Verify that logging of the request start still occurred
        assert mock_logger.info.call_count >= 1
        start_call = mock_logger.info.call_args_list[0]
        assert start_call[0][0] == "Request started"

    def test_middleware_order_matters(self, test_app):
        """Test that middleware order affects behavior."""
        # First add timing, then request ID
        test_app.add_middleware(TimingMiddleware)
        test_app.add_middleware(RequestIDMiddleware)

        @test_app.get("/check-timing")
        async def check_timing(request: Request):
            # Simulate some processing
            time.sleep(0.05)
            return {
                "has_request_id": hasattr(request.state, "request_id"),
            }

        client = TestClient(test_app)
        response = client.get("/check-timing")
        assert response.status_code == 200
        assert response.json()["has_request_id"] is True

        # Process time should include all middleware
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0.05
