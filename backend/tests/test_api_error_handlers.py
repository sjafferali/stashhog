"""
Tests for API error handlers with edge cases.
"""

import json
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_handlers import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    register_error_handlers,
    validation_exception_handler,
)
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    JobConflictError,
    NotFoundError,
    RateLimitError,
    StashConnectionError,
    StashHogException,
    ValidationError,
)


class TestValidationExceptionHandler:
    """Test validation exception handler with edge cases."""

    @pytest.mark.asyncio
    async def test_validation_error_with_nested_fields(self):
        """Test validation error with deeply nested field paths."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "POST"

        # Create validation error with nested fields
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "loc": ["body", "user", "profile", "settings", "notifications"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["query", "filter", 0, "value"],
                "msg": "invalid value",
                "type": "type_error.str",
            },
        ]

        with patch("app.api.error_handlers.uuid4", return_value="test-uuid"):
            response = await validation_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = json.loads(response.body)

        # Check nested field formatting
        errors = content["validation_errors"]
        assert errors[0]["field"] == "body.user.profile.settings.notifications"
        assert errors[1]["field"] == "query.filter.0.value"

    @pytest.mark.asyncio
    async def test_validation_error_with_empty_location(self):
        """Test validation error with empty location."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "POST"

        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "loc": [],
                "msg": "invalid request",
                "type": "value_error",
            }
        ]

        response = await validation_exception_handler(request, exc)
        content = json.loads(response.body)

        # Should handle empty location gracefully
        assert content["validation_errors"][0]["field"] == ""

    @pytest.mark.asyncio
    async def test_validation_error_with_special_characters(self):
        """Test validation error with special characters in field names."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "POST"

        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [
            {
                "loc": ["body", "field-with-dash", "field.with.dot", "field[0]"],
                "msg": "invalid format",
                "type": "value_error.str.regex",
            }
        ]

        response = await validation_exception_handler(request, exc)
        content = json.loads(response.body)

        # Should preserve special characters
        assert (
            content["validation_errors"][0]["field"]
            == "body.field-with-dash.field.with.dot.field[0]"
        )

    @pytest.mark.asyncio
    async def test_validation_error_logging(self):
        """Test that validation errors are properly logged."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "POST"

        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = [{"loc": ["body"], "msg": "test", "type": "test"}]

        with patch("app.api.error_handlers.logger") as mock_logger:
            await validation_exception_handler(request, exc)

        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args
        assert "Validation error" in str(log_call)
        assert "extra" in log_call[1]
        assert "errors" in log_call[1]["extra"]


class TestHTTPExceptionHandler:
    """Test HTTP exception handler with edge cases."""

    @pytest.mark.asyncio
    async def test_http_exception_with_none_detail(self):
        """Test HTTP exception with None detail."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = StarletteHTTPException(status_code=404, detail=None)

        response = await http_exception_handler(request, exc)
        content = json.loads(response.body)

        # Should provide default error message from Starlette
        assert content["error"] == "Not Found"

    @pytest.mark.asyncio
    async def test_http_exception_with_dict_detail(self):
        """Test HTTP exception with dictionary detail."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = StarletteHTTPException(
            status_code=400, detail={"code": "INVALID_INPUT", "field": "username"}
        )

        response = await http_exception_handler(request, exc)
        content = json.loads(response.body)

        # Should handle dict detail
        assert content["detail"] == {"code": "INVALID_INPUT", "field": "username"}

    @pytest.mark.asyncio
    async def test_http_exception_with_headers(self):
        """Test HTTP exception preserves custom headers."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = StarletteHTTPException(
            status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"}
        )

        response = await http_exception_handler(request, exc)

        # Should not include custom headers from exception
        # (Our handler doesn't copy them)
        assert "Retry-After" not in response.headers

    @pytest.mark.asyncio
    async def test_http_exception_logging(self):
        """Test that HTTP exceptions are properly logged."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = StarletteHTTPException(status_code=503, detail="Service unavailable")

        with patch("app.api.error_handlers.logger") as mock_logger:
            await http_exception_handler(request, exc)

        mock_logger.error.assert_called_once()


