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

from app.core.database import AsyncSessionLocal
from app.models import Scene
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


async def _create_and_run_subjob(  # noqa: C901
    job_service: JobService,
    job_type: JobType,
    metadata: Dict[str, Any],
    parent_job_id: str,
    step_name: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    step_info: Optional[Dict[str, Any]] = None,
    created_subjobs: Optional[List[str]] = None,
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

    # Track the subjob if tracking list provided
    if created_subjobs is not None:
        created_subjobs.append(sub_job_id)

    # Update parent job metadata with current sub-job info
    async with AsyncSessionLocal() as db:
        parent_job = await job_service.get_job(parent_job_id, db)
        if parent_job:
            # Get current metadata or create new dict
            raw_metadata: Any = parent_job.job_metadata or {}
            current_metadata: Dict[str, Any] = (
                raw_metadata if isinstance(raw_metadata, dict) else {}
            )
            updated_metadata = current_metadata.copy()

            # Update sub_job_ids list
            sub_job_ids = updated_metadata.get("sub_job_ids", [])
            if sub_job_id not in sub_job_ids:
                sub_job_ids.append(sub_job_id)
                updated_metadata["sub_job_ids"] = sub_job_ids

            # Update step info if provided
            if step_info:
                updated_metadata.update(
                    {
                        "current_step": step_info.get("current_step", 1),
                        "total_steps": step_info.get("total_steps", 6),
                        "step_name": step_name,
                        "active_sub_job": {
                            "id": sub_job_id,
                            "type": job_type.value,
                            "status": "running",
                            "progress": 0,
                        },
                    }
                )
            else:
                # Still update active_sub_job even without step_info
                updated_metadata["active_sub_job"] = {
                    "id": sub_job_id,
                    "type": job_type.value,
                    "status": "running",
                    "progress": 0,
                }

            parent_job.job_metadata = updated_metadata  # type: ignore
            await db.commit()

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

            # Update parent job metadata with sub-job status
            parent_job = await job_service.get_job(parent_job_id, db)
            if parent_job and parent_job.job_metadata:
                # Get current metadata
                parent_metadata: Dict[str, Any] = (
                    parent_job.job_metadata
                    if isinstance(parent_job.job_metadata, dict)
                    else {}
                )
                if "active_sub_job" in parent_metadata:
                    updated_metadata = parent_metadata.copy()
                    updated_metadata["active_sub_job"]["status"] = (
                        sub_job.status.value
                        if hasattr(sub_job.status, "value")
                        else sub_job.status
                    )
                    updated_metadata["active_sub_job"]["progress"] = sub_job.progress
                    parent_job.job_metadata = updated_metadata  # type: ignore
                    await db.commit()

            if sub_job.is_finished():
                logger.info(
                    f"Sub-job {sub_job_id} finished with status: {sub_job.status}"
                )
                # Clear active sub-job from parent metadata
                if parent_job and parent_job.job_metadata:
                    job_metadata_for_clear: Dict[str, Any] = (
                        parent_job.job_metadata
                        if isinstance(parent_job.job_metadata, dict)
                        else {}
                    )
                    if "active_sub_job" in job_metadata_for_clear:
                        cleared_metadata = job_metadata_for_clear.copy()
                        cleared_metadata["active_sub_job"] = None
                        parent_job.job_metadata = cleared_metadata  # type: ignore
                        await db.commit()

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
            # Handle job_metadata which could be None, dict, or SQLAlchemy Column
            raw_metadata = sub_job.job_metadata
            job_metadata: Dict[str, Any] = (
                raw_metadata if isinstance(raw_metadata, dict) else {}
            )

            # Don't update the parent progress directly here - let the main workflow handle it
            # Just update the message
            await progress_callback(
                None,  # Don't change progress
                f"{step_name}: {job_metadata.get('message', 'In progress...')}",
            )

        await asyncio.sleep(poll_interval)


async def _check_pending_scenes_for_sync() -> int:
    """Check if there are any scenes pending sync from Stash."""
    from app.core.config import get_settings
    from app.models.sync_history import SyncHistory

    settings = get_settings()

    async with AsyncSessionLocal() as db:
        # Get last sync time
        stmt = (
            select(SyncHistory)
            .where(SyncHistory.entity_type == "scene")
            .where(SyncHistory.status == "completed")
            .order_by(SyncHistory.completed_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_sync_record = result.scalar_one_or_none()

        # Create stash service to check for pending scenes
        stash_service = StashService(
            stash_url=settings.stash.url,
            api_key=settings.stash.api_key,
        )

        try:
            if last_sync_record and last_sync_record.completed_at:
                # Check for scenes updated since last sync
                # Convert to Pacific timezone with Z suffix for Stash compatibility
                import pytz

                pacific_tz = pytz.timezone("America/Los_Angeles")
                completed_at_no_microseconds = last_sync_record.completed_at.replace(
                    microsecond=0
                )
                completed_at_pacific = completed_at_no_microseconds.astimezone(
                    pacific_tz
                )
                formatted_timestamp = completed_at_pacific.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )

                filter_dict = {
                    "updated_at": {
                        "value": formatted_timestamp,
                        "modifier": "GREATER_THAN",
                    }
                }
                logger.info(
                    f"Checking for scenes updated since {last_sync_record.completed_at} "
                    f"(formatted as {formatted_timestamp} for Stash API)"
                )
            else:
                # No previous sync, check total scenes
                filter_dict = None
                logger.info("No previous sync found, checking total scene count")

            scenes_sample, total_pending = await stash_service.get_scenes(
                page=1, per_page=1, filter=filter_dict
            )

            logger.info(f"Found {total_pending} scenes pending sync")
            return total_pending

        finally:
            await stash_service.close()


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
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    created_subjobs: Optional[List[str]] = None,
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
                "detect_video_tags": True,
                "detect_performers": False,
                "detect_studios": False,
                "detect_tags": True,
                "detect_details": False,
            },
            "plan_name": f"Video Tags Analysis - Batch {batch_num} - {len(scene_ids)} scenes",
        },
        parent_job_id,
        f"Analysis batch {batch_num}/{total_batches}",
        progress_callback,
        cancellation_token,
        {"current_step": 4, "total_steps": 6},
        created_subjobs,
    )


