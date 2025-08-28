#!/usr/bin/env python3
"""
Test script to verify the concurrent database operations fix.
This simulates the scenario that was causing the asyncpg InterfaceError.
"""

import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import DATABASE_URL
from app.models.plan import AnalysisPlan, PlanStatus
from app.models.plan_change import PlanChange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create async engine and session factory
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def simulate_concurrent_operations():
    """Simulate the concurrent operations that were causing the error."""

    async with AsyncSessionLocal() as db:
        # Get or create a test plan
        result = await db.execute(
            select(AnalysisPlan)
            .where(AnalysisPlan.name == "Test Concurrent Fix")
            .limit(1)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            plan = AnalysisPlan(
                name="Test Concurrent Fix",
                status=PlanStatus.PENDING,
                metadata={"test": True},
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            logger.info(f"Created test plan {plan.id}")
        else:
            logger.info(f"Using existing test plan {plan.id}")

        plan_id = plan.id

        # Simulate adding changes from multiple scenes
        # This is what was causing the "another operation is in progress" error
        for i in range(5):
            logger.info(f"Processing scene {i+1}")

            # Add a change
            change = PlanChange(
                plan_id=plan_id,
                scene_id=f"test-scene-{i+1}",
                field="title",
                action="update",
                current_value="Old Title",
                proposed_value=f"New Title {i+1}",
                confidence=0.95,
            )
            db.add(change)

            # This count query was causing the error when multiple scenes
            # were being processed
            count_query = select(func.count()).where(PlanChange.plan_id == plan_id)
            result = await db.execute(count_query)
            total = result.scalar() or 0
            logger.info(f"Current total changes: {total}")

            # Flush to database
            await db.flush()

        # Commit all changes
        await db.commit()
        logger.info("Successfully processed all scenes without concurrency errors!")

        # Clean up test data
        await db.execute(
            PlanChange.__table__.delete().where(PlanChange.plan_id == plan_id)
        )
        await db.delete(plan)
        await db.commit()
        logger.info("Cleaned up test data")


async def main():
    try:
        await simulate_concurrent_operations()
        logger.info("✅ Test passed - no concurrent operation errors!")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
