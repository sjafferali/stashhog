"""
Global error handlers for the API.
"""

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import Request, status

if TYPE_CHECKING:
    from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import StashHogException

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    """
    request_id = str(uuid4())

    # Log the error
    logger.error(
        f"Validation error for request {request_id}: {exc.errors()}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )

    # Format errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation failed",
            "detail": "The request contains invalid data",
            "request_id": request_id,
            "validation_errors": errors,
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    """
    request_id = str(uuid4())

    # Log the error
    logger.error(
        f"HTTP error {exc.status_code} for request {request_id}: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail or "An error occurred",
            "detail": exc.detail,
            "request_id": request_id,
        },
    )


async def app_exception_handler(
    request: Request, exc: StashHogException
) -> JSONResponse:
    """
    Handle application exceptions.
    """
    request_id = str(uuid4())

    # Log the error
    logger.error(
        f"Application error for request {request_id}: {exc}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": str(exc),
            "error_code": exc.error_code,
            "detail": exc.details,
            "request_id": request_id,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """
    request_id = str(uuid4())

    # Log the error with full traceback
    logger.exception(
        f"Unexpected error for request {request_id}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Don't expose internal errors in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "request_id": request_id,
        },
    )


def register_error_handlers(app: "FastAPI") -> None:
    """
    Register all error handlers with the FastAPI app.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StashHogException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)
