import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.services.stash_service import StashService
from app.models import Job, JobStatus, Scene, Performer, Tag, Studio
from app.core.database import get_db
from .models import SyncResult, SyncStatus, SyncStats
from .strategies import SyncStrategy, FullSyncStrategy, IncrementalSyncStrategy, SmartSyncStrategy
from .scene_sync import SceneSyncHandler
from .entity_sync import EntitySyncHandler
from .progress import SyncProgress
from .conflicts import ConflictResolver

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(
        self,
        stash_service: StashService,
        db_session: Session,
        strategy: Optional[SyncStrategy] = None
    ):
        self.stash_service = stash_service
        self.db = db_session
        self.strategy = strategy or SmartSyncStrategy()
        self.scene_handler = SceneSyncHandler(stash_service, self.strategy)
        self.entity_handler = EntitySyncHandler(stash_service, self.strategy)
        self.conflict_resolver = ConflictResolver()
        self._progress: Optional[SyncProgress] = None
    
    async def sync_all(
        self,
        job_id: Optional[str] = None,
        force: bool = False,
        batch_size: int = 100,
        progress_callback: Optional[Any] = None
    ) -> SyncResult:
        """Full sync of all entities from Stash"""
        job_id = job_id or str(uuid4())
        result = SyncResult(
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Update job status if job_id provided
            await self._update_job_status(job_id, JobStatus.IN_PROGRESS, "Starting full sync")
            
            # Report initial progress
            if progress_callback:
                await progress_callback(0, "Starting full sync")
            
            # Sync entities first (performers, tags, studios)
            logger.info("Syncing entities...")
            entity_result = await self._sync_entities(force)
            result.stats.performers_processed = entity_result.get("performers", {}).get("processed", 0)
            result.stats.performers_created = entity_result.get("performers", {}).get("created", 0)
            result.stats.performers_updated = entity_result.get("performers", {}).get("updated", 0)
            
            result.stats.tags_processed = entity_result.get("tags", {}).get("processed", 0)
            result.stats.tags_created = entity_result.get("tags", {}).get("created", 0)
            result.stats.tags_updated = entity_result.get("tags", {}).get("updated", 0)
            
            result.stats.studios_processed = entity_result.get("studios", {}).get("processed", 0)
            result.stats.studios_created = entity_result.get("studios", {}).get("created", 0)
            result.stats.studios_updated = entity_result.get("studios", {}).get("updated", 0)
            
            # Report entity sync progress
            if progress_callback:
                await progress_callback(20, "Entities synced, starting scene sync")
            
            # Sync scenes
            logger.info("Syncing scenes...")
            scene_result = await self.sync_scenes(
                since=None if force else await self._get_last_sync_time("scene"),
                job_id=job_id,
                batch_size=batch_size,
                progress_callback=progress_callback
            )
            
            # Merge scene results
            result.total_items += scene_result.total_items
            result.processed_items += scene_result.processed_items
            result.created_items += scene_result.created_items
            result.updated_items += scene_result.updated_items
            result.skipped_items += scene_result.skipped_items
            result.failed_items += scene_result.failed_items
            result.errors.extend(scene_result.errors)
            
            result.stats.scenes_processed = scene_result.stats.scenes_processed
            result.stats.scenes_created = scene_result.stats.scenes_created
            result.stats.scenes_updated = scene_result.stats.scenes_updated
            result.stats.scenes_skipped = scene_result.stats.scenes_skipped
            result.stats.scenes_failed = scene_result.stats.scenes_failed
            
            result.complete()
            await self._update_job_status(
                job_id, 
                JobStatus.COMPLETED, 
                f"Sync completed. Processed {result.processed_items} items."
            )
            
        except Exception as e:
            logger.error(f"Full sync failed: {str(e)}")
            result.add_error("sync", "full", str(e))
            result.complete(SyncStatus.FAILED)
            await self._update_job_status(job_id, JobStatus.FAILED, str(e))
            raise
        
        return result
    
    async def sync_scenes(
        self,
        since: Optional[datetime] = None,
        job_id: Optional[str] = None,
        batch_size: int = 100,
        progress_callback: Optional[Any] = None,
        scene_ids: Optional[List[str]] = None,
        force: bool = False
    ) -> SyncResult:
        """Sync scenes with optional incremental mode"""
        job_id = job_id or str(uuid4())
        result = SyncResult(
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Get total scene count for progress tracking
            stats = await self.stash_service.get_stats()
            total_scenes = stats.get("scene_count", 0)
            result.total_items = total_scenes
            
            # Initialize progress tracking
            self._progress = SyncProgress(job_id, total_scenes)
            
            # Process scenes in batches
            offset = 0
            while True:
                # Fetch batch of scenes from Stash
                logger.info(f"Fetching scenes batch: offset={offset}, limit={batch_size}")
                scenes_data = await self.stash_service.find_scenes(
                    filter_dict={"updated_at": {"value": since.isoformat(), "modifier": "GREATER_THAN"}} if since else None,
                    limit=batch_size,
                    offset=offset
                )
                
                if not scenes_data or not scenes_data.get("scenes"):
                    break
                
                batch_scenes = scenes_data["scenes"]
                logger.info(f"Processing {len(batch_scenes)} scenes")
                
                # Process batch
                for scene_data in batch_scenes:
                    try:
                        await self._sync_single_scene(scene_data, result)
                        result.processed_items += 1
                        result.stats.scenes_processed += 1
                        
                        # Update progress
                        if self._progress:
                            await self._progress.update(result.processed_items)
                        
                        # Report progress via callback
                        if progress_callback and result.total_items > 0:
                            progress = int((result.processed_items / result.total_items) * 80) + 20  # 20-100%
                            await progress_callback(progress, f"Synced {result.processed_items}/{result.total_items} scenes")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync scene {scene_data.get('id')}: {str(e)}")
                        result.add_error("scene", scene_data.get("id", "unknown"), str(e))
                
                offset += batch_size
                
                # Check if we've processed all scenes
                if offset >= total_scenes or len(batch_scenes) < batch_size:
                    break
            
            result.complete()
            
            # Update last sync time
            await self._update_last_sync_time("scene")
            
            if self._progress:
                await self._progress.complete(result)
            
        except Exception as e:
            logger.error(f"Scene sync failed: {str(e)}")
            result.add_error("sync", "scenes", str(e))
            result.complete(SyncStatus.FAILED)
            raise
        
        return result
    
    async def sync_performers(
        self,
        job_id: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Any] = None
    ) -> SyncResult:
        """Sync all performers from Stash"""
        job_id = job_id or str(uuid4())
        result = SyncResult(
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Get performer stats
            stats = await self.stash_service.get_stats()
            total_performers = stats.get("performer_count", 0)
            result.total_items = total_performers
            
            if progress_callback:
                await progress_callback(0, f"Starting sync of {total_performers} performers")
            
            # Sync performers using entity handler
            entity_result = await self.entity_handler.sync_performers(
                self.db,
                force=force,
                progress_callback=lambda processed: progress_callback(
                    int((processed / total_performers) * 100) if total_performers > 0 else 0,
                    f"Synced {processed}/{total_performers} performers"
                ) if progress_callback else None
            )
            
            # Update result stats
            result.processed_items = entity_result.get("processed", 0)
            result.created_items = entity_result.get("created", 0)
            result.updated_items = entity_result.get("updated", 0)
            result.stats.performers_processed = entity_result.get("processed", 0)
            result.stats.performers_created = entity_result.get("created", 0)
            result.stats.performers_updated = entity_result.get("updated", 0)
            
            result.complete()
            
        except Exception as e:
            logger.error(f"Performer sync failed: {str(e)}")
            result.add_error("sync", "performers", str(e))
            result.complete(SyncStatus.FAILED)
            raise
        
        return result
    
    async def sync_tags(
        self,
        job_id: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Any] = None
    ) -> SyncResult:
        """Sync all tags from Stash"""
        job_id = job_id or str(uuid4())
        result = SyncResult(
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Get tag stats
            stats = await self.stash_service.get_stats()
            total_tags = stats.get("tag_count", 0)
            result.total_items = total_tags
            
            if progress_callback:
                await progress_callback(0, f"Starting sync of {total_tags} tags")
            
            # Sync tags using entity handler
            entity_result = await self.entity_handler.sync_tags(
                self.db,
                force=force,
                progress_callback=lambda processed: progress_callback(
                    int((processed / total_tags) * 100) if total_tags > 0 else 0,
                    f"Synced {processed}/{total_tags} tags"
                ) if progress_callback else None
            )
            
            # Update result stats
            result.processed_items = entity_result.get("processed", 0)
            result.created_items = entity_result.get("created", 0)
            result.updated_items = entity_result.get("updated", 0)
            result.stats.tags_processed = entity_result.get("processed", 0)
            result.stats.tags_created = entity_result.get("created", 0)
            result.stats.tags_updated = entity_result.get("updated", 0)
            
            result.complete()
            
        except Exception as e:
            logger.error(f"Tag sync failed: {str(e)}")
            result.add_error("sync", "tags", str(e))
            result.complete(SyncStatus.FAILED)
            raise
        
        return result
    
    async def sync_studios(
        self,
        job_id: Optional[str] = None,
        force: bool = False,
        progress_callback: Optional[Any] = None
    ) -> SyncResult:
        """Sync all studios from Stash"""
        job_id = job_id or str(uuid4())
        result = SyncResult(
            job_id=job_id,
            started_at=datetime.utcnow()
        )
        
        try:
            # Get studio stats
            stats = await self.stash_service.get_stats()
            total_studios = stats.get("studio_count", 0)
            result.total_items = total_studios
            
            if progress_callback:
                await progress_callback(0, f"Starting sync of {total_studios} studios")
            
            # Sync studios using entity handler
            entity_result = await self.entity_handler.sync_studios(
                self.db,
                force=force,
                progress_callback=lambda processed: progress_callback(
                    int((processed / total_studios) * 100) if total_studios > 0 else 0,
                    f"Synced {processed}/{total_studios} studios"
                ) if progress_callback else None
            )
            
            # Update result stats
            result.processed_items = entity_result.get("processed", 0)
            result.created_items = entity_result.get("created", 0)
            result.updated_items = entity_result.get("updated", 0)
            result.stats.studios_processed = entity_result.get("processed", 0)
            result.stats.studios_created = entity_result.get("created", 0)
            result.stats.studios_updated = entity_result.get("updated", 0)
            
            result.complete()
            
        except Exception as e:
            logger.error(f"Studio sync failed: {str(e)}")
            result.add_error("sync", "studios", str(e))
            result.complete(SyncStatus.FAILED)
            raise
        
        return result
    
    async def sync_scene_by_id(self, scene_id: str) -> SyncResult:
        """Sync a single scene by ID"""
        result = SyncResult(
            job_id=str(uuid4()),
            started_at=datetime.utcnow(),
            total_items=1
        )
        
        try:
            # Fetch scene from Stash
            scene_data = await self.stash_service.get_scene(scene_id)
            if not scene_data:
                raise ValueError(f"Scene {scene_id} not found in Stash")
            
            # Sync the scene
            await self._sync_single_scene(scene_data, result)
            result.processed_items = 1
            result.stats.scenes_processed = 1
            
            result.complete()
            
        except Exception as e:
            logger.error(f"Failed to sync scene {scene_id}: {str(e)}")
            result.add_error("scene", scene_id, str(e))
            result.complete(SyncStatus.FAILED)
            raise
        
        return result
    
    async def _sync_single_scene(self, scene_data: Dict[str, Any], result: SyncResult):
        """Sync a single scene with conflict resolution"""
        scene_id = scene_data.get("id")
        
        try:
            # Check if scene exists locally
            existing_scene = self.db.query(Scene).filter(Scene.stash_id == scene_id).first()
            
            # Apply sync strategy
            should_sync = await self.strategy.should_sync(scene_data, existing_scene)
            if not should_sync:
                result.skipped_items += 1
                result.stats.scenes_skipped += 1
                return
            
            # Sync the scene
            synced_scene = await self.scene_handler.sync_scene(scene_data, self.db)
            
            if existing_scene:
                result.updated_items += 1
                result.stats.scenes_updated += 1
            else:
                result.created_items += 1
                result.stats.scenes_created += 1
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise
    
    async def _sync_entities(self, force: bool = False) -> Dict[str, Any]:
        """Sync performers, tags, and studios"""
        results = {}
        
        # Sync performers
        try:
            performers_data = await self.stash_service.find_performers(limit=1000)
            results["performers"] = await self.entity_handler.sync_performers(
                performers_data.get("performers", []),
                self.db,
                force=force
            )
        except Exception as e:
            logger.error(f"Failed to sync performers: {str(e)}")
            results["performers"] = {"error": str(e)}
        
        # Sync tags
        try:
            tags_data = await self.stash_service.find_tags(limit=1000)
            results["tags"] = await self.entity_handler.sync_tags(
                tags_data.get("tags", []),
                self.db,
                force=force
            )
        except Exception as e:
            logger.error(f"Failed to sync tags: {str(e)}")
            results["tags"] = {"error": str(e)}
        
        # Sync studios
        try:
            studios_data = await self.stash_service.find_studios(limit=1000)
            results["studios"] = await self.entity_handler.sync_studios(
                studios_data.get("studios", []),
                self.db,
                force=force
            )
        except Exception as e:
            logger.error(f"Failed to sync studios: {str(e)}")
            results["studios"] = {"error": str(e)}
        
        return results
    
    async def _get_last_sync_time(self, entity_type: str) -> Optional[datetime]:
        """Get the last successful sync time for an entity type"""
        # This would query a sync history table
        # For now, return None to do full sync
        return None
    
    async def _update_last_sync_time(self, entity_type: str):
        """Update the last sync time for an entity type"""
        # This would update a sync history table
        pass
    
    async def _update_job_status(self, job_id: str, status: JobStatus, message: str):
        """Update job status in database"""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            job.message = message
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = datetime.utcnow()
            self.db.commit()