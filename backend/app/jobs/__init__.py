from app.jobs.analysis_jobs import register_analysis_jobs
from app.jobs.sync_jobs import register_sync_jobs
from app.services.job_service import JobService


def register_all_jobs(job_service: JobService) -> None:
    """Register all job handlers.

    Args:
        job_service: The job service instance to register handlers with
    """
    register_sync_jobs(job_service)
    register_analysis_jobs(job_service)


__all__ = ["register_all_jobs"]
