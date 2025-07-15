"""Create test app without lifespan events."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.error_handlers import register_error_handlers
from app.core.config import get_settings
from app.core.middleware import ErrorHandlingMiddleware

settings = get_settings()


def create_test_app():
    """Create FastAPI app for testing without lifespan events."""
    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="Test app",
    )

    # Register error handlers
    register_error_handlers(app)

    # Add minimal middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.credentials,
        allow_methods=settings.cors.methods,
        allow_headers=settings.cors.headers,
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    return app
