import asyncio
import logging
from collections.abc import Awaitable
from typing import Any, Callable, Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import AnalysisPlan, PlanChange
from app.models.analysis_plan import PlanStatus
from app.models.job import JobType
from app.services.analysis.analysis_service import AnalysisService
from app.services.analysis.models import AnalysisOptions
from app.services.job_service import JobService
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService

from .analysis_jobs_helpers import calculate_plan_summary


def _format_summary(raw_summary: dict[str, int]) -> dict[str, Any]:
    """Format the raw summary into the expected structure."""
    total = sum(raw_summary.values())

    by_field = {
        "performers": raw_summary.get("performers_to_add", 0),
        "tags": raw_summary.get("tags_to_add", 0),
        "studio": raw_summary.get("studios_to_set", 0),
        "title": raw_summary.get("titles_to_update", 0),
        "details": raw_summary.get("details_to_update", 0),
        "markers": raw_summary.get("markers_to_add", 0),
    }

    by_action = {
        "add": (
            raw_summary.get("performers_to_add", 0)
            + raw_summary.get("tags_to_add", 0)
            + raw_summary.get("markers_to_add", 0)
        ),
        "set": (
            raw_summary.get("studios_to_set", 0)
            + raw_summary.get("titles_to_update", 0)
        ),
        "update": raw_summary.get("details_to_update", 0),
    }

    return {
        "total": total,
        "by_field": by_field,
        "by_action": by_action,
    }


logger = logging.getLogger(__name__)


