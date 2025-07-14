from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.job import Job, JobStatus, JobType


class JobRepository:
    """Repository for job persistence and retrieval."""
    
    async def create_job(
        self,
        job_id: str,
        job_type: JobType,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Create job record in database."""
        job = Job(
            id=job_id,
            type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            metadata=metadata or {}
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        db: Session,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        message: Optional[str] = None
    ) -> Optional[Job]:
        """Update job status and related fields."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        job.status = status
        
        if progress is not None:
            job.progress = progress
        
        if result is not None:
            job.result = result
        
        if error is not None:
            job.error = error
        
        if message is not None:
            if not job.metadata:
                job.metadata = {}
            job.metadata["last_message"] = message
        
        # Update timestamps based on status
        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()
        
        job.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(job)
        return job
    
    async def get_job(self, job_id: str, db: Session) -> Optional[Job]:
        """Get job by ID."""
        return db.query(Job).filter(Job.id == job_id).first()
    
    async def list_jobs(
        self,
        db: Session,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Job]:
        """List jobs with optional filters."""
        query = db.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        
        if job_type:
            query = query.filter(Job.type == job_type)
        
        return query.order_by(desc(Job.created_at)).offset(offset).limit(limit).all()
    
    async def cancel_job(self, job_id: str, db: Session) -> Optional[Job]:
        """Cancel a job by updating its status."""
        return await self.update_job_status(
            job_id=job_id,
            status=JobStatus.CANCELLED,
            db=db,
            message="Job cancelled by user"
        )
    
    async def get_active_jobs(
        self,
        db: Session,
        job_type: Optional[JobType] = None
    ) -> List[Job]:
        """Get all active (pending or running) jobs."""
        query = db.query(Job).filter(
            Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
        )
        
        if job_type:
            query = query.filter(Job.type == job_type)
        
        return query.order_by(Job.created_at).all()
    
    async def cleanup_old_jobs(
        self,
        db: Session,
        days: int = 30
    ) -> int:
        """Clean up completed jobs older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = db.query(Job).filter(
            Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
            Job.completed_at < cutoff_date
        ).delete()
        
        db.commit()
        return deleted_count


# Global instance
job_repository = JobRepository()