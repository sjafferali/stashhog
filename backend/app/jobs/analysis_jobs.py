import logging
from typing import Any, Awaitable, Callable, Dict, Optional

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

            logger.info(f"Analysis completed for job {job_id}, plan ID: {plan.id}")

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
                changes_query = select(PlanChange).where(PlanChange.plan_id == plan_id)
                changes_result = await db.execute(changes_query)
                changes_list = list(changes_result.scalars().all())

                logger.debug(f"Loaded {len(changes_list)} changes for plan {plan_id}")

                # Calculate summary with the loaded changes
                summary = calculate_plan_summary(changes_list)

                # Get total changes count and metadata while session is active
                total_changes = len(changes_list)
                # Use the fresh plan to access metadata safely
                scenes_analyzed = fresh_plan.get_metadata("scene_count", 0)

                logger.info(
                    f"Summary calculated for job {job_id}: {total_changes} total changes"
                )

            except Exception as e:
                logger.error(
                    f"Error calculating summary for job {job_id}: {str(e)}",
                    exc_info=True,
                )
                raise

            result = {
                "plan_id": plan_id,
                "total_changes": total_changes,
                "scenes_analyzed": scenes_analyzed,
                "summary": summary,
            }

            logger.info(f"Job {job_id} completed successfully with result: {result}")
            return result

    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}", exc_info=True)
        await progress_callback(100, f"Analysis failed: {str(e)}")
        raise


