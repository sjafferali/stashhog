"""Tests for custom exception classes."""

import pytest

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    JobConflictError,
    JobNotFoundError,
    NotFoundError,
    OpenAIError,
    PlanNotFoundError,
    RateLimitError,
    SceneNotFoundError,
    StashAPIError,
    StashConnectionError,
    StashHogException,
    ValidationError,
)


class TestStashHogException:
    """Test base exception class."""

    def test_basic_exception(self):
        """Test creating basic exception."""
        exc = StashHogException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "StashHogException"
        assert exc.details == {}

    def test_exception_with_all_params(self):
        """Test exception with all parameters."""
        exc = StashHogException(
            message="Test error",
            status_code=400,
            error_code="TEST_ERROR",
            details={"key": "value"},
        )
        assert exc.message == "Test error"
        assert exc.status_code == 400
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {"key": "value"}

    def test_exception_inheritance(self):
        """Test that exception inherits from Exception."""
        exc = StashHogException("Test error")
        assert isinstance(exc, Exception)


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_not_found_error(self):
        """Test creating not found error."""
        exc = NotFoundError("User", 123)
        assert exc.message == "User with id '123' not found"
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.details == {"resource": "User", "resource_id": "123"}

    def test_not_found_with_string_id(self):
        """Test not found error with string ID."""
        exc = NotFoundError("Scene", "abc-123")
        assert exc.message == "Scene with id 'abc-123' not found"
        assert exc.details["resource_id"] == "abc-123"


class TestValidationError:
    """Test ValidationError exception."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        exc = ValidationError("Invalid input")
        assert exc.message == "Invalid input"
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == {}

    def test_validation_error_with_field(self):
        """Test validation error with field."""
        exc = ValidationError("Invalid email format", field="email")
        assert exc.message == "Invalid email format"
        assert exc.details == {"field": "email"}

    def test_validation_error_with_field_and_value(self):
        """Test validation error with field and value."""
        exc = ValidationError("Invalid email format", field="email", value="not-email")
        assert exc.message == "Invalid email format"
        assert exc.details == {"field": "email", "value": "not-email"}

    def test_validation_error_with_value_only(self):
        """Test validation error with value only."""
        exc = ValidationError("Invalid value", value=123)
        assert exc.details == {"value": "123"}


class TestStashConnectionError:
    """Test StashConnectionError exception."""

    def test_basic_connection_error(self):
        """Test basic connection error."""
        exc = StashConnectionError("Connection refused")
        assert exc.message == "Connection refused"
        assert exc.status_code == 503
        assert exc.error_code == "STASH_CONNECTION_ERROR"
        assert exc.details == {}

    def test_connection_error_with_url(self):
        """Test connection error with URL."""
        exc = StashConnectionError("Connection timeout", url="http://localhost:9999")
        assert exc.message == "Connection timeout"
        assert exc.details == {"url": "http://localhost:9999"}


class TestStashAPIError:
    """Test StashAPIError exception."""

    def test_basic_api_error(self):
        """Test basic API error."""
        exc = StashAPIError("API request failed")
        assert exc.message == "API request failed"
        assert exc.status_code == 502
        assert exc.error_code == "STASH_API_ERROR"
        assert exc.details == {}

    def test_api_error_with_response_code(self):
        """Test API error with response code."""
        exc = StashAPIError("Bad request", response_code=400)
        assert exc.message == "Bad request"
        assert exc.details == {"response_code": 400}

    def test_api_error_with_response_body(self):
        """Test API error with response body."""
        exc = StashAPIError(
            "Server error", response_code=500, response_body="Internal server error"
        )
        assert exc.message == "Server error"
        assert exc.details == {
            "response_code": 500,
            "response_body": "Internal server error",
        }


class TestOpenAIError:
    """Test OpenAIError exception."""

    def test_basic_openai_error(self):
        """Test basic OpenAI error."""
        exc = OpenAIError("API key invalid")
        assert exc.message == "API key invalid"
        assert exc.status_code == 502
        assert exc.error_code == "OPENAI_ERROR"
        assert exc.details == {}

    def test_openai_error_with_model(self):
        """Test OpenAI error with model."""
        exc = OpenAIError("Rate limit exceeded", model="gpt-4")
        assert exc.message == "Rate limit exceeded"
        assert exc.details == {"model": "gpt-4"}

    def test_openai_error_with_api_error(self):
        """Test OpenAI error with API error."""
        exc = OpenAIError(
            "Request failed", model="gpt-3.5-turbo", api_error="insufficient_quota"
        )
        assert exc.message == "Request failed"
        assert exc.details == {
            "model": "gpt-3.5-turbo",
            "api_error": "insufficient_quota",
        }


class TestSpecificNotFoundErrors:
    """Test specific not found error subclasses."""

    def test_job_not_found_error(self):
        """Test JobNotFoundError."""
        exc = JobNotFoundError("job-123")
        assert exc.message == "Job with id 'job-123' not found"
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.details == {"resource": "Job", "resource_id": "job-123"}

    def test_scene_not_found_error(self):
        """Test SceneNotFoundError."""
        exc = SceneNotFoundError("scene-456")
        assert exc.message == "Scene with id 'scene-456' not found"
        assert exc.details["resource"] == "Scene"

    def test_plan_not_found_error(self):
        """Test PlanNotFoundError."""
        exc = PlanNotFoundError("plan-789")
        assert exc.message == "Analysis Plan with id 'plan-789' not found"
        assert exc.details["resource"] == "Analysis Plan"


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_default_authentication_error(self):
        """Test authentication error with default message."""
        exc = AuthenticationError()
        assert exc.message == "Authentication required"
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.details == {}

    def test_custom_authentication_error(self):
        """Test authentication error with custom message."""
        exc = AuthenticationError("Invalid token")
        assert exc.message == "Invalid token"
        assert exc.status_code == 401


class TestAuthorizationError:
    """Test AuthorizationError exception."""

    def test_default_authorization_error(self):
        """Test authorization error with default message."""
        exc = AuthorizationError()
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.details == {}

    def test_custom_authorization_error(self):
        """Test authorization error with custom message."""
        exc = AuthorizationError("Admin access required")
        assert exc.message == "Admin access required"
        assert exc.status_code == 403


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_basic_rate_limit_error(self):
        """Test basic rate limit error."""
        exc = RateLimitError()
        assert exc.message == "Rate limit exceeded"
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_ERROR"
        assert exc.details == {}

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry after."""
        exc = RateLimitError(retry_after=60)
        assert exc.message == "Rate limit exceeded"
        assert exc.details == {"retry_after": 60}


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_basic_configuration_error(self):
        """Test basic configuration error."""
        exc = ConfigurationError("Missing configuration")
        assert exc.message == "Missing configuration"
        assert exc.status_code == 500
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details == {}

    def test_configuration_error_with_key(self):
        """Test configuration error with config key."""
        exc = ConfigurationError("Invalid value", config_key="database_url")
        assert exc.message == "Invalid value"
        assert exc.details == {"config_key": "database_url"}


