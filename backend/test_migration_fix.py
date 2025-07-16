#!/usr/bin/env python3
"""
Test script to verify migration fix.

This script simulates the app startup behavior to test if the migration
handling properly resets database connections.
"""

import asyncio
import logging

from app.core.logging import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


async def test_migration_flow():
    """Test the migration flow and engine reset."""
    logger.info("Starting migration test...")

    # Step 1: Import database module (engines get created)
    logger.info("Step 1: Importing database module...")
    import app.core.database  # noqa: F401 - Import to trigger engine creation

    # Step 2: Run migrations (should reset engines after)
    logger.info("Step 2: Running migrations...")
    from app.core.migrations import run_migrations_async

    await run_migrations_async()

    # Step 3: Try to use the engines (should work without issues)
    logger.info("Step 3: Testing database connection...")
    from app.core.database import get_async_db

    try:
        async for db in get_async_db():
            # Try a simple query
            result = await db.execute("SELECT 1")
            logger.info(f"Database query successful: {result.scalar()}")
            break

        logger.info(
            "✅ Migration fix test PASSED - Database is accessible after migrations"
        )

    except Exception as e:
        logger.error(f"❌ Migration fix test FAILED - Error accessing database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_migration_flow())
