"""Diagnostic utilities for debugging analysis job issues."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import AnalysisPlan, Job, PlanChange, Scene
from app.models.job import JobType
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService

logger = logging.getLogger(__name__)


class AnalysisDiagnostics:
    """Diagnostic tools for debugging analysis job issues."""

    def __init__(self):
        self.settings = get_settings()
        self.stash_service = StashService(
            stash_url=self.settings.stash.url,
            api_key=self.settings.stash.api_key,
            timeout=self.settings.stash.timeout,
            max_retries=self.settings.stash.max_retries,
        )

    async def diagnose_job(self, job_id: str) -> Dict[str, Any]:
        """Run comprehensive diagnostics on a failed analysis job.

        Args:
            job_id: The ID of the job to diagnose

        Returns:
            Dictionary containing diagnostic information
        """
        async with AsyncSessionLocal() as db:
            # Get job details
            job_info = await self._get_job_info(job_id, db)
            if not job_info:
                return {"error": f"Job {job_id} not found"}

            diagnostics: Dict[str, Any] = {
                "job_id": job_id,
                "job_info": job_info,
                "checks": {},
            }

            # Run diagnostic checks
            diagnostics["checks"]["database_connection"] = (
                await self._check_database_connection(db)
            )
            diagnostics["checks"][
                "stash_connection"
            ] = await self._check_stash_connection()
            diagnostics["checks"][
                "openai_connection"
            ] = await self._check_openai_connection()

            # Check job-specific issues
            if job_info.get("type") == JobType.ANALYSIS.value:
                diagnostics["checks"]["scene_data"] = await self._check_scene_data(
                    job_info.get("parameters", {}).get("scene_ids", []), db
                )
                diagnostics["checks"]["plan_data"] = await self._check_plan_data(
                    job_info.get("result", {}).get("plan_id"), db
                )

            # Check for common issues
            diagnostics["checks"]["memory_usage"] = self._check_memory_usage()
            diagnostics["checks"]["disk_space"] = self._check_disk_space()

            return diagnostics

    async def _get_job_info(
        self, job_id: str, db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get job information from database."""
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                return {
                    "id": job.id,
                    "type": job.type.value if job.type else None,
                    "status": job.status.value if job.status else None,
                    "created_at": str(job.created_at),
                    "started_at": str(job.started_at) if job.started_at else None,
                    "completed_at": str(job.completed_at) if job.completed_at else None,
                    "error": job.error,
                    "parameters": job.parameters,
                    "result": job.result,
                    "progress": job.progress,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting job info: {e}")
            return None

    async def _check_database_connection(self, db: AsyncSession) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            # Simple query to test connection
            result = await db.execute(select(1))
            result.scalar()
            return {"status": "healthy", "message": "Database connection is working"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_stash_connection(self) -> Dict[str, Any]:
        """Check Stash API connection."""
        try:
            # Try to get server info
            result = await self.stash_service.health_check()
            return {
                "status": "healthy",
                "message": "Stash connection is working",
                "result": result,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_openai_connection(self) -> Dict[str, Any]:
        """Check OpenAI API connection."""
        try:
            if not self.settings.openai.api_key:
                return {
                    "status": "not_configured",
                    "message": "OpenAI API key not configured",
                }

            client = OpenAIClient(
                api_key=self.settings.openai.api_key,
                model=self.settings.openai.model,
                base_url=self.settings.openai.base_url,
            )

            # Try a simple completion using the generate_completion method
            await client.generate_completion(prompt="Test connection", temperature=0.1)
            return {"status": "healthy", "message": "OpenAI connection is working"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_scene_data(
        self, scene_ids: List[str], db: AsyncSession
    ) -> Dict[str, Any]:
        """Check scene data integrity."""
        results: Dict[str, Any] = {
            "total_scenes": len(scene_ids),
            "scenes_in_db": 0,
            "scenes_in_stash": 0,
            "missing_in_db": [],
            "missing_in_stash": [],
            "sync_issues": [],
        }

        for scene_id in scene_ids[:10]:  # Check first 10 scenes
            # Check database
            db_result = await db.execute(select(Scene).where(Scene.id == scene_id))
            db_scene = db_result.scalar_one_or_none()

            if db_scene:
                results["scenes_in_db"] = results["scenes_in_db"] + 1
            else:
                missing_in_db = results["missing_in_db"]
                if isinstance(missing_in_db, list):
                    missing_in_db.append(scene_id)

            # Check Stash
            try:
                stash_scene = await self.stash_service.get_scene(scene_id)
                if stash_scene:
                    results["scenes_in_stash"] = results["scenes_in_stash"] + 1
                else:
                    missing_in_stash = results["missing_in_stash"]
                    if isinstance(missing_in_stash, list):
                        missing_in_stash.append(scene_id)
            except Exception as e:
                sync_issues = results["sync_issues"]
                if isinstance(sync_issues, list):
                    sync_issues.append({"scene_id": scene_id, "error": str(e)})

        return results

    async def _check_plan_data(
        self, plan_id: Optional[int], db: AsyncSession
    ) -> Dict[str, Any]:
        """Check analysis plan data integrity."""
        if not plan_id:
            return {"status": "no_plan", "message": "No plan ID provided"}

        try:
            result = await db.execute(
                select(AnalysisPlan).where(AnalysisPlan.id == plan_id)
            )
            plan = result.scalar_one_or_none()

            if not plan:
                return {"status": "not_found", "message": f"Plan {plan_id} not found"}

            # Count changes using query to avoid lazy loading
            change_count = await db.scalar(
                select(func.count()).where(PlanChange.plan_id == plan_id)
            )

            return {
                "status": "found",
                "plan_id": plan.id,
                "name": plan.name,
                "plan_status": plan.status.value if plan.status else None,
                "created_at": str(plan.created_at),
                "total_changes": change_count,
                "metadata": plan.plan_metadata,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
                "health_status": "healthy" if memory.percent < 90 else "warning",
            }
        except ImportError:
            return {"health_status": "unknown", "message": "psutil not installed"}

    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space availability."""
        try:
            import psutil

            disk = psutil.disk_usage("/")
            return {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent,
                "health_status": "healthy" if disk.percent < 90 else "warning",
            }
        except ImportError:
            return {"health_status": "unknown", "message": "psutil not installed"}


async def run_diagnostics(job_id: str) -> None:
    """Run diagnostics for a specific job and print results."""
    diagnostics = AnalysisDiagnostics()
    results = await diagnostics.diagnose_job(job_id)

    print("\n=== Analysis Job Diagnostics ===")
    print(f"Job ID: {job_id}")

    if "error" in results:
        print(f"Error: {results['error']}")
        return

    # Print job info
    job_info = results.get("job_info", {})
    print(f"\nJob Status: {job_info.get('status', 'Unknown')}")
    print(f"Job Type: {job_info.get('type', 'Unknown')}")
    if job_info.get("error"):
        print(f"Job Error: {job_info['error']}")

    # Print check results
    print("\n--- System Checks ---")
    for check_name, check_result in results.get("checks", {}).items():
        print(f"\n{check_name}:")
        if isinstance(check_result, dict):
            for key, value in check_result.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {check_result}")


# Allow running as a script
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.utils.analysis_diagnostics <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]
    asyncio.run(run_diagnostics(job_id))