class TestJobConflictError:
    """Test JobConflictError exception."""

    def test_basic_job_conflict_error(self):
        """Test basic job conflict error."""
        exc = JobConflictError("sync")
        assert (
            exc.message
            == "A sync job is already running. Please wait for it to complete."
        )
        assert exc.status_code == 409
        assert exc.error_code == "JOB_CONFLICT"
        assert exc.details == {"job_type": "sync"}

    def test_job_conflict_error_with_existing_job(self):
        """Test job conflict error with existing job ID."""
        exc = JobConflictError("analysis", existing_job_id="job-123")
        assert (
            exc.message
            == "A analysis job is already running. Please wait for it to complete."
        )
        assert exc.details == {"job_type": "analysis", "existing_job_id": "job-123"}


class TestExceptionUsagePatterns:
    """Test common usage patterns for exceptions."""

    def test_exception_chaining(self):
        """Test that exceptions can be chained properly."""
        try:
            raise ValueError("Original error")
        except ValueError:
            exc = StashConnectionError("Failed to connect to Stash server")
            # Python's exception chaining
            assert exc.__cause__ is None  # Not explicitly set

    def test_exception_context_manager(self):
        """Test using exceptions in context managers."""
        with pytest.raises(NotFoundError) as exc_info:
            raise SceneNotFoundError("test-scene")

        assert exc_info.value.message == "Scene with id 'test-scene' not found"
        assert exc_info.value.status_code == 404

    def test_exception_serialization(self):
        """Test that exception details can be serialized."""
        exc = ValidationError("Invalid input", field="email", value="not-an-email")

        # Simulate what might happen in an error handler
        error_dict = {
            "message": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        }

        assert error_dict["message"] == "Invalid input"
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        assert error_dict["status_code"] == 422
        assert error_dict["details"]["field"] == "email"
        assert error_dict["details"]["value"] == "not-an-email"

    def test_exception_type_checking(self):
        """Test exception type checking for error handling."""
        exc = JobNotFoundError("job-123")

        # Check inheritance chain
        assert isinstance(exc, JobNotFoundError)
        assert isinstance(exc, NotFoundError)
        assert isinstance(exc, StashHogException)
        assert isinstance(exc, Exception)

        # Check that it's not other types
        assert not isinstance(exc, ValidationError)
        assert not isinstance(exc, StashConnectionError)
