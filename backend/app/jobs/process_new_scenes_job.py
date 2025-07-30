"""Process new scenes workflow job.

This job orchestrates a complete workflow for processing newly downloaded scenes:
1. Process downloads from qBittorrent
2. Run Stash metadata scan if new items were downloaded
3. Run incremental sync to import new scenes
4. Analyze unanalyzed scenes in batches
5. Apply approved changes from analysis
6. Generate Stash metadata
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models import Scene
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


async def _create_and_run_subjob(
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Create and run a sub-job, polling until completion."""
    logger.info(f"Starting {step_name} for parent job {parent_job_id}")

    async with AsyncSessionLocal() as db:
        # Create the sub-job
        sub_job = await job_service.create_job(
            job_type=job_type,
            db=db,
            metadata={**metadata, "parent_job_id": parent_job_id},
        )
        await db.commit()
        sub_job_id = str(sub_job.id)

    logger.info(f"Created sub-job {sub_job_id} for {step_name}")

    # Poll for completion
    poll_interval = 2  # seconds
    while True:
        # Check cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Parent job {parent_job_id} cancelled, stopping {step_name}")
            # Cancel the sub-job
            async with AsyncSessionLocal() as db:
                await job_service.cancel_job(sub_job_id, db)
                await db.commit()
            return None

        # Check sub-job status
        async with AsyncSessionLocal() as db:
            sub_job_result = await job_service.get_job(sub_job_id, db)
            if not sub_job_result:
                logger.error(f"Sub-job {sub_job_id} not found")
                return None
            sub_job = sub_job_result

            if sub_job.is_finished():
                logger.info(
                    f"Sub-job {sub_job_id} finished with status: {sub_job.status}"
                )
                # Return the result
                return {
                    "job_id": sub_job_id,
                    "status": (
                        sub_job.status.value
                        if hasattr(sub_job.status, "value")
                        else sub_job.status
                    ),
                    "result": sub_job.result,
                    "error": sub_job.error,
                    "duration_seconds": sub_job.get_duration_seconds(),
                }

            # Update progress with sub-job progress
            sub_progress = int(sub_job.progress or 0)
            # Handle job_metadata which could be None, dict, or SQLAlchemy Column
            raw_metadata = sub_job.job_metadata
            job_metadata: Dict[str, Any] = (
                raw_metadata if isinstance(raw_metadata, dict) else {}
            )
            await progress_callback(
                sub_progress,
                f"{step_name}: {job_metadata.get('message', 'In progress...')}",
            )

        await asyncio.sleep(poll_interval)


async def _get_unanalyzed_scenes(batch_size: int = 100) -> List[List[str]]:
    """Get scenes that haven't been video analyzed, in batches."""
    async with AsyncSessionLocal() as db:
        # Query for scenes without video_analyzed flag
        query = (
            select(Scene)
            .where(Scene.video_analyzed.is_(False))
            .order_by(Scene.created_at.desc())
        )

        result = await db.execute(query)
        scenes = result.scalars().all()

        # Convert to scene IDs and batch them
        scene_ids = [str(scene.id) for scene in scenes]
        batches = []

        for i in range(0, len(scene_ids), batch_size):
            batch = scene_ids[i : i + batch_size]
            batches.append(batch)

        logger.info(
            f"Found {len(scene_ids)} unanalyzed scenes in {len(batches)} batches"
        )
        return batches


