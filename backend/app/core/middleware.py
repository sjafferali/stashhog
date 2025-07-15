"""
Custom middleware for the StashHog application.
"""

import logging
import time
import uuid
from typing import Awaitable, Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Add X-Request-ID header to request and response.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response with X-Request-ID header
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store request ID in request state for logging
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Log request and response information.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response
        """
        start_time = time.time()

        # Get request ID from state (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request
        client_host = "unknown"
        if request.client:
            client_host = request.client.host

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": client_host,
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate process time
        process_time = time.time() - start_time

        # Log response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s",
            },
        )

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request processing time to response headers."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Add X-Process-Time header to response.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response with X-Process-Time header
        """
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle unexpected errors."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Catch and handle unexpected errors.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response or error response
        """
        try:
            return await call_next(request)
        except Exception:
            # Re-raise the exception to let FastAPI's exception handlers deal with it
            # This allows proper error handling in tests and production
            raise


class CORSMiddleware:
    """Custom CORS middleware with more control."""

    def __init__(
        self,
        app: object,
        origins: List[str],
        credentials: bool = True,
        methods: Optional[List[str]] = None,
        headers: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize CORS middleware.

        Args:
            app: FastAPI application
            origins: Allowed origins
            credentials: Allow credentials
            methods: Allowed methods
            headers: Allowed headers
        """
        self.app = app
        self.origins = origins
        self.credentials = credentials
        self.methods = methods or ["*"]
        self.headers = headers or ["*"]

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Handle CORS headers.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response with CORS headers
        """
        # Get origin from request
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        # Add CORS headers if origin is allowed
        if origin in self.origins or "*" in self.origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

            if self.credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            if request.method == "OPTIONS":
                response.headers["Access-Control-Allow-Methods"] = ", ".join(
                    self.methods
                )
                response.headers["Access-Control-Allow-Headers"] = ", ".join(
                    self.headers
                )
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

        return response
