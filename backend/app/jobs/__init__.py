from app.jobs.sync_jobs import register_sync_jobs
from app.jobs.analysis_jobs import register_analysis_jobs


def register_all_jobs():
    """Register all job handlers."""
    register_sync_jobs()
    register_analysis_jobs()


__all__ = ["register_all_jobs"]