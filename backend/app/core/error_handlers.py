"""
Exception handlers for FastAPI application.
"""

import logging
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from fastapi import FastAPI

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import StashHogException

logger = logging.getLogger(__name__)


async def stashhog_exception_handler(
    request: Request, exc: StashHogException
) -> JSONResponse:
    """
    Handle StashHog custom exceptions.

    Args:
        request: Request object
        exc: StashHogException instance

    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"StashHog exception: {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle validation errors from Pydantic.

    Args:
        request: Request object
        exc: Validation error

    Returns:
        JSONResponse with validation error details
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Extract validation errors
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
    else:
        errors = exc.errors() if hasattr(exc, "errors") else []

    # Format errors for response
    formatted_errors = []
    for error in errors:
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        formatted_errors.append(
            {
                "field": field_path,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )

    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "errors": formatted_errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "details": {"errors": formatted_errors},
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.

    Args:
        request: Request object
        exc: HTTP exception

    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "error_code": error_code,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: Request object
        exc: Any exception

    Returns:
        JSONResponse with generic error message
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.exception(
        "Unexpected error occurred",
        extra={
            "request_id": request_id,
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An unexpected error occurred",
                "error_code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: "FastAPI") -> None:
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Custom exceptions
    app.add_exception_handler(StashHogException, stashhog_exception_handler)  # type: ignore[arg-type]

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)  # type: ignore[arg-type]

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]

    # General exceptions (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
