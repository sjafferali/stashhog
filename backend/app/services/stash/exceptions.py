"""Custom exceptions for Stash API operations."""

from typing import Any, List, Optional


class StashException(Exception):
    """Base exception for all Stash-related errors."""

    pass


class StashConnectionError(StashException):
    """Raised when connection to Stash API fails."""

    pass


class StashAuthenticationError(StashException):
    """Raised when authentication with Stash API fails."""

    pass


class StashNotFoundError(StashException):
    """Raised when requested entity is not found in Stash."""

    pass


class StashValidationError(StashException):
    """Raised when data validation fails."""

    pass


class StashRateLimitError(StashException):
    """Raised when rate limit is exceeded."""

    pass


class StashGraphQLError(StashException):
    """Raised when GraphQL query/mutation fails."""

    def __init__(self, message: str, errors: Optional[List[Any]] = None):
        super().__init__(message)
        self.errors = errors or []