class TestAppExceptionHandler:
    """Test StashHog exception handler with edge cases."""

    @pytest.mark.asyncio
    async def test_stashhog_exception_subclasses(self):
        """Test handling of different StashHogException subclasses."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        test_cases = [
            (NotFoundError("Scene", "123"), 404, "RESOURCE_NOT_FOUND"),
            (ValidationError("Invalid input", field="name"), 422, "VALIDATION_ERROR"),
            (AuthenticationError("Invalid token"), 401, "AUTHENTICATION_ERROR"),
            (AuthorizationError("Access denied"), 403, "AUTHORIZATION_ERROR"),
            (JobConflictError("sync", "existing-123"), 409, "JOB_CONFLICT"),
            (RateLimitError(retry_after=60), 429, "RATE_LIMIT_ERROR"),
            (
                StashConnectionError("Connection failed", url="http://localhost"),
                503,
                "STASH_CONNECTION_ERROR",
            ),
        ]

        for exc, expected_status, expected_code in test_cases:
            response = await app_exception_handler(request, exc)
            content = json.loads(response.body)

            assert response.status_code == expected_status
            assert content["error_code"] == expected_code
            assert str(exc) in content["error"]

    @pytest.mark.asyncio
    async def test_stashhog_exception_with_none_details(self):
        """Test StashHogException with None details."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = StashHogException("Test error", error_code="TEST", details=None)

        response = await app_exception_handler(request, exc)
        content = json.loads(response.body)

        assert content["detail"] == {}

    @pytest.mark.asyncio
    async def test_stashhog_exception_with_complex_details(self):
        """Test StashHogException with complex nested details."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        complex_details = {
            "errors": [
                {"field": "name", "issue": "too_short"},
                {"field": "age", "issue": "out_of_range"},
            ],
            "metadata": {"timestamp": "2024-01-01T00:00:00Z", "request_id": "abc123"},
        }

        exc = StashHogException(
            "Multiple errors", error_code="MULTI_ERROR", details=complex_details
        )

        response = await app_exception_handler(request, exc)
        content = json.loads(response.body)

        assert content["detail"] == complex_details


class TestGeneralExceptionHandler:
    """Test general exception handler with edge cases."""

    @pytest.mark.asyncio
    async def test_general_exception_with_unicode(self):
        """Test exception with unicode characters."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = ValueError("Error with emoji: 🚨 and unicode: ñáéíóú")

        response = await general_exception_handler(request, exc)
        content = json.loads(response.body)

        # Should handle unicode properly
        assert response.status_code == 500
        assert content["error"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_general_exception_with_no_message(self):
        """Test exception with no message."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        class CustomError(Exception):
            pass

        exc = CustomError()

        response = await general_exception_handler(request, exc)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_general_exception_logging_traceback(self):
        """Test that full traceback is logged."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        exc = RuntimeError("Test runtime error")

        with patch("app.api.error_handlers.logger") as mock_logger:
            await general_exception_handler(request, exc)

        # Should use logger.exception for full traceback
        mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_exception_handling(self):
        """Test handling multiple exceptions concurrently."""
        request1 = Mock(spec=Request)
        request1.url = Mock(path="/test1")
        request1.method = "GET"

        request2 = Mock(spec=Request)
        request2.url = Mock(path="/test2")
        request2.method = "POST"

        exc1 = ValueError("Error 1")
        exc2 = TypeError("Error 2")

        # Handle exceptions concurrently
        import asyncio

        responses = await asyncio.gather(
            general_exception_handler(request1, exc1),
            general_exception_handler(request2, exc2),
        )

        # Each should get unique request ID
        content1 = json.loads(responses[0].body)
        content2 = json.loads(responses[1].body)

        assert content1["request_id"] != content2["request_id"]


class TestErrorHandlerIntegration:
    """Test error handler integration scenarios."""

    def test_register_error_handlers(self):
        """Test registration of all error handlers."""
        app = FastAPI()

        # Count initial exception handlers
        initial_count = len(app.exception_handlers)

        register_error_handlers(app)

        # Should register 4 handlers (validation, http, app, general)
        # FastAPI has 3 default handlers, we add 4 more (but http might override)
        assert len(app.exception_handlers) >= initial_count + 2

    def test_error_handlers_with_middleware(self):
        """Test error handlers work with middleware."""
        app = FastAPI()
        register_error_handlers(app)

        # Add a test endpoint that raises different exceptions
        @app.get("/http-error")
        async def http_endpoint():
            raise StarletteHTTPException(status_code=418, detail="I'm a teapot")

        @app.get("/app-error")
        async def app_endpoint():
            raise StashHogException(
                "Test error", status_code=404, error_code="TEST_ERROR"
            )

        client = TestClient(app)

        # Test each error type
        response = client.get("/http-error")
        assert response.status_code == 418

        response = client.get("/app-error")
        assert response.status_code == 404

    def test_error_response_format_consistency(self):
        """Test that all error responses have consistent format."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/test-http")
        async def test_http():
            raise StarletteHTTPException(status_code=400, detail="Bad request")

        @app.get("/test-app")
        async def test_app():
            raise StashHogException(
                "Invalid data", status_code=400, error_code="TEST_ERROR"
            )

        client = TestClient(app)

        # Test each error type
        endpoints = ["/test-http", "/test-app"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            content = json.loads(response.text)

            # All should have request_id
            assert "request_id" in content

    @pytest.mark.asyncio
    async def test_request_id_propagation(self):
        """Test that request ID is properly propagated."""
        request = Mock(spec=Request)
        request.url = Mock(path="/test")
        request.method = "GET"

        # Test with custom request ID
        custom_id = str(uuid4())
        with patch("app.api.error_handlers.uuid4", return_value=custom_id):
            exc = ValueError("Test")
            response = await general_exception_handler(request, exc)

        content = json.loads(response.body)
        assert content["request_id"] == custom_id

    def test_error_handler_performance(self):
        """Test error handler performance with many errors."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/error")
        async def error_endpoint():
            raise StashHogException("Test error", status_code=400)

        client = TestClient(app)

        # Generate many errors quickly
        import time

        start = time.time()

        for _ in range(50):
            response = client.get("/error")
            assert response.status_code == 400

        elapsed = time.time() - start

        # Should handle 50 errors in reasonable time (< 3 seconds)
        assert elapsed < 3.0
