"""
Schedule management endpoints.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_job_service
from app.models import Job, ScheduledTask
from app.models.job import JobType
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter()

# Create a separate router for /schedule-runs endpoint
schedule_runs_router = APIRouter()


@router.get("", response_model=Dict[str, Any])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all schedules."""
    try:
        result = await db.execute(select(ScheduledTask).order_by(ScheduledTask.name))
        schedules = result.scalars().all()

        return {"schedules": [schedule.to_dict() for schedule in schedules]}
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedules",
        )


@router.post("", response_model=Dict[str, Any])
async def create_schedule(
    schedule_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new schedule."""
    try:
        # Validate cron expression
        try:
            croniter(schedule_data["schedule"])
        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}",
            )

        # Create scheduled task
        schedule = ScheduledTask(
            name=schedule_data["name"],
            task_type=schedule_data["task_type"],
            schedule=schedule_data["schedule"],
            config=schedule_data.get("config", {}),
            enabled=schedule_data.get("enabled", True),
        )

        # Calculate next run
        schedule.update_next_run()

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        return schedule.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule",
        )


def _validate_cron_expression(cron_expr: str) -> None:
    """Validate a cron expression."""
    try:
        croniter(cron_expr)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {str(e)}",
        )


def _update_schedule_fields(
    schedule: ScheduledTask, update_data: Dict[str, Any]
) -> None:
    """Update schedule fields from update data."""
    for field, value in update_data.items():
        if hasattr(schedule, field):
            setattr(schedule, field, value)


def _update_next_run(schedule: ScheduledTask, update_data: Dict[str, Any]) -> None:
    """Update next run time based on schedule changes."""
    if "schedule" not in update_data and "enabled" not in update_data:
        return

    if schedule.enabled:
        schedule.update_next_run()
    else:
        schedule.next_run = None  # type: ignore[assignment]


@router.put("/{schedule_id}", response_model=Dict[str, Any])
async def update_schedule(
    schedule_id: int,
    update_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update an existing schedule."""
    try:
        # Get schedule
        result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
            )

        # Validate cron expression if provided
        if "schedule" in update_data:
            _validate_cron_expression(update_data["schedule"])

        # Update fields
        _update_schedule_fields(schedule, update_data)

        # Recalculate next run if needed
        _update_next_run(schedule, update_data)

        await db.commit()
        await db.refresh(schedule)

        return schedule.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule",
        )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a schedule."""
    try:
        # Get schedule
        result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
            )

        await db.delete(schedule)
        await db.commit()

        return {"message": "Schedule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule",
        )


@router.post("/{schedule_id}/run", response_model=Dict[str, Any])
async def run_schedule_now(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
) -> Dict[str, Any]:
    """Manually trigger a scheduled task."""
    try:
        # Get schedule
        result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
            )

        # Create job based on task type
        job_params = dict(schedule.config) if schedule.config else {}
        job_params["scheduled_task_id"] = schedule.id

        # Convert task_type string to JobType enum
        job_type = JobType(schedule.task_type)

        job = await job_service.create_job(
            job_type=job_type,
            db=db,
            metadata=job_params,
        )

        # Update schedule's last job reference
        schedule.last_job_id = job.id
        await db.commit()

        return {"job_id": job.id, "message": "Schedule triggered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run schedule {schedule_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger schedule",
        )


@router.get("/{schedule_id}/runs", response_model=Dict[str, Any])
async def get_schedule_runs(
    schedule_id: int,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get run history for a specific schedule."""
    try:
        # Get schedule
        schedule_result = await db.execute(
            select(ScheduledTask).where(ScheduledTask.id == schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
            )

        # Get jobs for this schedule
        jobs_result = await db.execute(
            select(Job)
            .where(Job.params.contains({"scheduled_task_id": schedule_id}))
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        jobs = jobs_result.scalars().all()

        # Convert to run format
        runs = []
        for job in jobs:
            run = {
                "id": job.id,
                "schedule_id": schedule_id,
                "started_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
                "status": _map_job_status_to_run_status(
                    cast(
                        str,
                        (
                            job.status.value
                            if hasattr(job.status, "value")
                            else job.status
                        ),
                    )
                ),
                "job_id": job.id,
                "result": job.result,
                "error": job.error,
                "duration": _calculate_duration(
                    cast(Optional[datetime], job.created_at),
                    cast(Optional[datetime], job.completed_at),
                ),
            }
            runs.append(run)

        # Calculate stats
        stats = _calculate_schedule_stats(runs)

        return {"runs": runs, "stats": stats}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get runs for schedule {schedule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule runs",
        )


@schedule_runs_router.get("", response_model=Dict[str, Any])
async def get_all_schedule_runs(
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get run history for all schedules."""
    try:
        # Get jobs that were created by scheduled tasks
        result = await db.execute(
            select(Job)
            .where(Job.initiated_by == "scheduled")
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        jobs = result.scalars().all()

        # Convert to run format
        runs = []
        for job in jobs:
            schedule_id = job.params.get("scheduled_task_id") if job.params else None
            run = {
                "id": job.id,
                "schedule_id": schedule_id,
                "started_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
                "status": _map_job_status_to_run_status(
                    cast(
                        str,
                        (
                            job.status.value
                            if hasattr(job.status, "value")
                            else job.status
                        ),
                    )
                ),
                "job_id": job.id,
                "result": job.result,
                "error": job.error,
                "duration": _calculate_duration(
                    cast(Optional[datetime], job.created_at),
                    cast(Optional[datetime], job.completed_at),
                ),
            }
            runs.append(run)

        # Calculate overall stats
        stats = _calculate_schedule_stats(runs)

        return {"runs": runs, "stats": stats}

    except Exception as e:
        logger.error(f"Failed to get all schedule runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule runs",
        )


@router.post("/preview", response_model=Dict[str, Any])
async def preview_schedule(
    preview_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Preview next run times for a cron expression."""
    try:
        expression = preview_data.get("expression", "")
        count = preview_data.get("count", 5)

        if not expression:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Expression is required"
            )

        # Validate and calculate next runs
        try:
            cron = croniter(expression, datetime.utcnow())
            next_runs = []
            for _ in range(count):
                next_run = cron.get_next(datetime)
                next_runs.append(next_run.isoformat())
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}",
            )

        return {"next_runs": next_runs}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview schedule",
        )


def _map_job_status_to_run_status(job_status: str) -> str:
    """Map Job status to ScheduleRun status."""
    mapping = {
        "pending": "running",
        "running": "running",
        "completed": "success",
        "failed": "failed",
        "cancelled": "cancelled",
    }
    return mapping.get(job_status, "failed")


def _calculate_duration(
    start: Optional[datetime], end: Optional[datetime]
) -> Optional[float]:
    """Calculate duration in seconds between two timestamps."""
    if start and end:
        return (end - start).total_seconds()
    return None


def _calculate_schedule_stats(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics for schedule runs."""
    total_runs = len(runs)
    successful_runs = sum(1 for run in runs if run["status"] == "success")
    failed_runs = sum(1 for run in runs if run["status"] == "failed")

    durations = [run["duration"] for run in runs if run["duration"] is not None]
    average_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "average_duration": average_duration,
        "last_run": runs[0] if runs else None,
    }


__all__ = ["router", "schedule_runs_router"]