async def analyze_scenes_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    cancellation_token: Optional[Any] = None,
    scene_ids: Optional[list[str]] = None,
    options: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute scene analysis as a background job."""
    plan_id: Optional[int] = None
    scenes_processed: int = 0

    # Create a wrapper to track progress
    async def tracking_progress_callback(progress: int, message: str) -> None:
        nonlocal scenes_processed
        scenes_processed = _extract_scenes_processed(message, scenes_processed)
        await progress_callback(progress, message)

    try:
        # Initialize services
        services = await _initialize_services(job_id, scene_ids)

        # Execute analysis
        plan = await _execute_analysis(
            services,
            job_id,
            scene_ids,
            options,
            kwargs,
            tracking_progress_callback,
            cancellation_token,
        )

        # Process results
        result, plan_id = await _process_analysis_results(plan, job_id, scene_ids)

        return result

    except asyncio.CancelledError:
        return await _handle_job_cancellation(
            job_id, plan_id, scenes_processed, scene_ids
        )
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}", exc_info=True)
        await progress_callback(100, error_msg)
        raise


def _extract_scenes_processed(message: str, current_count: int) -> int:
    """Extract scenes processed count from progress message."""
    if "Processed" in message and "/" in message:
        try:
            processed_part = message.split("Processed")[1].split("scenes")[0]
            return int(processed_part.split("/")[0].strip())
        except (IndexError, ValueError):
            pass
    return current_count


async def _initialize_services(
    job_id: str, scene_ids: Optional[list[str]]
) -> dict[str, Any]:
    """Initialize required services for analysis."""
    logger.info(
        f"Starting analyze_scenes job {job_id} for {len(scene_ids or [])} scenes"
    )
    logger.debug(f"Scene IDs received in job: {scene_ids}")

    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )
    openai_client = (
        OpenAIClient(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            base_url=settings.openai.base_url,
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature,
            timeout=settings.openai.timeout,
        )
        if settings.openai.api_key
        else None
    )

    return {
        "settings": settings,
        "stash_service": stash_service,
        "openai_client": openai_client,
    }


async def _execute_analysis(
    services: dict[str, Any],
    job_id: str,
    scene_ids: Optional[list[str]],
    options: Optional[dict[str, Any]],
    kwargs: dict[str, Any],
    progress_callback: Callable[[int, str], Awaitable[None]],
    cancellation_token: Optional[Any],
) -> Any:
    """Execute the scene analysis."""
    if services["openai_client"] is None:
        raise ValueError("OpenAI client is required for analysis")

    analysis_options = AnalysisOptions(**options) if options else AnalysisOptions()
    plan_name = kwargs.get("plan_name")

    async with AsyncSessionLocal() as db:
        analysis_service = AnalysisService(
            openai_client=services["openai_client"],
            stash_service=services["stash_service"],
            settings=services["settings"],
        )

        logger.info(f"Creating analysis service and starting analysis for job {job_id}")

        plan = await analysis_service.analyze_scenes(
            scene_ids=scene_ids,
            options=analysis_options,
            job_id=job_id,
            db=db,
            progress_callback=progress_callback,
            plan_name=plan_name,
            cancellation_token=cancellation_token,
        )

        logger.info(
            f"Analysis completed for job {job_id}, plan ID: {getattr(plan, 'id', None)}"
        )

        return plan


async def _process_analysis_results(
    plan: Any, job_id: str, scene_ids: Optional[list[str]]
) -> tuple[dict[str, Any], Optional[int]]:
    """Process the analysis results and return formatted output."""
    plan_id: Optional[int] = None

    # Check if plan has an ID (was saved to database)
    if not hasattr(plan, "id") or plan.id is None:
        logger.info(f"No changes found for job {job_id}, returning minimal result")
        result = {
            "plan_id": None,
            "total_changes": 0,
            "scenes_analyzed": len(scene_ids or []),
            "summary": {
                "total": 0,
                "by_field": {},
                "by_action": {},
            },
        }
    else:
        async with AsyncSessionLocal() as db:
            try:
                plan_id = int(plan.id)

                # Re-fetch the plan in our current session
                plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
                plan_result = await db.execute(plan_query)
                fresh_plan = plan_result.scalar_one()

                # Query changes directly
                logger.debug(f"Querying changes for plan {plan_id}")
                changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
                changes_result = await db.execute(changes_query)
                changes_list = list(changes_result.scalars().all())

                logger.debug(f"Loaded {len(changes_list)} changes for plan {plan_id}")

                # Calculate summary
                raw_summary = calculate_plan_summary(changes_list)
                summary = _format_summary(raw_summary)
                total_changes = len(changes_list)
                scenes_analyzed = fresh_plan.get_metadata("scene_count", 0)

                logger.info(
                    f"Summary calculated for job {job_id}: {total_changes} total changes"
                )

                result = {
                    "plan_id": plan_id,
                    "total_changes": total_changes,
                    "scenes_analyzed": scenes_analyzed,
                    "summary": summary,
                }

            except Exception as e:
                logger.error(
                    f"Error calculating summary for job {job_id}: {str(e)}",
                    exc_info=True,
                )
                raise

            # Commit the plan finalization changes
            await db.commit()

    logger.info(f"Job {job_id} completed successfully with result: {result}")
    return result, plan_id


async def _handle_job_cancellation(
    job_id: str,
    plan_id: Optional[int],
    scenes_processed: int,
    scene_ids: Optional[list[str]],
) -> dict[str, Any]:
    """Handle job cancellation and update plan status."""
    logger.info(
        f"Job {job_id} was cancelled after processing {scenes_processed} scenes"
    )

    cancellation_result: dict[str, Any] = {
        "plan_id": plan_id,
        "total_changes": 0,
        "scenes_analyzed": scenes_processed,
        "summary": {
            "total": 0,
            "by_field": {},
            "by_action": {},
        },
        "cancelled": True,
        "total_scenes": len(scene_ids or []),
    }

    # Update plan status if one was created
    if plan_id is not None:
        await _update_cancelled_plan_status(plan_id, cancellation_result)

    # Store the partial result
    await _store_cancellation_result(job_id, cancellation_result, scenes_processed)

    raise


async def _update_cancelled_plan_status(
    plan_id: int, cancellation_result: dict[str, Any]
) -> None:
    """Update plan status to DRAFT and get actual change count."""
    logger.info(f"Setting plan {plan_id} status to DRAFT due to job cancellation")

    async with AsyncSessionLocal() as db:
        from app.services.analysis.plan_manager import PlanManager

        plan_manager = PlanManager()
        cancelled_plan = await plan_manager.get_plan(plan_id, db)

        if cancelled_plan is not None:
            # Get actual change count
            changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
            changes_result = await db.execute(changes_query)
            changes_list = list(changes_result.scalars().all())

            cancellation_result["total_changes"] = len(changes_list)
            raw_summary = calculate_plan_summary(changes_list)
            cancellation_result["summary"] = _format_summary(raw_summary)

            if cancelled_plan.status == PlanStatus.PENDING:
                cancelled_plan.status = PlanStatus.DRAFT  # type: ignore[assignment]
                await db.commit()
                logger.info(f"Successfully updated plan {plan_id} status to DRAFT")


async def _store_cancellation_result(
    job_id: str, cancellation_result: dict[str, Any], scenes_processed: int
) -> None:
    """Store the cancellation result in job metadata."""
    async with AsyncSessionLocal() as db:
        from app.repositories.job_repository import job_repository

        job = await job_repository.get_job(job_id, db)
        if job:
            job.result = cancellation_result  # type: ignore[assignment]
            job.processed_items = scenes_processed  # type: ignore[assignment]
            await db.commit()


async def _create_analysis_service() -> AnalysisService:
    """Create and return an AnalysisService instance."""
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )
    openai_client = (
        OpenAIClient(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            base_url=settings.openai.base_url,
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature,
            timeout=settings.openai.timeout,
        )
        if settings.openai.api_key
        else None
    )

    if openai_client is None:
        raise ValueError("OpenAI client is required for analysis")

    return AnalysisService(
        openai_client=openai_client, stash_service=stash_service, settings=settings
    )


async def _apply_single_plan_in_bulk(
    analysis_service: AnalysisService,
    plan_id: int,
    job_id: str,
) -> tuple[int, list[dict], Optional[Exception]]:
    """Apply a single plan and return results."""
    try:
        result = await analysis_service.apply_plan(
            plan_id=str(plan_id),
            auto_approve=True,  # Bulk apply assumes all changes are approved
            job_id=f"{job_id}_plan_{plan_id}",
        )

        errors = []
        if result.errors:
            errors = [{**error, "plan_id": plan_id} for error in result.errors]

        return result.applied_changes, errors, None
    except Exception as e:
        logger.error(f"Failed to apply plan {plan_id}: {str(e)}", exc_info=True)
        return 0, [], e


async def _trigger_scene_sync_for_bulk(
    job_id: str, modified_scene_ids: list[str]
) -> Optional[dict]:
    """Trigger scene sync after bulk apply."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.job import JobType
        from app.services.job_service import job_service

        async with AsyncSessionLocal() as db:
            sync_job = await job_service.create_job(
                job_type=JobType.SYNC_SCENES,
                db=db,
                metadata={
                    "scene_ids": modified_scene_ids,
                    "triggered_by": f"bulk_apply_{job_id}",
                    "force": False,
                },
            )
            await db.commit()
            logger.info(
                f"Created scene sync job {sync_job.id} for {len(modified_scene_ids)} scenes after bulk apply"
            )
            return None
    except Exception as sync_error:
        logger.error(
            f"Failed to trigger scene sync after bulk apply: {str(sync_error)}",
            exc_info=True,
        )
        return {
            "error": f"Failed to trigger scene sync: {str(sync_error)}",
            "type": "sync_trigger_failure",
        }


