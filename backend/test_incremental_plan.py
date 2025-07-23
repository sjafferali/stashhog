#!/usr/bin/env python3
"""Test script to verify incremental plan creation works properly."""

import asyncio
import logging
import time

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import AnalysisPlan, PlanStatus, Scene
from app.services.analysis.analysis_service import AnalysisService
from app.services.analysis.models import AnalysisOptions
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def monitor_plan_creation(job_id: str, interval: float = 2.0):
    """Monitor for plan creation and updates."""
    plan_id = None
    last_change_count = 0

    logger.info(f"Starting to monitor for plan with job_id={job_id}")

    while True:
        async with AsyncSessionLocal() as db:
            if plan_id is None:
                # Look for new plan
                query = select(AnalysisPlan).where(AnalysisPlan.job_id == job_id)
                result = await db.execute(query)
                plan = result.scalar_one_or_none()

                if plan:
                    plan_id = plan.id
                    logger.info(f"✅ Plan {plan_id} created! Status: {plan.status}")
                    logger.info(f"   Name: {plan.name}")
                    logger.info(f"   Changes: {len(plan.changes)}")
                    last_change_count = len(plan.changes)
            else:
                # Monitor existing plan
                query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
                result = await db.execute(query)
                plan = result.scalar_one_or_none()

                if plan:
                    change_count = len(plan.changes)
                    if change_count != last_change_count:
                        logger.info(
                            f"📊 Plan {plan_id} updated: {last_change_count} -> {change_count} changes"
                        )
                        last_change_count = change_count

                    if plan.status == PlanStatus.DRAFT:
                        logger.info(
                            f"✅ Plan {plan_id} finalized with {change_count} total changes!"
                        )
                        break

        await asyncio.sleep(interval)


async def run_test():
    """Run a test analysis job and monitor plan creation."""
    settings = await load_settings_with_db_overrides()

    # Get some scenes to analyze
    async with AsyncSessionLocal() as db:
        query = select(Scene).limit(5)
        result = await db.execute(query)
        scenes = result.scalars().all()
        scene_ids = [str(scene.id) for scene in scenes]

    if not scene_ids:
        logger.error("No scenes found in database!")
        return

    logger.info(f"Found {len(scene_ids)} scenes to analyze")

    # Create services
    stash_service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )

    openai_client = OpenAIClient(
        api_key=settings.openai.api_key,
        model=settings.openai.model,
        base_url=settings.openai.base_url,
        max_tokens=settings.openai.max_tokens,
        temperature=settings.openai.temperature,
        timeout=settings.openai.timeout,
    )

    analysis_service = AnalysisService(
        openai_client=openai_client,
        stash_service=stash_service,
        settings=settings,
    )

    # Create job ID
    job_id = f"test-incremental-{int(time.time())}"

    # Start monitoring in background
    monitor_task = asyncio.create_task(monitor_plan_creation(job_id))

    # Run analysis
    logger.info(f"Starting analysis with job_id={job_id}")

    async def progress_callback(progress: int, message: str):
        logger.info(f"Progress: {progress}% - {message}")

    try:
        async with AsyncSessionLocal() as db:
            plan = await analysis_service.analyze_scenes(
                scene_ids=scene_ids,
                options=AnalysisOptions(
                    detect_performers=True,
                    detect_tags=True,
                ),
                job_id=job_id,
                db=db,
                progress_callback=progress_callback,
                plan_name=f"Incremental Test Plan {int(time.time())}",
            )

        logger.info(
            f"Analysis completed! Plan ID: {plan.id if hasattr(plan, 'id') else 'None'}"
        )

        # Wait for monitor to finish
        await monitor_task

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        monitor_task.cancel()


if __name__ == "__main__":
    asyncio.run(run_test())
