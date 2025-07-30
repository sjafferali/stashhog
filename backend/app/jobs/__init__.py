from app.jobs.analysis_jobs import register_analysis_jobs
from app.jobs.check_stash_generate_job import register_check_stash_generate_jobs
from app.jobs.cleanup_jobs import register_cleanup_jobs
from app.jobs.download_jobs import register_download_jobs
from app.jobs.process_new_scenes_job import register_process_new_scenes_job
from app.jobs.stash_generate_jobs import register_stash_generate_jobs
from app.jobs.stash_scan_jobs import register_stash_scan_jobs
from app.jobs.sync_jobs import register_sync_jobs
from app.services.job_service import JobService


def register_all_jobs(job_service: JobService) -> None:
    """Register all job handlers.

    Args:
        job_service: The job service instance to register handlers with
    """
    register_sync_jobs(job_service)
    register_analysis_jobs(job_service)
    register_cleanup_jobs(job_service)
    register_download_jobs(job_service)
    register_stash_scan_jobs(job_service)
    register_stash_generate_jobs(job_service)
    register_check_stash_generate_jobs(job_service)
    register_process_new_scenes_job(job_service)


__all__ = ["register_all_jobs"]
