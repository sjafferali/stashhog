"""
StashHog FastAPI application.
"""
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    TimingMiddleware,
    ErrorHandlingMiddleware
)
from app.api.error_handlers import register_error_handlers
from app.api import api_router
from app.core.logging import configure_logging
from app.core.tasks import get_task_queue
from app.jobs import register_all_jobs

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        register_all_jobs()
        
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

# Mount static files for frontend (in production)
if settings.app.environment == "production":
    try:
        app.mount("/", StaticFiles(directory="static", html=True), name="static")
    except RuntimeError:
        logger.warning("Static files directory not found, skipping mount")

# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "message": "Welcome to StashHog API"
    }

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
    all_ready = all([
        checks["database"],
        # Other critical checks
    ])
    
    status_code = 200 if all_ready else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not ready",
            "checks": checks
        }
    )

# Version endpoint
@app.get("/version", include_in_schema=False)
async def version_info() -> Dict[str, str]:
    """Get application version information."""
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "environment": settings.app.environment,
        "debug": settings.app.debug,
    }