async def _analyze_batch(
    job_service: JobService,
    scene_ids: List[str],
    batch_num: int,
    total_batches: int,
    parent_job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Run analysis on a batch of scenes."""
    logger.info(
        f"Analyzing batch {batch_num}/{total_batches} with {len(scene_ids)} scenes"
    )

    return await _create_and_run_subjob(
        job_service,
        JobType.ANALYSIS,
        {
            "scene_ids": scene_ids,
            "options": {
                "analyze_video_tags": True,
                "analyze_video_markers": True,
                "analyze_scene_text": False,
                "analyze_scene_ai": False,
            },
        },
        parent_job_id,
        f"Analysis batch {batch_num}/{total_batches}",
        progress_callback,
        cancellation_token,
    )


async def _approve_plan_changes(plan_id: int, batch_num: int) -> int:
    """Approve all changes in a plan."""
    async with AsyncSessionLocal() as db:
        from app.models import AnalysisPlan

        query = (
            select(AnalysisPlan)
            .where(AnalysisPlan.id == plan_id)
            .options(selectinload(AnalysisPlan.changes))
        )
        result = await db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Approve all changes
        changes_to_approve = 0
        for change in plan.changes:
            if not change.is_approved:
                change.is_approved = True
                changes_to_approve += 1

        if changes_to_approve > 0:
            await db.commit()
            logger.info(f"Approved {changes_to_approve} changes for batch {batch_num}")

        return changes_to_approve


async def _process_analysis_batch(
    job_service: JobService,
    scene_ids: List[str],
    batch_num: int,
    total_batches: int,
    parent_job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Process a batch of scenes through analysis and apply changes."""
    batch_result: Dict[str, Any] = {
        "batch_num": batch_num,
        "scenes_analyzed": len(scene_ids),
        "changes_approved": 0,
        "changes_applied": 0,
        "errors": [],
    }

    # Step 1: Run video tag/markers analysis
    analysis_result = await _analyze_batch(
        job_service,
        scene_ids,
        batch_num,
        total_batches,
        parent_job_id,
        progress_callback,
        cancellation_token,
    )

    if not analysis_result or analysis_result["status"] != "completed":
        error_msg = f"Analysis failed for batch {batch_num}"
        if analysis_result and analysis_result.get("error"):
            error_msg += f": {analysis_result['error']}"
        errors_list = cast(List[str], batch_result["errors"])
        errors_list.append(error_msg)
        return batch_result

    # Step 2: Check if a plan was generated
    plan_id = analysis_result.get("result", {}).get("plan_id")
    if not plan_id:
        logger.info(f"No plan generated for batch {batch_num}, skipping to next batch")
        return batch_result

    # Step 3: Approve changes
    try:
        changes_to_approve = await _approve_plan_changes(plan_id, batch_num)
        batch_result["changes_approved"] = changes_to_approve
    except ValueError as e:
        errors_list = cast(List[str], batch_result["errors"])
        errors_list.append(str(e))
        return batch_result

    # Step 4: Apply the approved changes
    if changes_to_approve > 0:
        apply_result = await _create_and_run_subjob(
            job_service,
            JobType.APPLY_PLAN,
            {"plan_id": plan_id},
            parent_job_id,
            f"Apply changes batch {batch_num}/{total_batches}",
            progress_callback,
            cancellation_token,
        )

        if not apply_result or apply_result["status"] != "completed":
            error_msg = f"Failed to apply changes for batch {batch_num}"
            if apply_result and apply_result.get("error"):
                error_msg += f": {apply_result['error']}"
            errors_list = cast(List[str], batch_result["errors"])
            errors_list.append(error_msg)
        else:
            batch_result["changes_applied"] = apply_result.get("result", {}).get(
                "applied_changes", 0
            )

    return batch_result


async def _run_workflow_step(
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
    result_key: str,
) -> Optional[Dict[str, Any]]:
    """Run a workflow step and update results."""
    result = await _create_and_run_subjob(
        job_service,
        job_type,
        metadata,
        parent_job_id,
        step_name,
        progress_callback,
        cancellation_token,
    )

    workflow_result["steps"][result_key] = result

    if not result or result["status"] != "completed":
        workflow_result["status"] = "completed_with_errors"
        workflow_result["summary"]["total_errors"] += 1

    return result


async def _process_downloads_step(
    job_service: JobService,
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
) -> Optional[int]:
    """Process downloads and return synced items count."""
    await progress_callback(5, "Step 1/6: Processing downloads")

    downloads_result = await _run_workflow_step(
        job_service,
        JobType.PROCESS_DOWNLOADS,
        {},
        job_id,
        "Process Downloads",
        progress_callback,
        cancellation_token,
        workflow_result,
        "process_downloads",
    )

    if not downloads_result or downloads_result["status"] != "completed":
        await progress_callback(
            100, "Workflow completed with errors in download processing"
        )
        return None

    synced_items = downloads_result.get("result", {}).get("synced_items", 0)
    workflow_result["summary"]["total_synced_items"] = synced_items
    return int(synced_items)


async def process_new_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute the process new scenes workflow.

    This job orchestrates multiple sub-jobs to process newly downloaded scenes.
    """
    logger.info(f"Starting process_new_scenes job {job_id}")

    # Initialize result tracking
    workflow_result: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "steps": {},
        "summary": {
            "total_synced_items": 0,
            "total_scenes_analyzed": 0,
            "total_changes_approved": 0,
            "total_changes_applied": 0,
            "total_errors": 0,
        },
    }

    try:
        # Initial progress
        await progress_callback(0, "Starting process new scenes workflow")

        # Create job service instance
        from app.core.dependencies import get_job_service

        job_service = get_job_service()

        # Step 1: Process downloads
        synced_items = await _process_downloads_step(
            job_service, job_id, progress_callback, cancellation_token, workflow_result
        )

        if synced_items is None:
            return workflow_result

        if synced_items == 0:
            logger.info("No new items downloaded, ending workflow")
            await progress_callback(100, "Workflow completed: No new items to process")
            return workflow_result

        # Step 2: Stash metadata scan
        await progress_callback(
            20, f"Step 2/6: Scanning metadata ({synced_items} new items)"
        )
        await _run_workflow_step(
            job_service,
            JobType.STASH_SCAN,
            {},
            job_id,
            "Stash Metadata Scan",
            progress_callback,
            cancellation_token,
            workflow_result,
            "stash_scan",
        )

        # Step 3: Incremental sync
        await progress_callback(35, "Step 3/6: Running incremental sync")
        await _run_workflow_step(
            job_service,
            JobType.SYNC,
            {"force": False},
            job_id,
            "Incremental Sync",
            progress_callback,
            cancellation_token,
            workflow_result,
            "incremental_sync",
        )

        # Step 4: Get unanalyzed scenes and process in batches
        await progress_callback(50, "Step 4/6: Analyzing unanalyzed scenes")
        scene_batches = await _get_unanalyzed_scenes()

        if scene_batches:
            analysis_summary = await _process_all_batches(
                job_service,
                scene_batches,
                job_id,
                progress_callback,
                cancellation_token,
            )

            # Update workflow result with analysis summary
            workflow_result["steps"]["analysis_batches"] = analysis_summary[
                "batch_results"
            ]
            workflow_result["summary"]["total_scenes_analyzed"] = analysis_summary[
                "total_scenes_analyzed"
            ]
            workflow_result["summary"]["total_changes_approved"] = analysis_summary[
                "total_changes_approved"
            ]
            workflow_result["summary"]["total_changes_applied"] = analysis_summary[
                "total_changes_applied"
            ]
            workflow_result["summary"]["total_errors"] += analysis_summary[
                "total_errors"
            ]

            if analysis_summary["has_errors"]:
                workflow_result["status"] = "completed_with_errors"
        else:
            logger.info("No unanalyzed scenes found")

        # Step 5: Stash metadata generate
        await progress_callback(85, "Step 5/6: Generating Stash metadata")
        await _run_workflow_step(
            job_service,
            JobType.STASH_GENERATE,
            {},
            job_id,
            "Stash Metadata Generate",
            progress_callback,
            cancellation_token,
            workflow_result,
            "stash_generate",
        )

        # Final progress
        await progress_callback(100, "Workflow completed")

        logger.info(
            f"Process new scenes workflow completed: "
            f"{workflow_result['summary']['total_synced_items']} items synced, "
            f"{workflow_result['summary']['total_scenes_analyzed']} scenes analyzed, "
            f"{workflow_result['summary']['total_changes_applied']} changes applied"
        )

        return workflow_result

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        workflow_result["status"] = "cancelled"
        raise
    except Exception as e:
        error_msg = f"Process new scenes workflow failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        workflow_result["status"] = "failed"
        workflow_result["error"] = error_msg
        raise


async def _process_all_batches(
    job_service: JobService,
    scene_batches: List[List[str]],
    parent_job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Process all scene batches for analysis."""
    batch_results: List[Dict[str, Any]] = []
    total_batches = len(scene_batches)

    summary: Dict[str, Any] = {
        "batch_results": batch_results,
        "total_scenes_analyzed": 0,
        "total_changes_approved": 0,
        "total_changes_applied": 0,
        "total_errors": 0,
        "has_errors": False,
    }

    for i, batch in enumerate(scene_batches):
        batch_num = i + 1
        # Calculate progress for this step (50-80% range)
        batch_progress = 50 + int((i / total_batches) * 30)
        await progress_callback(
            batch_progress,
            f"Step 4/6: Processing batch {batch_num}/{total_batches}",
        )

        batch_result = await _process_analysis_batch(
            job_service,
            batch,
            batch_num,
            total_batches,
            parent_job_id,
            progress_callback,
            cancellation_token,
        )

        batch_results.append(batch_result)

        # Update summary
        summary["total_scenes_analyzed"] += batch_result["scenes_analyzed"]
        summary["total_changes_approved"] += batch_result["changes_approved"]
        summary["total_changes_applied"] += batch_result["changes_applied"]
        errors_count = len(cast(List[str], batch_result.get("errors", [])))
        summary["total_errors"] += errors_count

        if batch_result["errors"]:
            summary["has_errors"] = True

    return summary


def register_process_new_scenes_job(job_service: JobService) -> None:
    """Register process new scenes job handler with the job service."""
    job_service.register_handler(JobType.PROCESS_NEW_SCENES, process_new_scenes_job)
    logger.info("Registered process new scenes job handler")
