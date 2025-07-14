"""
Sync management endpoints.
"""
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    JobResponse,
    SuccessResponse,
    JobType as APIJobType,
    JobStatus as APIJobStatus,
    SyncResultResponse,
    SyncStatsResponse
)
from app.core.dependencies import get_db, get_stash_service, get_sync_service
from app.core.exceptions import NotFoundError
from app.services.stash_service import StashService
from app.services.sync import SyncService, SyncResult
from app.services.websocket_manager import websocket_manager
from app.services.job_service import job_service
from app.models import Job, SyncHistory
from app.models.job import JobType, JobStatus
from app.core.tasks import task_queue

router = APIRouter()


@router.post("/all", response_model=JobResponse)
async def sync_all(
    force: bool = Query(False, description="Force full sync ignoring timestamps"),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    Trigger full sync of all entities from Stash.
    
    This creates a background job to sync performers, tags, studios, and scenes.
    
    Args:
        force: Force full sync ignoring timestamps
        db: Database session
        
    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=JobType.SYNC,
        db=db,
        metadata={"force": force},
        force=force
    )
    
    return JobResponse(
        id=job.id,
        type=APIJobType(job.type.value),
        status=APIJobStatus(job.status.value),
        progress=job.progress,
        parameters=job.metadata or {},
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None
    )


@router.post("/scenes", response_model=JobResponse)
async def sync_scenes(
    scene_ids: Optional[List[str]] = None,
    force: bool = Query(False, description="Force sync even if unchanged"),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    Sync scenes from Stash.
    
    Args:
        scene_ids: Specific scene IDs to sync (if not provided, syncs all)
        force: Force sync even if scenes are unchanged
        db: Database session
        
    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=JobType.SYNC_SCENES,
        db=db,
        metadata={"scene_ids": scene_ids, "force": force},
        scene_ids=scene_ids,
        force=force
    )
    
    return JobResponse(
        id=job.id,
        type=APIJobType(job.type.value),
        status=APIJobStatus(job.status.value),
        progress=job.progress,
        parameters=job.metadata or {},
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None
    )


@router.post("/performers", response_model=JobResponse)
async def sync_performers(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    Sync performers from Stash.
    
    Args:
        force: Force sync ignoring timestamps
        db: Database session
        
    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=JobType.SYNC_PERFORMERS,
        db=db,
        metadata={"force": force},
        force=force
    )
    
    return JobResponse(
        id=job.id,
        type=APIJobType(job.type.value),
        status=APIJobStatus(job.status.value),
        progress=job.progress,
        parameters=job.metadata or {},
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None
    )


@router.post("/tags", response_model=JobResponse)
async def sync_tags(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    Sync tags from Stash.
    
    Args:
        force: Force sync ignoring timestamps
        db: Database session
        
    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=JobType.SYNC_TAGS,
        db=db,
        metadata={"force": force},
        force=force
    )
    
    return JobResponse(
        id=job.id,
        type=APIJobType(job.type.value),
        status=APIJobStatus(job.status.value),
        progress=job.progress,
        parameters=job.metadata or {},
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None
    )


@router.post("/studios", response_model=JobResponse)
async def sync_studios(
    force: bool = Query(False, description="Force sync ignoring timestamps"),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    Sync studios from Stash.
    
    Args:
        force: Force sync ignoring timestamps
        db: Database session
        
    Returns:
        Job information
    """
    # Create job via job service
    job = await job_service.create_job(
        job_type=JobType.SYNC_STUDIOS,
        db=db,
        metadata={"force": force},
        force=force
    )
    
    return JobResponse(
        id=job.id,
        type=APIJobType(job.type.value),
        status=APIJobStatus(job.status.value),
        progress=job.progress,
        parameters=job.metadata or {},
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None
    )


@router.post("/scene/{scene_id}", response_model=SyncResultResponse)
async def sync_single_scene(
    scene_id: str,
    db: Session = Depends(get_db),
    sync_service: SyncService = Depends(get_sync_service)
) -> SyncResultResponse:
    """
    Sync a single scene by ID.
    
    This is a synchronous operation that immediately syncs the scene.
    
    Args:
        scene_id: Scene ID to sync
        db: Database session
        sync_service: Sync service instance
        
    Returns:
        Sync result
    """
    result = await sync_service.sync_scene_by_id(scene_id)
    
    return SyncResultResponse(
        job_id=result.job_id,
        status=result.status,
        total_items=result.total_items,
        processed_items=result.processed_items,
        created_items=result.created_items,
        updated_items=result.updated_items,
        skipped_items=result.skipped_items,
        failed_items=result.failed_items,
        started_at=result.started_at.isoformat() if result.started_at else None,
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        duration_seconds=result.duration_seconds,
        errors=[{"entity": e.entity_type, "id": e.entity_id, "message": e.message} for e in result.errors]
    )


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    db: Session = Depends(get_db)
) -> SyncStatsResponse:
    """
    Get sync statistics.
    
    Returns counts and last sync times for each entity type.
    
    Args:
        db: Database session
        
    Returns:
        Sync statistics
    """
    # Get last sync times for each entity type
    last_syncs = {}
    for entity_type in ["scene", "performer", "tag", "studio"]:
        last_sync = db.query(SyncHistory).filter(
            SyncHistory.entity_type == entity_type,
            SyncHistory.status == "completed"
        ).order_by(SyncHistory.completed_at.desc()).first()
        
        if last_sync:
            last_syncs[entity_type] = last_sync.completed_at.isoformat()
    
    # Get counts from database
    from app.models import Scene, Performer, Tag, Studio
    
    scene_count = db.query(Scene).count()
    performer_count = db.query(Performer).count()
    tag_count = db.query(Tag).count()
    studio_count = db.query(Studio).count()
    
    # Get pending sync counts (simplified)
    # In a real implementation, this would check which items need syncing
    pending_scenes = 0
    pending_performers = 0
    pending_tags = 0
    pending_studios = 0
    
    return SyncStatsResponse(
        scene_count=scene_count,
        performer_count=performer_count,
        tag_count=tag_count,
        studio_count=studio_count,
        last_scene_sync=last_syncs.get("scene"),
        last_performer_sync=last_syncs.get("performer"),
        last_tag_sync=last_syncs.get("tag"),
        last_studio_sync=last_syncs.get("studio"),
        pending_scenes=pending_scenes,
        pending_performers=pending_performers,
        pending_tags=pending_tags,
        pending_studios=pending_studios
    )


