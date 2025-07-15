"""
Custom exception classes for the StashHog application.
"""

from typing import Any, Dict, Optional


class StashHogException(Exception):
    """Base exception for StashHog application."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class NotFoundError(StashHogException):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: Any):
        """
        Initialize not found error.

        Args:
            resource: Resource type (e.g., "Scene", "Job")
            resource_id: Resource identifier
        """
        super().__init__(
            message=f"{resource} with id '{resource_id}' not found",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "resource_id": str(resource_id)},
        )


class ValidationError(StashHogException):
    """Validation error."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class StashConnectionError(StashHogException):
    """Stash API connection error."""

    def __init__(self, message: str, url: Optional[str] = None):
        """
        Initialize Stash connection error.

        Args:
            message: Error message
            url: Stash server URL
        """
        details = {}
        if url:
            details["url"] = url

        super().__init__(
            message=message,
            status_code=503,
            error_code="STASH_CONNECTION_ERROR",
            details=details,
        )


class StashAPIError(StashHogException):
    """Stash API error response."""

    def __init__(
        self,
        message: str,
        response_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        """
        Initialize Stash API error.

        Args:
            message: Error message
            response_code: HTTP response code from Stash
            response_body: Response body from Stash
        """
        details: Dict[str, Any] = {}
        if response_code is not None:
            details["response_code"] = response_code
        if response_body:
            details["response_body"] = response_body

        super().__init__(
            message=message,
            status_code=502,
            error_code="STASH_API_ERROR",
            details=details,
        )


class OpenAIError(StashHogException):
    """OpenAI API error."""

    def __init__(
        self, message: str, model: Optional[str] = None, api_error: Optional[str] = None
    ):
        """
        Initialize OpenAI error.

        Args:
            message: Error message
            model: Model being used
            api_error: Original API error message
        """
        details = {}
        if model:
            details["model"] = model
        if api_error:
            details["api_error"] = api_error

        super().__init__(
            message=message, status_code=502, error_code="OPENAI_ERROR", details=details
        )


class JobNotFoundError(NotFoundError):
    """Job not found error."""

    def __init__(self, job_id: str):
        """
        Initialize job not found error.

        Args:
            job_id: Job identifier
        """
        super().__init__(resource="Job", resource_id=job_id)


class SceneNotFoundError(NotFoundError):
    """Scene not found error."""

    def __init__(self, scene_id: str):
        """
        Initialize scene not found error.

        Args:
            scene_id: Scene identifier
        """
        super().__init__(resource="Scene", resource_id=scene_id)


class PlanNotFoundError(NotFoundError):
    """Analysis plan not found error."""

    def __init__(self, plan_id: str):
        """
        Initialize plan not found error.

        Args:
            plan_id: Plan identifier
        """
        super().__init__(resource="Analysis Plan", resource_id=plan_id)


class AuthenticationError(StashHogException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication required"):
        """
        Initialize authentication error.

        Args:
            message: Error message
        """
        super().__init__(
            message=message, status_code=401, error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(StashHogException):
    """Authorization error."""

    def __init__(self, message: str = "Insufficient permissions"):
        """
        Initialize authorization error.

        Args:
            message: Error message
        """
        super().__init__(
            message=message, status_code=403, error_code="AUTHORIZATION_ERROR"
        )


class RateLimitError(StashHogException):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: Optional[int] = None):
        """
        Initialize rate limit error.

        Args:
            retry_after: Seconds to wait before retrying
        """
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_ERROR",
            details=details,
        )


class ConfigurationError(StashHogException):
    """Configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that has issue
        """
        details = {}
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details=details,
        )
