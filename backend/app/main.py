"""
StashHog FastAPI application.
"""

import logging
import warnings
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.error_handlers import register_error_handlers
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import configure_logging
from app.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from app.core.tasks import get_task_queue
from app.jobs import register_all_jobs
from app.services.job_service import job_service

# Suppress passlib's crypt deprecation warning in Python 3.11+
warnings.filterwarnings(
    "ignore", message="'crypt' is deprecated", category=DeprecationWarning
)

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app.name} v{settings.app.version}")

    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()

        # Initialize background task queue
        logger.info("Starting background workers...")
        task_queue = get_task_queue()
        await task_queue.start()

        # Register job handlers
        logger.info("Registering job handlers...")
        register_all_jobs(job_service)

        # TODO: Test external connections
        # logger.info("Testing external connections...")
        # await test_connections()

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app.name}")

    try:
        # Stop background workers
        logger.info("Stopping background workers...")
        task_queue = get_task_queue()
        await task_queue.stop()

        # Close database connections
        logger.info("Closing database connections...")
        await close_db()

        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="Automated scene tagging and metadata enrichment for Stash",
    docs_url="/docs" if settings.app.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.app.debug else None,
    openapi_url="/openapi.json" if settings.app.debug else None,
    lifespan=lifespan,
)

# Register exception handlers
register_error_handlers(app)

# Add middleware (order matters - last added is first to process)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

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


# Health check endpoint (outside of API prefix for monitoring)
@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}


# Ready check endpoint (more comprehensive)
@app.get("/ready", include_in_schema=False)
async def ready_check(request: Request) -> JSONResponse:
    """
    Readiness check endpoint.

    Checks if the application is ready to handle requests.
    """
    checks = {
        "database": False,
        "stash": False,
        "openai": False,
    }

    # TODO: Implement actual checks
    # try:
    #     # Check database
    #     await check_database()
    #     checks["database"] = True
    # except Exception as e:
    #     logger.error(f"Database check failed: {e}")

    # Check if all critical services are ready
    all_ready = all(
        [
            checks["database"],
            # Other critical checks
        ]
    )

    status_code = 200 if all_ready else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ready else "not ready", "checks": checks},
    )


# Version endpoint
@app.get("/version", include_in_schema=False)
async def version_info() -> Dict[str, Any]:
    """Get application version information."""
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "environment": settings.app.environment,
        "debug": settings.app.debug,
    }


# Root endpoint for non-production environments
if settings.app.environment != "production":

    @app.get("/", include_in_schema=False)
    async def root() -> Dict[str, str]:
        """Root endpoint."""
        return {
            "name": settings.app.name,
            "version": settings.app.version,
            "message": "Welcome to StashHog API",
        }


# Mount static files for frontend (in production)
# This must come after all explicit routes
if settings.app.environment == "production":
    import os

    try:
        static_dir = "static"

        # Check if static directory exists
        if os.path.exists(static_dir):
            # Serve static assets with a specific path
            assets_dir = os.path.join(static_dir, "assets")
            if os.path.exists(assets_dir):
                app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

            # Catch-all route for SPA - must be last!
            @app.get("/{full_path:path}", include_in_schema=False)
            async def serve_spa(full_path: str) -> FileResponse:
                """Serve the SPA for any unmatched routes."""
                # Skip API routes - they should return 404 from API router
                if full_path.startswith("api/"):
                    raise HTTPException(status_code=404, detail="Not Found")

                # Serve index.html for all other routes
                index_path = os.path.join(static_dir, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
                else:
                    raise HTTPException(
                        status_code=404, detail="Static files not found"
                    )

        else:
            logger.warning(
                f"Static directory '{static_dir}' not found, skipping SPA setup"
            )

    except Exception as e:
        logger.error(f"Error setting up static file serving: {e}")
