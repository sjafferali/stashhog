"""
StashHog FastAPI application.
"""

import logging
import os
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
from app.core.database import close_db
from app.core.job_context import setup_job_logging
from app.core.logging import configure_logging
from app.core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from app.core.migrations import run_migrations_async
from app.core.tasks import get_task_queue
from app.jobs import register_all_jobs
from app.services.daemon_service import daemon_service
from app.services.job_service import job_service

# Suppress passlib's crypt deprecation warning in Python 3.11+
warnings.filterwarnings(
    "ignore", message="'crypt' is deprecated", category=DeprecationWarning
)

# Configure logging
# Set up job context logging first to ensure filter is available
setup_job_logging()
configure_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


async def _run_migrations_with_retry(max_attempts: int = 3) -> None:
    """Run database migrations with retry logic."""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                f"Running database migrations... (attempt {attempt}/{max_attempts})"
            )
            await run_migrations_async()
            return  # Success
        except Exception as e:
            logger.error(f"Migration attempt {attempt} failed: {e}")
            if attempt >= max_attempts:
                logger.error(
                    f"Failed to apply migrations after {max_attempts} attempts"
                )
                logger.error("Application cannot start due to migration failures")
                logger.error(
                    "Please check the logs above for detailed error information"
                )
                raise RuntimeError(
                    f"Database migrations failed after {max_attempts} attempts: {e}"
                )
            else:
                logger.info("Waiting 5 seconds before retry...")
                import asyncio

                await asyncio.sleep(5)


async def _startup_tasks() -> None:
    """Run all startup tasks."""
    # Skip migrations in test environment
    if os.getenv("PYTEST_CURRENT_TEST"):
        logger.info("Skipping migrations in test environment")
    else:
        await _run_migrations_with_retry()

    # Initialize background task queue
    # Skip starting workers in test environment to avoid SQLite concurrency issues
    if not os.getenv("PYTEST_CURRENT_TEST"):
        logger.info("Starting background workers...")
        task_queue = get_task_queue()
        await task_queue.start()
    else:
        logger.info("Skipping background workers in test environment")

    # Register job handlers
    logger.info("Registering job handlers...")
    register_all_jobs(job_service)

    # Start scheduler
    if not os.getenv("PYTEST_CURRENT_TEST"):
        logger.info("Starting scheduler...")
        from app.services.sync.scheduler import sync_scheduler

        sync_scheduler.start()
        logger.info("Scheduler started successfully")

        # Initialize daemon service
        logger.info("Initializing daemon service...")
        await daemon_service.initialize()
        logger.info("Daemon service initialized successfully")

    # TODO: Test external connections
    # logger.info("Testing external connections...")
    # await test_connections()

    logger.info("Application startup complete")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app.name} v{settings.app.version}")

    try:
        await _startup_tasks()

    except Exception as e:
        logger.error("=" * 80)
        logger.error("APPLICATION STARTUP FAILURE")
        logger.error("=" * 80)
        logger.error(f"Failed to start application: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, "__cause__") and e.__cause__:
            logger.error(f"Caused by: {e.__cause__}")
        logger.error("=" * 80)
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app.name}")

    try:
        # Stop background workers (if they were started)
        if not os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("Stopping background workers...")
            task_queue = get_task_queue()
            await task_queue.stop()

            # Stop scheduler
            logger.info("Stopping scheduler...")
            from app.services.sync.scheduler import sync_scheduler

            sync_scheduler.shutdown()

            # Shutdown daemon service
            logger.info("Shutting down daemon service...")
            await daemon_service.shutdown()
        else:
            logger.info("Skipping worker shutdown in test environment")

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


# Root endpoint - always register but behavior changes based on environment
@app.get("/", include_in_schema=False)
async def root(request: Request) -> Any:
    """Root endpoint."""
    # In production with static files, serve the SPA
    if settings.app.environment == "production" and os.path.exists("static/index.html"):
        return FileResponse("static/index.html")

    # Otherwise return API info
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "message": "Welcome to StashHog API",
    }


# Mount static files for frontend (in production)
# This must come after all explicit routes
if settings.app.environment == "production":
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
