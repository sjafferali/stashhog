"""
Service for centralized dashboard status checks.

This service consolidates all on-demand checks that run when the dashboard is loaded,
making it easier to add new checks and maintain consistency.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.models import AnalysisPlan, Performer, Scene, Studio, Tag
from app.models.analysis_plan import PlanStatus
from app.models.job import Job, JobStatus
from app.models.job import JobType as ModelJobType
from app.services.download_check_service import download_check_service
from app.services.job_service import JobService
from app.services.stash_service import StashService
from app.services.sync_status_service import SyncStatusService

logger = logging.getLogger(__name__)


class DashboardStatusService:
    """Service for performing all dashboard status checks."""

    def __init__(self, stash_service: StashService, job_service: JobService):
        self.stash_service = stash_service
        self.job_service = job_service
        self.sync_status_service = SyncStatusService(stash_service)

    async def get_all_status_data(self, db: AsyncDBSession) -> Dict[str, Any]:
        """
        Get all dashboard status data in one consolidated call.

        This includes:
        - Basic entity counts
        - Sync status and pending items
        - Analysis status
        - Organization status
        - Metadata quality metrics
        - Job status
        - Actionable items

        Args:
            db: Database session

        Returns:
            Comprehensive status data dictionary
        """
        # Get all basic metrics
        basic_metrics = await self._get_basic_metrics(db)
        sync_status = await self._get_sync_status(db)
        analysis_status = await self._get_analysis_status(db)
        organization_status = await self._get_organization_status(db)
        metadata_status = await self._get_metadata_status(db)
        job_status = await self._get_job_status(db)

        # Get pending downloads
        pending_downloads = await download_check_service.get_pending_downloads_count()

        # Generate actionable items based on all collected data
        actionable_items = self._generate_actionable_items(
            sync_status=sync_status,
            analysis_status=analysis_status,
            pending_downloads=pending_downloads,
            metadata_status=metadata_status,
        )

        return {
            "summary": basic_metrics,
            "sync": sync_status,
            "analysis": analysis_status,
            "organization": organization_status,
            "metadata": metadata_status,
            "jobs": job_status,
            "actionable_items": actionable_items,
        }

    async def _get_basic_metrics(self, db: AsyncDBSession) -> Dict[str, int]:
        """Get basic entity counts."""
        scene_count_result = await db.execute(select(func.count(Scene.id)))
        scene_count = scene_count_result.scalar_one()

        performer_count_result = await db.execute(select(func.count(Performer.id)))
        performer_count = performer_count_result.scalar_one()

        tag_count_result = await db.execute(select(func.count(Tag.id)))
        tag_count = tag_count_result.scalar_one()

        studio_count_result = await db.execute(select(func.count(Studio.id)))
        studio_count = studio_count_result.scalar_one()

        return {
            "scene_count": scene_count,
            "performer_count": performer_count,
            "tag_count": tag_count,
            "studio_count": studio_count,
        }

    async def _get_sync_status(self, db: AsyncDBSession) -> Dict[str, Any]:
        """Get sync status including pending scenes."""
        # Use centralized sync status service
        sync_status = await self.sync_status_service.get_sync_status(db)

        # Check if sync is running
        is_syncing = await self._is_job_running(
            db, [ModelJobType.SYNC, ModelJobType.SYNC_SCENES]
        )

        # Add is_syncing to the status
        sync_status["is_syncing"] = is_syncing

        return sync_status

    async def _get_analysis_status(self, db: AsyncDBSession) -> Dict[str, Any]:
        """Get analysis status metrics."""
        # Scenes not analyzed
        not_analyzed_query = select(func.count(Scene.id)).where(
            Scene.analyzed.is_(False)
        )
        not_analyzed_result = await db.execute(not_analyzed_query)
        scenes_not_analyzed = not_analyzed_result.scalar_one()

        # Scenes not video analyzed
        not_video_analyzed_query = select(func.count(Scene.id)).where(
            Scene.video_analyzed.is_(False)
        )
        not_video_analyzed_result = await db.execute(not_video_analyzed_query)
        scenes_not_video_analyzed = not_video_analyzed_result.scalar_one()

        # Analysis plans by status
        draft_plans_query = select(func.count(AnalysisPlan.id)).where(
            AnalysisPlan.status == PlanStatus.DRAFT
        )
        draft_plans_result = await db.execute(draft_plans_query)
        draft_plans = draft_plans_result.scalar_one()

        reviewing_plans_query = select(func.count(AnalysisPlan.id)).where(
            AnalysisPlan.status == PlanStatus.REVIEWING
        )
        reviewing_plans_result = await db.execute(reviewing_plans_query)
        reviewing_plans = reviewing_plans_result.scalar_one()

        # Check if analysis job is running
        is_analyzing = await self._is_job_running(db, [ModelJobType.ANALYSIS])

        return {
            "scenes_not_analyzed": scenes_not_analyzed,
            "scenes_not_video_analyzed": scenes_not_video_analyzed,
            "draft_plans": draft_plans,
            "reviewing_plans": reviewing_plans,
            "is_analyzing": is_analyzing,
        }

    async def _get_organization_status(self, db: AsyncDBSession) -> Dict[str, int]:
        """Get organization status metrics."""
        unorganized_query = select(func.count(Scene.id)).where(
            Scene.organized.is_(False)
        )
        unorganized_result = await db.execute(unorganized_query)
        unorganized_scenes = unorganized_result.scalar_one()

        return {
            "unorganized_scenes": unorganized_scenes,
        }

    async def _get_metadata_status(self, db: AsyncDBSession) -> Dict[str, int]:
        """Get metadata quality metrics."""
        # Scenes without files
        scenes_without_files_query = select(func.count(Scene.id)).where(
            ~Scene.files.any()
        )
        scenes_without_files_result = await db.execute(scenes_without_files_query)
        scenes_without_files = scenes_without_files_result.scalar_one()

        # Scenes missing key metadata
        scenes_missing_details_query = select(func.count(Scene.id)).where(
            or_(Scene.details.is_(None), Scene.details == "")
        )
        scenes_missing_details_result = await db.execute(scenes_missing_details_query)
        scenes_missing_details = scenes_missing_details_result.scalar_one()

        # Scenes without studio
        scenes_without_studio_query = select(func.count(Scene.id)).where(
            Scene.studio_id.is_(None)
        )
        scenes_without_studio_result = await db.execute(scenes_without_studio_query)
        scenes_without_studio = scenes_without_studio_result.scalar_one()

        # Scenes without performers
        scenes_without_performers_query = select(func.count(Scene.id)).where(
            ~Scene.performers.any()
        )
        scenes_without_performers_result = await db.execute(
            scenes_without_performers_query
        )
        scenes_without_performers = scenes_without_performers_result.scalar_one()

        # Scenes without tags
        scenes_without_tags_query = select(func.count(Scene.id)).where(
            ~Scene.tags.any()
        )
        scenes_without_tags_result = await db.execute(scenes_without_tags_query)
        scenes_without_tags = scenes_without_tags_result.scalar_one()

        return {
            "scenes_without_files": scenes_without_files,
            "scenes_missing_details": scenes_missing_details,
            "scenes_without_studio": scenes_without_studio,
            "scenes_without_performers": scenes_without_performers,
            "scenes_without_tags": scenes_without_tags,
        }

    async def _get_job_status(self, db: AsyncDBSession) -> Dict[str, Any]:
        """Get job status metrics."""
        # Get running jobs from job service (active jobs)
        all_running_jobs = await self.job_service.get_active_jobs(db)
        # Sort by created_at desc and limit to 5
        running_jobs = sorted(
            all_running_jobs,
            key=lambda j: j.created_at if j.created_at else datetime.min,  # type: ignore[arg-type,return-value]
            reverse=True,
        )[:5]

        # Get recently completed jobs
        completed_jobs_query = (
            select(Job)
            .where(
                Job.status.in_(
                    [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
                )
            )
            .order_by(Job.completed_at.desc().nullslast(), Job.updated_at.desc())
            .limit(10)
        )
        completed_result = await db.execute(completed_jobs_query)
        completed_jobs = completed_result.scalars().all()

        # Failed jobs in last 24 hours
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        failed_jobs_query = select(func.count(Job.id)).where(
            Job.status == JobStatus.FAILED, Job.completed_at >= twenty_four_hours_ago
        )
        failed_jobs_result = await db.execute(failed_jobs_query)
        recent_failed_jobs = failed_jobs_result.scalar_one()

        return {
            "recent_failed_jobs": recent_failed_jobs,
            "running_jobs": [self._format_job(job) for job in running_jobs],
            "completed_jobs": [self._format_job(job) for job in completed_jobs],
        }

    async def _is_job_running(
        self, db: AsyncDBSession, job_types: List[ModelJobType]
    ) -> bool:
        """Check if any jobs of the given types are running."""
        # Get active jobs from job service instead of direct DB query
        active_jobs = await self.job_service.get_active_jobs(db)

        # Check if any active job matches the requested types
        for job in active_jobs:
            job_type_value = job.type.value if hasattr(job.type, "value") else job.type
            if job_type_value in [jt.value for jt in job_types]:
                return True
        return False

    def _format_job(self, job: Job) -> Dict[str, Any]:
        """Format a job for API response."""
        return {
            "id": str(job.id),
            "type": job.type.value if hasattr(job.type, "value") else str(job.type),
            "status": (
                job.status.value if hasattr(job.status, "value") else str(job.status)
            ),
            "progress": job.progress,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
            "result": job.result if isinstance(job.result, dict) else {},
            "metadata": (
                job.job_metadata
                if hasattr(job, "job_metadata") and isinstance(job.job_metadata, dict)
                else {}
            ),
        }

    def _generate_actionable_items(
        self,
        sync_status: Dict[str, Any],
        analysis_status: Dict[str, Any],
        pending_downloads: int,
        metadata_status: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Generate actionable items based on status data."""
        items = []

        # Pending sync
        pending_scenes = sync_status.get("pending_scenes", 0)
        if pending_scenes > 0:
            items.append(
                {
                    "id": "pending_sync",
                    "type": "sync",
                    "title": "Pending Sync",
                    "description": f"{pending_scenes} scenes have been updated in Stash since last sync",
                    "count": pending_scenes,
                    "action": "sync_scenes",
                    "action_label": "Run Incremental Sync",
                    "priority": "high" if pending_scenes > 10 else "medium",
                    "visible": True,
                }
            )

        # Draft plans
        draft_plans = analysis_status.get("draft_plans", 0)
        if draft_plans > 0:
            items.append(
                {
                    "id": "draft_plans",
                    "type": "analysis",
                    "title": "Draft Plans",
                    "description": f"{draft_plans} analysis plans are in draft status",
                    "count": draft_plans,
                    "action": "view_plans",
                    "action_label": "Review Plans",
                    "route": "/analysis/plans?status=draft",
                    "priority": "medium",
                    "visible": True,
                }
            )

        # Reviewing plans
        reviewing_plans = analysis_status.get("reviewing_plans", 0)
        if reviewing_plans > 0:
            items.append(
                {
                    "id": "reviewing_plans",
                    "type": "analysis",
                    "title": "Plans Under Review",
                    "description": f"{reviewing_plans} analysis plans are being reviewed",
                    "count": reviewing_plans,
                    "action": "view_plans",
                    "action_label": "Continue Review",
                    "route": "/analysis/plans?status=reviewing",
                    "priority": "high",
                    "visible": True,
                }
            )

        # Scenes not analyzed
        scenes_not_analyzed = analysis_status.get("scenes_not_analyzed", 0)
        if scenes_not_analyzed > 0:
            items.append(
                {
                    "id": "scenes_not_analyzed",
                    "type": "analysis",
                    "title": "Scenes Pending Analysis",
                    "description": f"{scenes_not_analyzed} scenes have not been analyzed yet",
                    "count": scenes_not_analyzed,
                    "action": "view_scenes",
                    "action_label": "View Scenes",
                    "route": "/scenes?analyzed=false",
                    "priority": "medium",
                    "visible": True,
                }
            )

        # Scenes not video analyzed
        scenes_not_video_analyzed = analysis_status.get("scenes_not_video_analyzed", 0)
        if scenes_not_video_analyzed > 0:
            items.append(
                {
                    "id": "scenes_not_video_analyzed",
                    "type": "analysis",
                    "title": "Scenes Pending Video Analysis",
                    "description": f"{scenes_not_video_analyzed} scenes have not been video analyzed",
                    "count": scenes_not_video_analyzed,
                    "action": "view_scenes",
                    "action_label": "View Scenes",
                    "route": "/scenes?video_analyzed=false",
                    "priority": "low",
                    "visible": True,
                }
            )

        # Scenes without files
        scenes_without_files = metadata_status.get("scenes_without_files", 0)
        if scenes_without_files > 0:
            items.append(
                {
                    "id": "scenes_without_files",
                    "type": "sync",
                    "title": "Scenes Without Files",
                    "description": f"{scenes_without_files} scenes have no associated files",
                    "count": scenes_without_files,
                    "action": "view_scenes",
                    "action_label": "View Broken Scenes",
                    "route": "/scenes?has_files=false",
                    "priority": "high",
                    "visible": True,
                }
            )

        # Pending downloads
        if pending_downloads > 0:
            items.append(
                {
                    "id": "pending_downloads",
                    "type": "sync",
                    "title": "Downloads to Process",
                    "description": f"{pending_downloads} completed torrents need to be processed",
                    "count": pending_downloads,
                    "action": "process_downloads",
                    "action_label": "Process Downloads",
                    "priority": "high" if pending_downloads > 5 else "medium",
                    "visible": True,
                }
            )

        return items
