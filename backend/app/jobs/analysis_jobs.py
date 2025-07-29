import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

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
    plan_id: Optional[int] = None  # Track plan ID for cancellation handling
    try:
        logger.info(
            f"Starting analyze_scenes job {job_id} for {len(scene_ids or [])} scenes"
        )
        logger.debug(f"Scene IDs received in job: {scene_ids}")

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

        # Convert options dict to AnalysisOptions
        analysis_options = AnalysisOptions(**options) if options else AnalysisOptions()

        # Extract plan_name from kwargs if provided
        plan_name = kwargs.get("plan_name")

        # Execute analysis with progress callback
        async with AsyncSessionLocal() as db:
            if openai_client is None:
                raise ValueError("OpenAI client is required for analysis")
            analysis_service = AnalysisService(
                openai_client=openai_client,
                stash_service=stash_service,
                settings=settings,
            )

            logger.info(
                f"Creating analysis service and starting analysis for job {job_id}"
            )

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

            # Check if plan has an ID (was saved to database)
            if not hasattr(plan, "id") or plan.id is None:
                # Mock plan - no changes were found
                logger.info(
                    f"No changes found for job {job_id}, returning minimal result"
                )
                result: dict[str, Any] = {
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
                # Calculate summary while still in session
                try:
                    logger.debug(f"Plan object session: {plan in db}")
                    logger.debug(f"Current db session: {db}")

                    # The plan object is bound to a different session context
                    # We need to re-fetch it in our current session to access its relationships

                    # Store the plan ID before any potential session issues
                    plan_id = int(plan.id)  # This updates the outer scope plan_id

                    # Re-fetch the plan in our current session to avoid cross-session issues
                    plan_query = select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
                    plan_result = await db.execute(plan_query)
                    fresh_plan = plan_result.scalar_one()

                    # Now query changes directly (since it's a dynamic relationship)
                    logger.debug(f"Querying changes for plan {plan_id}")
                    changes_query = select(PlanChange).where(
                        PlanChange.plan_id == plan_id
                    )
                    changes_result = await db.execute(changes_query)
                    changes_list = list(changes_result.scalars().all())

                    logger.debug(
                        f"Loaded {len(changes_list)} changes for plan {plan_id}"
                    )

                    # Calculate summary with the loaded changes
                    summary = calculate_plan_summary(changes_list)

                    # Get total changes count and metadata while session is active
                    total_changes = len(changes_list)
                    # Use the fresh plan to access metadata safely
                    scenes_analyzed = fresh_plan.get_metadata("scene_count", 0)

                    logger.info(
                        f"Summary calculated for job {job_id}: {total_changes} total changes"
                    )

                    result = {
                        "plan_id": plan_id,  # Already an int from line 120
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

            # Commit the plan finalization changes (status update from PENDING to DRAFT/REVIEWING)
            await db.commit()

            logger.info(f"Job {job_id} completed successfully with result: {result}")
            return result

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        # If a plan was created, update its status to DRAFT before cancelling
        if plan_id is not None:
            logger.info(
                f"Setting plan {plan_id} status to DRAFT due to job cancellation"
            )
            async with AsyncSessionLocal() as cancel_db:
                # Import here to avoid circular imports
                from app.services.analysis.plan_manager import PlanManager

                plan_manager = PlanManager()

                # Get the plan and update its status
                cancelled_plan: Optional[AnalysisPlan] = await plan_manager.get_plan(
                    plan_id, cancel_db
                )
                if (
                    cancelled_plan is not None
                    and cancelled_plan.status == PlanStatus.PENDING
                ):
                    cancelled_plan.status = PlanStatus.DRAFT  # type: ignore[assignment]
                    await cancel_db.commit()
                    logger.info(f"Successfully updated plan {plan_id} status to DRAFT")

        # Re-raise to let the job service handle the cancellation
        raise

    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}", exc_info=True)
        await progress_callback(100, f"Analysis failed: {str(e)}")
        # For complete failures (initialization errors, etc.), re-raise
        raise


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


async def _trigger_incremental_sync_for_bulk(
    job_id: str, plan_ids: list[int], total_applied: int
) -> Optional[dict]:
    """Trigger incremental sync after bulk apply."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.job import JobType
        from app.services.job_service import job_service

        async with AsyncSessionLocal() as db:
            sync_job = await job_service.create_job(
                job_type=JobType.SYNC,
                db=db,
                metadata={
                    "incremental": True,
                    "triggered_by": f"bulk_apply_{job_id}",
                    "plans_applied": plan_ids[:total_applied],
                },
            )
            await db.commit()
            logger.info(f"Created incremental sync job {sync_job.id} after bulk apply")
            return None
    except Exception as sync_error:
        logger.error(
            f"Failed to trigger incremental sync after bulk apply: {str(sync_error)}",
            exc_info=True,
        )
        return {
            "error": f"Failed to trigger incremental sync: {str(sync_error)}",
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
    total_plans = len(plan_ids)
    total_applied = 0
    total_failed = 0
    total_changes_applied = 0
    all_errors = []

    # Create service instances
    analysis_service = await _create_analysis_service()

    # Process each plan
    for idx, plan_id in enumerate(plan_ids):
        if cancellation_token and cancellation_token.is_cancelled:
            logger.info(f"Bulk apply job {job_id} cancelled")
            break

        progress = int((idx / total_plans) * 90)  # Reserve last 10% for sync
        await progress_callback(
            progress,
            f"Applied {total_changes_applied} changes from {idx}/{total_plans} plans",
        )

        applied_changes, errors, exception = await _apply_single_plan_in_bulk(
            analysis_service, plan_id, job_id
        )

        if exception:
            total_failed += 1
            all_errors.append(
                {
                    "plan_id": plan_id,
                    "error": str(exception),
                    "type": "plan_application_failure",
                }
            )
        else:
            if applied_changes > 0:
                total_applied += 1
                total_changes_applied += applied_changes
            all_errors.extend(errors)

    # If any changes were applied, trigger an incremental sync
    if total_changes_applied > 0:
        logger.info(
            f"Bulk apply job {job_id} applied {total_changes_applied} changes, "
            f"triggering incremental sync"
        )
        await progress_callback(95, "Starting incremental sync...")

        sync_error = await _trigger_incremental_sync_for_bulk(
            job_id, plan_ids, total_applied
        )
        if sync_error:
            all_errors.append(sync_error)

    await progress_callback(100, "Bulk apply completed")

    return {
        "job_type": "bulk_apply",
        "total_plans": total_plans,
        "plans_applied": total_applied,
        "plans_failed": total_failed,
        "total_changes_applied": total_changes_applied,
        "errors": all_errors,
        "success_rate": ((total_applied / total_plans * 100) if total_plans > 0 else 0),
    }


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
        if result.applied_changes > 0:
            logger.info(
                f"Plan {plan_id} applied {result.applied_changes} changes, triggering incremental sync"
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
                    # Create an incremental sync job
                    sync_job = await job_service.create_job(
                        job_type=JobType.SYNC,
                        db=db,
                        metadata={
                            "incremental": True,
                            "triggered_by": f"apply_plan_{plan_id}",
                        },
                    )
                    await db.commit()
                    logger.info(
                        f"Created incremental sync job {sync_job.id} after applying plan {plan_id}"
                    )

            except Exception as sync_error:
                # Log the error but don't fail the whole job
                logger.error(
                    f"Failed to trigger incremental sync after applying plan {plan_id}: {str(sync_error)}",
                    exc_info=True,
                )
                # Add to errors but continue
                result.errors.append(
                    {
                        "error": f"Failed to trigger incremental sync: {str(sync_error)}",
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
    **kwargs: Any,
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