async def apply_analysis_plan_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    plan_id: str,
    cancellation_token: Optional[Any] = None,
    auto_approve: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Apply an analysis plan as a background job."""
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
    async with AsyncSessionLocal():
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
        )

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
    }


async def analyze_all_unanalyzed_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
    options: Optional[dict[str, Any]] = None,
    batch_size: int = 100,
    **kwargs: Any,
) -> dict[str, Any]:
    """Analyze all unanalyzed scenes as a background job."""
    logger.info(f"Starting analyze_all_unanalyzed job {job_id}")

    # Convert options dict to AnalysisOptions
    analysis_options = AnalysisOptions(**options) if options else AnalysisOptions()

    # Get unanalyzed scenes
    from app.core.database import AsyncSessionLocal
    from app.repositories.scene_repository import scene_repository

    async with AsyncSessionLocal() as db:
        unanalyzed_scenes = await scene_repository.get_unanalyzed_scenes(db)
        scene_ids: list[str] = [str(scene.id) for scene in unanalyzed_scenes]

        logger.info(f"Found {len(scene_ids)} unanalyzed scenes")

        # Execute analysis in batches
        total_scenes = len(scene_ids)
        analyzed_count = 0
        all_plans = []

        for i in range(0, total_scenes, batch_size):
            batch: list[str] = scene_ids[i : i + batch_size]
            batch_progress = int((i / total_scenes) * 100)

            progress_callback(
                batch_progress,
                f"Analyzing batch {i // batch_size + 1} of {(total_scenes + batch_size - 1) // batch_size}",
            )

            # Create service instances for this batch
            settings = await load_settings_with_db_overrides()
            stash_service = StashService(
                stash_url=settings.stash.url, api_key=settings.stash.api_key
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

            # Analyze batch
            async with AsyncSessionLocal() as batch_db:
                if openai_client is None:
                    raise ValueError("OpenAI client is required for analysis")

                analysis_service = AnalysisService(
                    openai_client=openai_client,
                    stash_service=stash_service,
                    settings=settings,
                )

                plan = await analysis_service.analyze_scenes(
                    scene_ids=batch,
                    options=analysis_options,
                    job_id=f"{job_id}_batch_{i // batch_size}",
                    db=batch_db,
                    progress_callback=lambda p, m: None,  # Don't report individual progress
                )

            all_plans.append(plan)
            analyzed_count += len(batch)

        # Summary
        total_changes = sum(plan.get_change_count() for plan in all_plans)

        return {
            "scenes_analyzed": analyzed_count,
            "total_changes": total_changes,
            "plans_created": len(all_plans),
            "plan_ids": [plan.id for plan in all_plans],
        }


async def generate_scene_details_job(
    job_id: str,
    progress_callback: Callable[[int, Optional[str]], None],
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

    for idx, scene_id in enumerate(scene_ids or []):
        progress = int((idx / total_scenes) * 100)
        progress_callback(
            progress, f"Generating details for scene {idx + 1} of {total_scenes}"
        )

        try:
            # This assumes there's a method to generate scene details
            # You may need to adapt this based on the actual AnalysisService API
            # Using analyze_single_scene since generate_scene_details doesn't exist
            scene_data = await stash_service.get_scene(scene_id)
            if scene_data:
                # Convert to Scene-like object
                class SceneLike:
                    def __init__(self, data: dict[str, Any]) -> None:
                        self.id = data.get("id")
                        self.title = data.get("title", "")
                        self.path = data.get(
                            "path", data.get("file", {}).get("path", "")
                        )
                        self.details = data.get("details", "")
                        self.duration = data.get("file", {}).get("duration", 0)
                        self.width = data.get("file", {}).get("width", 0)
                        self.height = data.get("file", {}).get("height", 0)
                        self.frame_rate = data.get("file", {}).get("frame_rate", 0)
                        self.performers = data.get("performers", [])
                        self.tags = data.get("tags", [])
                        self.studio = data.get("studio")

                scene = SceneLike(scene_data)
                from app.services.analysis.models import AnalysisOptions

                # Cast SceneLike to Scene for type checking
                changes = await analysis_service.analyze_single_scene(
                    scene,  # type: ignore[arg-type]
                    AnalysisOptions(detect_details=True),
                )
                details_changes = [c for c in changes if c.field == "details"]
                details = details_changes[0].proposed_value if details_changes else None
            else:
                details = None
            results.append(
                {"scene_id": scene_id, "status": "success", "details": details}
            )
        except Exception as e:
            logger.error(f"Failed to generate details for scene {scene_id}: {str(e)}")
            results.append({"scene_id": scene_id, "status": "failed", "error": str(e)})

    progress_callback(100, "Scene details generation completed")

    success_count = sum(1 for r in results if r["status"] == "success")
    return {
        "total_scenes": total_scenes,
        "successful": success_count,
        "failed": total_scenes - success_count,
        "results": results,
    }


async def analyze_video_tags_job(
    job_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[float, str], Awaitable[None]]] = None,
    cancellation_token: Optional[Any] = None,
) -> Dict[str, Any]:
    """Job handler for analyzing video tags on scenes.

    Args:
        job_id: The job ID
        metadata: Job metadata containing scene_ids and filters
        progress_callback: Callback for progress updates

    Returns:
        Job result dictionary
    """
    from app.core.settings_loader import load_settings_with_db_overrides

    if not metadata:
        raise ValueError("No metadata provided for video tag analysis job")

    # Extract parameters from metadata
    job_params = metadata.get("job_params", {})
    scene_ids = job_params.get("scene_ids", [])
    filters = job_params.get("filters")

    # Get services with database overrides
    settings = await load_settings_with_db_overrides()

    # Create OpenAI client if configured
    openai_client = None
    if settings.openai.api_key:
        from app.services.openai_client import OpenAIClient

        openai_client = OpenAIClient(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            base_url=getattr(settings.openai, "base_url", None),
            max_tokens=settings.openai.max_tokens,
            temperature=settings.openai.temperature,
            timeout=settings.openai.timeout,
        )

    # Create Stash service
    from app.services.stash_service import StashService

    stash_service = StashService(
        stash_url=settings.stash.url,
        api_key=settings.stash.api_key,
        timeout=settings.stash.timeout,
        max_retries=settings.stash.max_retries,
    )

    # For video tag analysis, we don't need OpenAI client, but AnalysisService requires it
    # Create a dummy client if not configured
    if openai_client is None:
        raise ValueError("OpenAI API key is required for video tag analysis")

    # Create analysis service
    from app.services.analysis.analysis_service import AnalysisService

    analysis_service = AnalysisService(
        openai_client=openai_client, stash_service=stash_service, settings=settings
    )

    # Run analysis
    result = await analysis_service.analyze_and_apply_video_tags(
        scene_ids=scene_ids,
        filters=filters,
        job_id=job_id,
        progress_callback=progress_callback,
        cancellation_token=cancellation_token,
    )

    return result


def register_analysis_jobs(job_service: JobService) -> None:
    """Register all analysis job handlers with the job service.

    Args:
        job_service: The job service instance to register handlers with
    """
    job_service.register_handler(JobType.ANALYSIS, analyze_scenes_job)
    job_service.register_handler(JobType.APPLY_PLAN, apply_analysis_plan_job)
    job_service.register_handler(JobType.GENERATE_DETAILS, generate_scene_details_job)
    job_service.register_handler(JobType.VIDEO_TAG_ANALYSIS, analyze_video_tags_job)

    logger.info("Registered all analysis job handlers")