async def _approve_plan_changes(plan_id: int, batch_num: int) -> int:
    """Approve all changes in a plan."""
    async with AsyncSessionLocal() as db:
        from app.models import AnalysisPlan
        from app.models.plan_change import ChangeStatus

        # Don't use selectinload with dynamic relationships
        query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
        result = await db.execute(query)
        plan = result.scalar_one_or_none()

        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Approve all changes - using the dynamic relationship
        # Filter for changes that are not already approved
        changes_to_approve = 0
        # Since plan.changes is a dynamic relationship, use it as a query
        unapproved_changes = plan.changes.filter_by(
            accepted=False, rejected=False
        ).all()

        for change in unapproved_changes:
            change.accepted = True
            change.status = ChangeStatus.APPROVED
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
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    created_subjobs: Optional[List[str]] = None,
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
        created_subjobs,
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
            {"current_step": 4, "total_steps": 6},
            created_subjobs,
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
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
    result_key: str,
    step_info: Optional[Dict[str, Any]] = None,
    created_subjobs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Run a workflow step and update results."""
    # Check if already cancelled before creating sub-job
    if cancellation_token and cancellation_token.is_cancelled:
        logger.info(f"Skipping {step_name} - workflow already cancelled")
        return None

    result = await _create_and_run_subjob(
        job_service,
        job_type,
        metadata,
        parent_job_id,
        step_name,
        progress_callback,
        cancellation_token,
        step_info,
        created_subjobs,
    )

    workflow_result["steps"][result_key] = result

    if not result:
        # Sub-job was cancelled or failed to create
        if cancellation_token and cancellation_token.is_cancelled:
            workflow_result["status"] = "cancelled"
        else:
            workflow_result["status"] = "completed_with_errors"
            workflow_result["summary"]["total_errors"] += 1
    elif result["status"] != "completed":
        workflow_result["status"] = "completed_with_errors"
        workflow_result["summary"]["total_errors"] += 1

    return result


async def _update_parent_job_step(
    job_service: JobService,
    job_id: str,
    step_number: int,
    step_name: str,
    total_steps: int = 6,
) -> None:
    """Update parent job metadata with current step info."""
    async with AsyncSessionLocal() as db:
        parent_job = await job_service.get_job(job_id, db)
        if parent_job:
            raw_metadata: Any = parent_job.job_metadata or {}
            metadata: Dict[str, Any] = (
                raw_metadata if isinstance(raw_metadata, dict) else {}
            )
            metadata.update(
                {
                    "current_step": step_number,
                    "total_steps": total_steps,
                    "step_name": step_name,
                    "active_sub_job": metadata.get(
                        "active_sub_job"
                    ),  # Preserve active sub-job
                }
            )
            parent_job.job_metadata = metadata  # type: ignore

            # For the final step, clear active_sub_job
            if step_number == 6:
                metadata["active_sub_job"] = None
                parent_job.job_metadata = metadata  # type: ignore

            await db.commit()
            await db.refresh(parent_job)

            # Send WebSocket update for step changes
            from app.services.websocket_manager import websocket_manager

            job_data = {
                "id": parent_job.id,
                "type": (
                    parent_job.type.value
                    if hasattr(parent_job.type, "value")
                    else parent_job.type
                ),
                "status": (
                    parent_job.status.value
                    if hasattr(parent_job.status, "value")
                    else parent_job.status
                ),
                "progress": parent_job.progress,
                "metadata": metadata,
            }
            await websocket_manager.broadcast_job_update(job_data)


async def _process_downloads_step(
    job_service: JobService,
    job_id: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any],
    workflow_result: Dict[str, Any],
    created_subjobs: Optional[List[str]] = None,
) -> Optional[int]:
    """Process downloads and return synced items count."""
    await progress_callback(5, "Step 1/6: Processing downloads")
    await _update_parent_job_step(job_service, job_id, 1, "Processing downloads")

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
        {"current_step": 1, "total_steps": 6},
        created_subjobs,
    )

    # Check if cancelled
    if not downloads_result:
        # Sub-job was cancelled
        return None

    if downloads_result["status"] != "completed":
        # Don't set progress to 100% here - let the main workflow handle it
        logger.warning("Download processing step did not complete successfully")
        return None

    synced_items = downloads_result.get("result", {}).get("synced_items", 0)
    workflow_result["summary"]["total_synced_items"] = synced_items
    return int(synced_items)


async def _wait_for_subjobs_to_finish(
    job_service: JobService,
    parent_job_id: str,
    created_subjobs: List[str],
    max_wait_seconds: int = 300,  # 5 minutes max wait
) -> None:
    """Wait for all subjobs to reach a terminal state.

    This ensures that when a workflow job is cancelled, it doesn't transition
    to CANCELLED status until all of its subjobs have finished cancelling.
    This prevents the parent job from appearing as cancelled while subjobs
    are still running or in the process of being cancelled.
    """
    if not created_subjobs:
        return

    logger.info(
        f"Waiting for {len(created_subjobs)} subjobs to finish for parent job {parent_job_id}"
    )

    start_time = asyncio.get_event_loop().time()
    poll_interval = 1  # second

    while True:
        # Check if we've exceeded max wait time
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > max_wait_seconds:
            logger.warning(
                f"Timeout waiting for subjobs to finish after {elapsed:.1f}s"
            )
            break

        # Check status of all subjobs
        all_finished = True
        async with AsyncSessionLocal() as db:
            for subjob_id in created_subjobs:
                subjob = await job_service.get_job(subjob_id, db)
                if subjob and not subjob.is_finished():
                    all_finished = False
                    break

        if all_finished:
            logger.info(f"All {len(created_subjobs)} subjobs have finished")
            break

        await asyncio.sleep(poll_interval)


async def process_new_scenes_job(  # noqa: C901
    job_id: str,
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
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

    # Track all created subjobs for cleanup on cancellation
    created_subjobs: List[str] = []

    # Step weights for progress calculation
    STEP_WEIGHTS = {
        1: (0, 15),  # Process Downloads: 0-15%
        2: (15, 30),  # Stash Scan: 15-30%
        3: (30, 45),  # Incremental Sync: 30-45%
        4: (45, 80),  # Batch Analysis: 45-80%
        5: (80, 95),  # Stash Generate: 80-95%
        6: (95, 100),  # Completion: 95-100%
    }

    # Track current step for weighted progress
    current_step_info = {"step": 0, "step_start": 0, "step_end": 0}

    # Create a weighted progress callback
    async def weighted_progress_callback(
        progress: Optional[int], message: Optional[str]
    ) -> None:
        """Update progress with weighted calculation based on current step."""
        if progress is not None:
            # Use the direct progress value (for manual progress setting)
            await progress_callback(progress, message)
        elif message:
            # Just update the message without changing progress
            await progress_callback(None, message)

    def set_current_step(step_num: int) -> None:
        """Set the current step for weighted progress calculation."""
        if step_num in STEP_WEIGHTS:
            current_step_info["step"] = step_num
            current_step_info["step_start"], current_step_info["step_end"] = (
                STEP_WEIGHTS[step_num]
            )

    async def step_progress_callback(
        progress: Optional[int], message: Optional[str]
    ) -> None:
        """Calculate weighted progress based on current step."""
        if progress is not None and current_step_info["step"] > 0:
            # Calculate weighted progress within the current step's range
            step_start = current_step_info["step_start"]
            step_end = current_step_info["step_end"]
            step_range = step_end - step_start
            weighted_progress = int(step_start + (progress / 100.0) * step_range)
            await progress_callback(weighted_progress, message)
        else:
            # Just pass through the message
            await progress_callback(progress, message)

    try:
        # Initial progress
        await weighted_progress_callback(0, "Starting process new scenes workflow")

        # Create job service instance
        from app.core.dependencies import get_job_service

        job_service = get_job_service()

        # Initialize parent job metadata with workflow info
        async with AsyncSessionLocal() as db:
            parent_job = await job_service.get_job(job_id, db)
            if parent_job:
                raw_initial_metadata: Any = parent_job.job_metadata or {}
                initial_metadata: Dict[str, Any] = (
                    raw_initial_metadata
                    if isinstance(raw_initial_metadata, dict)
                    else {}
                )
                initial_metadata.update(
                    {
                        "current_step": 0,
                        "total_steps": 6,
                        "step_name": "Initializing",
                        "active_sub_job": None,
                        "sub_job_ids": [],  # Track all subjobs created
                    }
                )
                parent_job.job_metadata = initial_metadata  # type: ignore
                await db.commit()

        # Step 1: Process downloads
        synced_items = await _process_downloads_step(
            job_service,
            job_id,
            progress_callback,
            cancellation_token,
            workflow_result,
            created_subjobs,
        )

        if synced_items is None:
            # Check if cancelled
            if cancellation_token and cancellation_token.is_cancelled:
                raise asyncio.CancelledError()
            return workflow_result

        # Step 2: Stash metadata scan (skip if no new items)
        if synced_items > 0:
            await weighted_progress_callback(
                20, f"Step 2/6: Scanning metadata ({synced_items} new items)"
            )
            await _update_parent_job_step(job_service, job_id, 2, "Scanning metadata")
            scan_result = await _run_workflow_step(
                job_service,
                JobType.STASH_SCAN,
                {},
                job_id,
                "Stash Metadata Scan",
                progress_callback,
                cancellation_token,
                workflow_result,
                "stash_scan",
                {"current_step": 2, "total_steps": 6},
                created_subjobs,
            )
            # Check if cancelled
            if (
                not scan_result
                and cancellation_token
                and cancellation_token.is_cancelled
            ):
                raise asyncio.CancelledError()
        else:
            logger.info("No new items downloaded, skipping Stash metadata scan")
            await weighted_progress_callback(
                20, "Step 2/6: Skipped - No new items to scan"
            )
            await _update_parent_job_step(
                job_service, job_id, 2, "Skipped - No new items"
            )

        # Step 3: Incremental sync (only if there are pending scenes)
        # Check cancellation before proceeding
        if cancellation_token and cancellation_token.is_cancelled:
            raise asyncio.CancelledError()

        await weighted_progress_callback(35, "Step 3/6: Checking for pending scenes")
        await _update_parent_job_step(
            job_service, job_id, 3, "Checking for pending scenes"
        )

        pending_scenes = await _check_pending_scenes_for_sync()
        if pending_scenes > 0:
            await weighted_progress_callback(
                35,
                f"Step 3/6: Running incremental sync ({pending_scenes} pending scenes)",
            )
            await _update_parent_job_step(
                job_service,
                job_id,
                3,
                f"Running incremental sync ({pending_scenes} scenes)",
            )
            sync_result = await _run_workflow_step(
                job_service,
                JobType.SYNC,
                {"force": False},
                job_id,
                "Incremental Sync",
                progress_callback,
                cancellation_token,
                workflow_result,
                "incremental_sync",
                {"current_step": 3, "total_steps": 6},
                created_subjobs,
            )
            # Check if cancelled
            if (
                not sync_result
                and cancellation_token
                and cancellation_token.is_cancelled
            ):
                raise asyncio.CancelledError()
        else:
            logger.info("No pending scenes to sync, skipping incremental sync")
            await weighted_progress_callback(
                45, "Step 3/6: Skipped - No pending scenes to sync"
            )
            await _update_parent_job_step(
                job_service, job_id, 3, "Skipped - No pending scenes"
            )
            workflow_result["steps"]["incremental_sync"] = {
                "status": "skipped",
                "message": "No pending scenes to sync",
            }

        # Step 4: Analyze scenes (only if there are unanalyzed scenes)
        # Check cancellation before proceeding
        if cancellation_token and cancellation_token.is_cancelled:
            raise asyncio.CancelledError()

        await weighted_progress_callback(50, "Step 4/6: Checking for unanalyzed scenes")
        await _update_parent_job_step(
            job_service, job_id, 4, "Checking for unanalyzed scenes"
        )
        scene_batches = await _get_unanalyzed_scenes()

        if scene_batches:
            total_unanalyzed = sum(len(batch) for batch in scene_batches)
            await weighted_progress_callback(
                50, f"Step 4/6: Analyzing {total_unanalyzed} unanalyzed scenes"
            )
            await _update_parent_job_step(
                job_service, job_id, 4, f"Analyzing {total_unanalyzed} scenes"
            )

            analysis_summary = await _process_all_batches(
                job_service,
                scene_batches,
                job_id,
                progress_callback,
                cancellation_token,
                created_subjobs,
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
            logger.info("No unanalyzed scenes found, skipping analysis")
            await weighted_progress_callback(
                80, "Step 4/6: Skipped - No unanalyzed scenes"
            )
            await _update_parent_job_step(
                job_service, job_id, 4, "Skipped - No unanalyzed scenes"
            )
            workflow_result["steps"]["analysis_batches"] = {
                "status": "skipped",
                "message": "No unanalyzed scenes found",
            }

        # Step 5: Stash metadata generate
        # Check cancellation before proceeding
        if cancellation_token and cancellation_token.is_cancelled:
            raise asyncio.CancelledError()

        await weighted_progress_callback(85, "Step 5/6: Generating Stash metadata")
        await _update_parent_job_step(job_service, job_id, 5, "Generating metadata")
        generate_result = await _run_workflow_step(
            job_service,
            JobType.STASH_GENERATE,
            {},
            job_id,
            "Stash Metadata Generate",
            progress_callback,
            cancellation_token,
            workflow_result,
            "stash_generate",
            {"current_step": 5, "total_steps": 6},
            created_subjobs,
        )
        # Check if cancelled
        if (
            not generate_result
            and cancellation_token
            and cancellation_token.is_cancelled
        ):
            raise asyncio.CancelledError()

        # Final progress - only set to 100% if we actually completed
        if (
            workflow_result["status"] == "completed"
            or workflow_result["status"] == "completed_with_errors"
        ):
            # Update to step 6 first, then set progress to 100%
            await _update_parent_job_step(job_service, job_id, 6, "Completed")
            # Small delay to ensure the step update is committed and propagated
            await asyncio.sleep(0.5)
            await weighted_progress_callback(100, "Workflow completed")

        logger.info(
            f"Process new scenes workflow completed: "
            f"{workflow_result['summary']['total_synced_items']} items synced, "
            f"{workflow_result['summary']['total_scenes_analyzed']} scenes analyzed, "
            f"{workflow_result['summary']['total_changes_applied']} changes applied"
        )

        # Final delay to ensure all updates are propagated before job completes
        await asyncio.sleep(0.5)

        return workflow_result

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        workflow_result["status"] = "cancelled"

        # Wait for all subjobs to finish before allowing parent to transition to CANCELLED
        if created_subjobs:
            logger.info(
                f"Waiting for {len(created_subjobs)} subjobs to finish before marking parent as cancelled"
            )
            await _wait_for_subjobs_to_finish(job_service, job_id, created_subjobs)

        # Don't update progress to 100% - leave it at current position
        # Update parent job status to show cancellation
        await _update_parent_job_step(
            job_service, job_id, current_step_info.get("step", 0), "Cancelled"
        )
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
    progress_callback: Callable[[Optional[int], Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    created_subjobs: Optional[List[str]] = None,
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
        # Check cancellation before processing each batch
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info("Batch processing cancelled")
            break

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
            created_subjobs,
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
