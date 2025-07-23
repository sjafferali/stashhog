import logging
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.settings_loader import load_settings_with_db_overrides
from app.models import AnalysisPlan, PlanChange
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
                    plan_id = plan.id

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
                        "plan_id": int(plan_id),
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

    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}", exc_info=True)
        await progress_callback(100, f"Analysis failed: {str(e)}")
        # For complete failures (initialization errors, etc.), re-raise
        raise


async def apply_analysis_plan_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], Awaitable[None]],
    plan_id: str,
    cancellation_token: Optional[Any] = None,
    auto_approve: bool = False,
    change_ids: Optional[list[int]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Apply an analysis plan as a background job."""
    try:
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