async def _apply_bulk_plans(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    plan_ids: list[int],
    cancellation_token: Optional[Any] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Apply multiple analysis plans in bulk."""
    # Initialize tracking variables
    state = _BulkApplyState(plan_ids)

    # Create service instances
    analysis_service = await _create_analysis_service()

    # Count total changes if needed
    total_changes = await _count_total_changes_if_needed(
        kwargs.get("total_changes", 0), plan_ids, progress_callback
    )

    # Process each plan
    for idx, plan_id in enumerate(plan_ids):
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Bulk apply job {job_id} cancelled")
            break

        await _process_single_plan(
            analysis_service,
            plan_id,
            idx,
            job_id,
            state,
            total_changes,
            progress_callback,
        )

    # Trigger sync if needed
    if state.total_changes_applied > 0 and state.all_modified_scene_ids:
        await _trigger_sync_after_bulk_apply(job_id, state, progress_callback)

    await progress_callback(100, "Bulk apply completed")

    return {
        "job_type": "bulk_apply",
        "total_plans": len(plan_ids),
        "plans_applied": state.total_applied,
        "plans_failed": state.total_failed,
        "total_changes_applied": state.total_changes_applied,
        "errors": state.all_errors,
        "success_rate": (
            (state.total_applied / state.total_plans * 100)
            if state.total_plans > 0
            else 0
        ),
    }


class _BulkApplyState:
    """Track state during bulk apply operation."""

    def __init__(self, plan_ids: list[int]):
        self.total_plans = len(plan_ids)
        self.total_applied = 0
        self.total_failed = 0
        self.total_changes_applied = 0
        self.all_errors: list[dict[str, Any]] = []
        self.all_modified_scene_ids: set[str] = set()
        self.changes_processed_so_far = 0


async def _count_total_changes_if_needed(
    existing_count: int,
    plan_ids: list[int],
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> int:
    """Count total changes across all plans if not already provided."""
    if existing_count > 0:
        return existing_count

    logger.info(f"Counting total changes across {len(plan_ids)} plans...")
    await progress_callback(0, f"Counting changes across {len(plan_ids)} plans...")

    total_changes = 0
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func, or_, select

        from app.models import PlanChange
        from app.models.plan_change import ChangeStatus

        for plan_id in plan_ids:
            count_query = select(func.count(PlanChange.id)).where(
                PlanChange.plan_id == plan_id,
                or_(
                    PlanChange.status == ChangeStatus.APPROVED,
                    PlanChange.accepted.is_(True),
                ),
                PlanChange.applied.is_(False),
            )
            count_result = await db.execute(count_query)
            plan_changes = count_result.scalar_one()
            total_changes += plan_changes

    logger.info(f"Found {total_changes} total changes to apply")
    return total_changes


async def _process_single_plan(
    analysis_service: AnalysisService,
    plan_id: int,
    idx: int,
    job_id: str,
    state: _BulkApplyState,
    total_changes: int,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Process a single plan in the bulk apply operation."""
    plan_progress_callback = _create_plan_progress_callback(
        idx,
        state.changes_processed_so_far,
        state.total_plans,
        total_changes,
        progress_callback,
    )

    try:
        result = await analysis_service.apply_plan(
            plan_id=str(plan_id),
            auto_approve=True,
            job_id=f"{job_id}_plan_{plan_id}",
            progress_callback=plan_progress_callback,
        )

        if result.errors:
            for error in result.errors:
                state.all_errors.append({**error, "plan_id": plan_id})

        if result.applied_changes > 0:
            state.total_applied += 1
            state.total_changes_applied += result.applied_changes
            state.all_modified_scene_ids.update(result.modified_scene_ids)

        state.changes_processed_so_far = state.total_changes_applied

    except Exception as e:
        logger.error(f"Failed to apply plan {plan_id}: {str(e)}", exc_info=True)
        state.total_failed += 1
        state.all_errors.append(
            {
                "plan_id": plan_id,
                "error": str(e),
                "type": "plan_application_failure",
            }
        )


def _create_plan_progress_callback(
    current_idx: int,
    current_changes_before: int,
    total_plans: int,
    total_changes: int,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> Callable[[int, str], Awaitable[None]]:
    """Create a progress callback for individual plan processing."""

    async def callback(plan_progress: int, message: str) -> None:
        if total_changes > 0:
            estimated_changes_per_plan = total_changes / total_plans
            estimated_changes_in_progress = (
                plan_progress / 100
            ) * estimated_changes_per_plan
            total_estimated_progress = (
                current_changes_before + estimated_changes_in_progress
            )
            overall_progress = int((total_estimated_progress / total_changes) * 90)
        else:
            overall_progress = int(
                ((current_idx + (plan_progress / 100)) / total_plans) * 90
            )

        await progress_callback(
            min(overall_progress, 90),
            f"Plan {current_idx + 1}/{total_plans}: {message}",
        )

    return callback


async def _trigger_sync_after_bulk_apply(
    job_id: str,
    state: _BulkApplyState,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
) -> None:
    """Trigger scene sync after bulk apply completes."""
    logger.info(
        f"Bulk apply job {job_id} applied {state.total_changes_applied} changes "
        f"to {len(state.all_modified_scene_ids)} scenes, triggering scene sync"
    )
    await progress_callback(95, "Starting scene sync...")

    sync_error = await _trigger_scene_sync_for_bulk(
        job_id, list(state.all_modified_scene_ids)
    )
    if sync_error:
        state.all_errors.append(sync_error)


async def apply_analysis_plan_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    plan_id: Optional[str] = None,
    cancellation_token: Optional[Any] = None,
    auto_approve: bool = False,
    change_ids: Optional[list[int]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Apply an analysis plan as a background job."""
    try:
        # Check if this is a bulk apply operation
        bulk_apply = kwargs.get("bulk_apply", False)
        plans_to_apply = kwargs.get("plans_to_apply", [])

        if bulk_apply and plans_to_apply:
            logger.info(
                f"Starting bulk apply job {job_id} for {len(plans_to_apply)} plans"
            )
            return await _apply_bulk_plans(
                job_id, progress_callback, plans_to_apply, cancellation_token, **kwargs
            )

        if not plan_id:
            raise ValueError("plan_id is required for single plan application")

        logger.info(f"Starting apply_analysis_plan job {job_id} for plan {plan_id}")

        # Create service instances
        settings = await load_settings_with_db_overrides()
        stash_service = StashService(
            stash_url=settings.stash.url,
            api_key=settings.stash.api_key,
            timeout=settings.stash.timeout,
            max_retries=settings.stash.max_retries,
        )
        openai_client = (
            OpenAIClient(
                api_key=settings.openai.api_key,
                model=settings.openai.model,
                base_url=settings.openai.base_url,
                max_tokens=settings.openai.max_tokens,
                temperature=settings.openai.temperature,
                timeout=settings.openai.timeout,
            )
            if settings.openai.api_key
            else None
        )

        # Execute plan application with progress callback
        if openai_client is None:
            raise ValueError("OpenAI client is required for analysis")
        analysis_service = AnalysisService(
            openai_client=openai_client, stash_service=stash_service, settings=settings
        )

        result = await analysis_service.apply_plan(
            plan_id=plan_id,
            auto_approve=auto_approve,
            job_id=job_id,
            progress_callback=progress_callback,
            change_ids=change_ids,
        )

        # If changes were successfully applied, trigger an incremental sync
        if result.applied_changes > 0 and result.modified_scene_ids:
            logger.info(
                f"Plan {plan_id} applied {result.applied_changes} changes to {len(result.modified_scene_ids)} scenes, triggering incremental sync"
            )
            await progress_callback(
                95,
                f"Applied {result.applied_changes} changes, starting incremental sync...",
            )

            try:
                from app.core.database import AsyncSessionLocal
                from app.models.job import JobType
                from app.services.job_service import job_service

                async with AsyncSessionLocal() as db:
                    # Create an incremental sync job for the modified scenes
                    sync_job = await job_service.create_job(
                        job_type=JobType.SYNC_SCENES,
                        db=db,
                        metadata={
                            "scene_ids": result.modified_scene_ids,
                            "incremental": True,
                            "triggered_by": f"apply_plan_{plan_id}",
                            "force": False,
                        },
                    )
                    await db.commit()
                    logger.info(
                        f"Created incremental sync job {sync_job.id} for {len(result.modified_scene_ids)} scenes after applying plan {plan_id}"
                    )

            except Exception as sync_error:
                # Log the error but don't fail the whole job
                logger.error(
                    f"Failed to trigger scene sync after applying plan {plan_id}: {str(sync_error)}",
                    exc_info=True,
                )
                # Add to errors but continue
                result.errors.append(
                    {
                        "error": f"Failed to trigger scene sync: {str(sync_error)}",
                        "type": "sync_trigger_failure",
                    }
                )

            await progress_callback(
                100, f"Plan applied successfully with {result.applied_changes} changes"
            )

    except Exception as e:
        logger.error(f"Failed to apply plan {plan_id}: {str(e)}", exc_info=True)
        # Return error result instead of re-raising
        return {
            "plan_id": plan_id,
            "applied_changes": 0,
            "failed_changes": 0,
            "skipped_changes": 0,
            "total_changes": 0,
            "success_rate": 0,
            "errors": [{"error": str(e), "type": "job_failure"}],
        }

    return {
        "plan_id": plan_id,
        "applied_changes": result.applied_changes,
        "failed_changes": result.failed_changes,
        "skipped_changes": result.skipped_changes,
        "total_changes": result.total_changes,
        "success_rate": (
            (result.applied_changes / result.total_changes * 100)
            if result.total_changes > 0
            else 0
        ),
        "errors": result.errors,
    }


async def generate_scene_details_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    scene_ids: Optional[list[str]] = None,
    **kwargs: Any,  # noqa: ARG001
) -> dict[str, Any]:
    """Generate detailed information for scenes as a background job."""
    logger.info(
        f"Starting generate_scene_details job {job_id} for {len(scene_ids or [])} scenes"
    )

    # Create service instances
    settings = await load_settings_with_db_overrides()
    stash_service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )
    openai_client = (
        OpenAIClient(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            base_url=settings.openai.base_url,
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature,
            timeout=settings.openai.timeout,
        )
        if settings.openai.api_key
        else None
    )

    if not openai_client:
        raise ValueError("OpenAI client is required for scene details generation")

    # Execute scene details generation
    if openai_client is None:
        raise ValueError("OpenAI client is required for analysis")
    analysis_service = AnalysisService(
        openai_client=openai_client, stash_service=stash_service, settings=settings
    )

    # Generate details for each scene
    results = []
    total_scenes = len(scene_ids or [])

    # Get scenes from local database
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import Scene

    async with AsyncSessionLocal() as db:
        for idx, scene_id in enumerate(scene_ids or []):
            progress = int((idx / total_scenes) * 100)
            await progress_callback(
                progress, f"Generating details for scene {idx + 1} of {total_scenes}"
            )

            try:
                # Get scene from local database
                stmt = select(Scene).where(Scene.id == scene_id)
                result = await db.execute(stmt)
                scene = result.scalar_one_or_none()

                if scene:
                    from app.services.analysis.models import AnalysisOptions

                    # Use the scene directly from database
                    changes = await analysis_service.analyze_single_scene(
                        scene,
                        AnalysisOptions(detect_details=True),
                    )
                    details_changes = [c for c in changes if c.field == "details"]
                    details = (
                        details_changes[0].proposed_value if details_changes else None
                    )
                else:
                    details = None
                    logger.warning(f"Scene {scene_id} not found in database")

                results.append(
                    {"scene_id": scene_id, "status": "success", "details": details}
                )
            except Exception as e:
                logger.error(
                    f"Failed to generate details for scene {scene_id}: {str(e)}"
                )
                results.append(
                    {"scene_id": scene_id, "status": "failed", "error": str(e)}
                )

    await progress_callback(100, "Scene details generation completed")

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_results = [r for r in results if r["status"] == "failed"]

    job_result = {
        "total_scenes": total_scenes,
        "successful": success_count,
        "failed": total_scenes - success_count,
        "results": results,
        "errors": failed_results,
    }

    # If all scenes failed, mark the job as failed
    if success_count == 0 and total_scenes > 0:
        job_result["status"] = "failed"
    elif failed_results:
        job_result["status"] = "completed_with_errors"

    return job_result


def register_analysis_jobs(job_service: JobService) -> None:
    """Register all analysis job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.ANALYSIS, analyze_scenes_job)
    job_service.register_handler(JobType.APPLY_PLAN, apply_analysis_plan_job)
    job_service.register_handler(JobType.GENERATE_DETAILS, generate_scene_details_job)

    logger.info("Registered all analysis job handlers")
