"""Tests for error handlers."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_handlers import (
    general_exception_handler,
    http_exception_handler,
    register_exception_handlers,
    stashhog_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import StashHogException


class TestErrorHandlers:
    """Test error handler functions."""

    @pytest.mark.asyncio
    async def test_stashhog_exception_handler(self):
        """Test handling of StashHog custom exceptions."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Create exception
        exc = StashHogException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"field": "value"},
        )

        # Handle exception
        with patch("app.core.error_handlers.logger") as mock_logger:
            response = await stashhog_exception_handler(request, exc)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        assert response.headers["X-Request-ID"] == "test-request-123"

        # Verify response content
        content = response.body.decode()
        assert "Test error" in content
        assert "TEST_ERROR" in content
        assert "test-request-123" in content

        # Verify logging
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stashhog_exception_handler_no_request_id(self):
        """Test handling when request has no request_id."""
        # Create mock request without request_id
        request = Mock(spec=Request)
        request.state = Mock()
        delattr(request.state, "request_id")

        exc = StashHogException(message="Test error", error_code="TEST_ERROR")

        response = await stashhog_exception_handler(request, exc)

        assert response.headers["X-Request-ID"] == "unknown"

    @pytest.mark.asyncio
    async def test_validation_exception_handler_request_validation(self):
        """Test handling of request validation errors."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Create validation error
        mock_errors = [
            {
                "loc": ["body", "field1"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["query", "limit"],
                "msg": "ensure this value is less than or equal to 100",
                "type": "value_error.number.not_le",
            },
        ]
        exc = Mock(spec=RequestValidationError)
        exc.errors.return_value = mock_errors

        # Handle exception
        with patch("app.core.error_handlers.logger") as mock_logger:
            response = await validation_exception_handler(request, exc)

        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["X-Request-ID"] == "test-request-123"

        # Verify response content
        content = response.body.decode()
        assert "Validation error" in content
        assert "VALIDATION_ERROR" in content
        assert "body -> field1" in content
        assert "query -> limit" in content

        # Verify logging
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_exception_handler_pydantic_validation(self):
        """Test handling of Pydantic validation errors."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Create Pydantic validation error
        exc = Mock()
        exc.errors.return_value = [
            {"loc": ["field1"], "msg": "invalid type", "type": "type_error"}
        ]

        response = await validation_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = response.body.decode()
        assert "field1" in content
        assert "invalid type" in content

    @pytest.mark.asyncio
    async def test_validation_exception_handler_no_errors_method(self):
        """Test handling when exception has no errors method."""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Create exception without errors method
        exc = Mock()
        delattr(exc, "errors")

        response = await validation_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test handling of HTTP exceptions."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Test various HTTP status codes
        test_cases = [
            (404, "NOT_FOUND", "Resource not found"),
            (401, "UNAUTHORIZED", "Authentication required"),
            (500, "INTERNAL_SERVER_ERROR", "Server error"),
            (418, "HTTP_ERROR", "I'm a teapot"),  # Unmapped status code
        ]

        for status_code, expected_error_code, detail in test_cases:
            exc = StarletteHTTPException(status_code=status_code, detail=detail)

            with patch("app.core.error_handlers.logger") as mock_logger:
                response = await http_exception_handler(request, exc)

            assert response.status_code == status_code
            content = response.body.decode()
            assert expected_error_code in content
            assert detail in content
            assert "test-request-123" in content

            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test handling of unexpected exceptions."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-request-123"

        # Create unexpected exception
        exc = ValueError("Something went wrong")

        # Handle exception
        with patch("app.core.error_handlers.logger") as mock_logger:
            response = await general_exception_handler(request, exc)

        # Verify response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["X-Request-ID"] == "test-request-123"

        # Verify response content
        content = response.body.decode()
        assert "An unexpected error occurred" in content
        assert "INTERNAL_SERVER_ERROR" in content
        assert "test-request-123" in content

        # Verify logging
        mock_logger.exception.assert_called_once()
        call_kwargs = mock_logger.exception.call_args[1]
        assert call_kwargs["extra"]["error"] == "Something went wrong"
        assert call_kwargs["extra"]["error_type"] == "ValueError"

    def test_register_exception_handlers(self):
        """Test registration of exception handlers."""
        # Create mock app
        app = Mock()
        app.add_exception_handler = Mock()

        # Register handlers
        register_exception_handlers(app)

        # Verify all handlers were registered
        assert app.add_exception_handler.call_count == 5

        # Verify specific handlers
        calls = app.add_exception_handler.call_args_list

        # Check that handlers were registered for expected exception types
        registered_exceptions = [call[0][0] for call in calls]
        assert StashHogException in registered_exceptions
        assert RequestValidationError in registered_exceptions
        assert PydanticValidationError in registered_exceptions
        assert StarletteHTTPException in registered_exceptions
        assert Exception in registered_exceptions
