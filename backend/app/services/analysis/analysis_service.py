"""Main analysis service for scene metadata detection."""

import logging
import time
from datetime import datetime
from typing import Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.analysis_plan import AnalysisPlan
from app.models.job import JobStatus
from app.models.scene import Scene
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService
from app.services.sync.scene_sync_utils import SceneSyncUtils

from .ai_client import AIClient
from .batch_processor import BatchProcessor
from .cost_tracker import AnalysisCostTracker
from .details_generator import DetailsGenerator
from .models import (
    AnalysisOptions,
    ApplyResult,
    ProposedChange,
    SceneChanges,
)
from .performer_detector import PerformerDetector
from .plan_manager import PlanManager
from .studio_detector import StudioDetector
from .tag_detector import TagDetector
from .video_tag_detector import VideoTagDetector

logger = logging.getLogger(__name__)


class AnalysisService:
    """Main service for analyzing scenes and generating metadata suggestions."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        stash_service: StashService,
        settings: Settings,
    ):
        """Initialize analysis service.

        Args:
            openai_client: OpenAI client for AI operations
            stash_service: Stash service for data operations
            settings: Application settings
        """
        self.stash_service = stash_service
        self.settings = settings
        self.scene_sync_utils = SceneSyncUtils(stash_service)

        # Initialize AI client
        self.ai_client = AIClient(openai_client)

        # Initialize detectors
        self.studio_detector = StudioDetector()
        self.performer_detector = PerformerDetector()
        self.tag_detector = TagDetector()
        self.details_generator = DetailsGenerator()
        self.video_tag_detector = VideoTagDetector(settings=settings)

        # Initialize managers
        self.plan_manager = PlanManager()
        self.batch_processor = BatchProcessor(
            batch_size=settings.analysis.batch_size,
            max_concurrent=settings.analysis.max_concurrent,
        )

        # Cache for known entities
        self._cache: dict[str, Any] = {
            "studios": [],
            "performers": [],
            "tags": [],
            "last_refresh": None,
        }

    async def analyze_scenes(
        self,
        scene_ids: Optional[list[str]] = None,
        filters: Optional[dict] = None,
        options: Optional[AnalysisOptions] = None,
        job_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        progress_callback: Optional[Any] = None,
        plan_name: Optional[str] = None,
    ) -> AnalysisPlan:
        """Analyze scenes and generate a plan with proposed changes.

        Args:
            scene_ids: Specific scene IDs to analyze
            filters: Filters for scene selection
            options: Analysis options
            job_id: Associated job ID for progress tracking
            db: Database session for saving plan
            plan_name: Optional custom name for the plan

        Returns:
            Generated analysis plan
        """
        if options is None:
            options = AnalysisOptions()

        # Refresh cache
        await self._refresh_cache()

        # Get scenes to analyze
        logger.debug(
            f"analyze_scenes called with scene_ids: {scene_ids}, filters: {filters}"
        )

        if not db:
            raise ValueError("Database session is required for scene analysis")

        # Sync scenes from Stash to database first
        scenes = await self._sync_and_get_scenes(scene_ids, filters, db)

        if not scenes:
            return await self._create_empty_plan(db)

        logger.info(f"Starting analysis of {len(scenes)} scenes")
        logger.debug(
            f"First few scene IDs being analyzed: {[s.get('id') if isinstance(s, dict) else s.id for s in scenes[:5]]}"
        )

        # Report initial progress
        await self._report_initial_progress(job_id, len(scenes), progress_callback)

        # Initialize cost tracker
        self.cost_tracker = AnalysisCostTracker()

        # Track processing time
        start_time = time.time()

        # Process scenes in batches
        # Cast scenes to the expected type for batch processor
        scenes_for_processing: list[Union[Scene, dict[str, Any], Any]] = scenes  # type: ignore[assignment]
        all_changes = await self.batch_processor.process_scenes(
            scenes=scenes_for_processing,
            analyzer=lambda batch: self._analyze_batch(batch, options),
            progress_callback=lambda c, t, p, s: (
                self._on_progress(job_id or "", c, t, p, s, progress_callback)
                if job_id or progress_callback
                else None
            ),
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Generate plan name
        if plan_name is None:
            plan_name = self._generate_plan_name(options, len(scenes), scenes)

        # Create metadata
        metadata = self._create_analysis_metadata(options, scenes, all_changes)
        metadata["processing_time"] = round(processing_time, 2)

        # Save plan if database session provided
        if db:
            plan = await self.plan_manager.create_plan(
                name=plan_name, changes=all_changes, metadata=metadata, db=db
            )

            # Mark scenes as analyzed
            await self._mark_scenes_as_analyzed(scenes, db)

            # Update job as completed
            if job_id:
                await self._update_job_progress(
                    job_id, 100, "Analysis complete", JobStatus.COMPLETED
                )

            return plan
        else:
            # Return mock plan for dry run
            return AnalysisPlan(name=plan_name, metadata=metadata, status="draft")

    async def analyze_single_scene(
        self, scene: Scene, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Analyze a single scene and return proposed changes.

        Args:
            scene: Scene to analyze
            options: Analysis options

        Returns:
            List of proposed changes
        """
        # Convert scene to dictionary
        scene_data = self._scene_to_dict(scene)

        # Perform analysis
        changes = []

        # Track scene for cost calculation
        if hasattr(self, "cost_tracker"):
            self.cost_tracker.increment_scenes()

        # Detect studio
        if options.detect_studios:
            studio_changes = await self._detect_studio(scene_data, options)
            changes.extend(studio_changes)

        # Detect performers
        if options.detect_performers:
            performer_changes = await self._detect_performers(scene_data, options)
            changes.extend(performer_changes)

        # Detect tags
        if options.detect_tags:
            tag_changes = await self._detect_tags(scene_data, options)
            changes.extend(tag_changes)

        # Generate/enhance title (using detect_details option for now)
        if options.detect_details:
            details_changes = await self._detect_details(scene_data, options)
            changes.extend(details_changes)

        # Detect tags/markers from video content
        if options.detect_video_tags:
            video_tag_changes = await self._detect_video_tags(scene_data, options)
            changes.extend(video_tag_changes)

        return changes

    async def _analyze_batch(
        self, batch_data: list[dict], options: AnalysisOptions
    ) -> list[SceneChanges]:
        """Analyze a batch of scenes.

        Args:
            batch_data: Batch of scene data dictionaries
            options: Analysis options

        Returns:
            List of scene changes
        """
        results = []

        for scene_data in batch_data:
            try:
                # Create Scene-like object for compatibility
                class SceneLike:
                    def __init__(self, data: dict[str, Any]) -> None:
                        self.id = data.get("id", "")
                        self.title = data.get("title", "")
                        self.path = data.get("file_path", "")
                        self.details = data.get("details", "")
                        self.duration = data.get("duration", 0)
                        self.width = data.get("width", 0)
                        self.height = data.get("height", 0)
                        self.frame_rate = data.get("frame_rate", 0)
                        self.framerate = data.get(
                            "frame_rate", 0
                        )  # Add framerate alias
                        self.performers = data.get("performers", [])
                        self.tags = data.get("tags", [])
                        self.studio = data.get("studio")

                    def get_primary_path(self) -> str:
                        return str(self.path)

                scene = SceneLike(scene_data)
                # Cast to Scene type as expected by analyze_single_scene
                changes = await self.analyze_single_scene(scene, options)  # type: ignore[arg-type]

                results.append(
                    SceneChanges(
                        scene_id=scene.id,
                        scene_title=scene.title or "Untitled",
                        scene_path=scene.path,
                        changes=changes,
                    )
                )

            except Exception as e:
                logger.error(f"Error analyzing scene {scene_data.get('id')}: {e}")
                results.append(
                    SceneChanges(
                        scene_id=scene_data.get("id", "unknown"),
                        scene_title=scene_data.get("title", "Untitled"),
                        scene_path=scene_data.get("file_path", ""),
                        changes=[],
                        error=str(e),
                    )
                )

        return results

    async def _detect_studio(
        self, scene_data: dict, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Detect studio for a scene.

        Args:
            scene_data: Scene data
            options: Analysis options

        Returns:
            List of proposed changes
        """
        changes: list[ProposedChange] = []
        current_studio = scene_data.get("studio")

        # Skip if already has studio
        if current_studio:
            return changes

        # First try local detection
        result = await self.studio_detector.detect(
            scene_data=scene_data,
            known_studios=(
                self._cache["studios"]
                if isinstance(self._cache["studios"], list)
                else []
            ),
            ai_client=None,
            use_ai=False,
        )

        # If no local detection, try AI
        if not result or result.confidence < options.confidence_threshold:
            result = await self.studio_detector.detect(
                scene_data=scene_data,
                known_studios=(
                    self._cache["studios"]
                    if isinstance(self._cache["studios"], list)
                    else []
                ),
                ai_client=self.ai_client,
                use_ai=True,
            )

        if result and result.confidence >= options.confidence_threshold:
            changes.append(
                ProposedChange(
                    field="studio",
                    action="set",
                    current_value=current_studio,
                    proposed_value=result.value,
                    confidence=result.confidence,
                    reason=f"Detected from {result.source}",
                )
            )

        return changes

    async def _detect_performers(
        self, scene_data: dict, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Detect performers for a scene.

        Args:
            scene_data: Scene data
            options: Analysis options

        Returns:
            List of proposed changes
        """
        changes = []
        current_performers = scene_data.get("performers", [])
        current_names = [
            p.get("name", "") for p in current_performers if isinstance(p, dict)
        ]

        # Detect from path and title
        path_results = await self.performer_detector.detect_from_path(
            file_path=scene_data.get("file_path", ""),
            known_performers=(
                self._cache["performers"]
                if isinstance(self._cache["performers"], list)
                else []
            ),
            title=scene_data.get("title", ""),
        )

        # Always detect with AI for performers
        ai_results: List[Any] = []
        # Use tracked version if cost tracker is available
        if hasattr(self, "cost_tracker"):
            ai_results, cost_info = (
                await self.performer_detector.detect_with_ai_tracked(
                    scene_data=scene_data,
                    ai_client=self.ai_client,
                    known_performers=self._cache["performers"],
                )
            )
            if cost_info:
                self.cost_tracker.track_operation(
                    "performer_detection",
                    cost_info["cost"],
                    cost_info["usage"]["prompt_tokens"],
                    cost_info["usage"]["completion_tokens"],
                    cost_info["model"],
                )
        else:
            ai_results = await self.performer_detector.detect_with_ai(
                scene_data=scene_data,
                ai_client=self.ai_client,
                known_performers=self._cache["performers"],
            )

        # Combine and deduplicate results
        all_results: dict[str, Any] = {}
        for result in path_results + ai_results:
            if result.confidence >= options.confidence_threshold:
                name = result.value
                if name not in current_names:
                    if (
                        name not in all_results
                        or result.confidence > all_results[name].confidence
                    ):
                        all_results[name] = result

        # Create changes for new performers
        if all_results:
            new_performers = list(all_results.keys())
            changes.append(
                ProposedChange(
                    field="performers",
                    action="add",
                    current_value=current_names,
                    proposed_value=new_performers,
                    confidence=sum(r.confidence for r in all_results.values())
                    / len(all_results),
                    reason=f"Detected {len(new_performers)} new performers",
                )
            )

        return changes

    async def _detect_tags(
        self, scene_data: dict, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Detect tags for a scene.

        Args:
            scene_data: Scene data
            options: Analysis options

        Returns:
            List of proposed changes
        """
        changes = []
        current_tags = scene_data.get("tags", [])
        current_names = [t.get("name", "") for t in current_tags if isinstance(t, dict)]

        # Detect technical tags
        tech_results = self.tag_detector.detect_technical_tags(
            scene_data=scene_data, existing_tags=current_names
        )

        # Always detect with AI for tags
        ai_results: List[Any] = []
        # Use tracked version if cost tracker is available
        if hasattr(self, "cost_tracker"):
            ai_results, cost_info = await self.tag_detector.detect_with_ai_tracked(
                scene_data=scene_data,
                ai_client=self.ai_client,
                existing_tags=current_names,
                available_tags=self._cache["tags"],
            )
            if cost_info:
                self.cost_tracker.track_operation(
                    "tag_detection",
                    cost_info["cost"],
                    cost_info["usage"]["prompt_tokens"],
                    cost_info["usage"]["completion_tokens"],
                    cost_info["model"],
                )
        else:
            ai_results = await self.tag_detector.detect_with_ai(
                scene_data=scene_data,
                ai_client=self.ai_client,
                existing_tags=current_names,
                available_tags=self._cache["tags"],
            )

        # Combine results and filter to only existing tags
        all_results: dict[str, Any] = {}
        available_tags = self._cache.get("tags", [])
        available_tags_map = {t.lower(): t for t in available_tags}

        for result in tech_results + ai_results:
            if result.confidence >= options.confidence_threshold:
                tag = result.value
                tag_lower = tag.lower()
                # Only accept tags that already exist in the database
                if tag_lower in available_tags_map:
                    # Use the exact case from the database
                    actual_tag = available_tags_map[tag_lower]
                    if (
                        actual_tag not in all_results
                        or result.confidence > all_results[actual_tag].confidence
                    ):
                        # Update the result to use the correct case
                        result.value = actual_tag
                        all_results[actual_tag] = result
                else:
                    logger.debug(f"Discarding non-existent tag: {tag}")

        # Create changes for new tags
        if all_results:
            new_tags = list(all_results.keys())
            changes.append(
                ProposedChange(
                    field="tags",
                    action="add",
                    current_value=current_names,
                    proposed_value=new_tags,
                    confidence=sum(r.confidence for r in all_results.values())
                    / len(all_results),
                    reason=f"Detected {len(new_tags)} new tags",
                )
            )

        return changes

    async def _detect_details(
        self, scene_data: dict, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Clean HTML from scene details.

        Args:
            scene_data: Scene data
            options: Analysis options

        Returns:
            List of proposed changes
        """
        changes: list[ProposedChange] = []
        current_details = scene_data.get("details", "")

        if not current_details:
            return changes

        # Clean HTML from details
        cleaned_details = self.details_generator.clean_html(current_details)

        # Only propose change if the cleaned version is different
        if cleaned_details != current_details:
            changes.append(
                ProposedChange(
                    field="details",
                    action="set",
                    current_value=current_details,
                    proposed_value=cleaned_details,
                    confidence=1.0,
                    reason="Removed HTML tags from details",
                )
            )

        return changes

    async def _detect_video_tags(
        self, scene_data: dict, options: AnalysisOptions
    ) -> list[ProposedChange]:
        """Detect tags and markers from video content.

        Args:
            scene_data: Scene data
            options: Analysis options

        Returns:
            List of proposed changes
        """
        changes: list[ProposedChange] = []

        # Get current tags and markers
        current_tags = scene_data.get("tags", [])
        current_tag_names = [
            t.get("name", "") for t in current_tags if isinstance(t, dict)
        ]
        current_markers = scene_data.get("markers", [])

        try:
            # Use video tag detector
            video_changes, cost_info = await self.video_tag_detector.detect(
                scene_data=scene_data,
                existing_tags=current_tag_names,
                existing_markers=current_markers,
            )

            # Track cost if available
            if cost_info and hasattr(self, "cost_tracker"):
                self.cost_tracker.track_operation(
                    "video_tag_detection",
                    cost_info.get("total_cost", 0.0),
                    cost_info.get("prompt_tokens", 0),
                    cost_info.get("completion_tokens", 0),
                    cost_info.get("model", "video-analysis"),
                )

            # Filter changes by confidence threshold
            for change in video_changes:
                if change.confidence >= options.confidence_threshold:
                    changes.append(change)

        except Exception as e:
            logger.error(f"Error detecting video tags: {e}")
            # Don't fail the entire analysis if video detection fails

        return changes

    async def _apply_tags_to_scene(
        self,
        scene_id: str,
        scene_data: dict,
        tags_to_add: list[str],
        has_tagme: bool,
    ) -> int:
        """Apply tags to a scene and return count of tags added."""
        # Get existing tag IDs
        current_tags = scene_data.get("tags", [])
        existing_tag_ids = [t.get("id") for t in current_tags if t.get("id")]

        # Get IDs for new tags (create if needed)
        new_tag_ids = []
        for tag_name in tags_to_add:
            tag_id = await self.stash_service.find_or_create_tag(tag_name)
            if tag_id and tag_id not in existing_tag_ids:
                new_tag_ids.append(tag_id)

        if not new_tag_ids:
            return 0

        # Update scene with all tags
        all_tag_ids = existing_tag_ids + new_tag_ids

        # Remove AI_TagMe if present, add AI_Tagged
        if has_tagme:
            tagme_id = await self.stash_service.find_or_create_tag("AI_TagMe")
            if tagme_id in all_tag_ids:
                all_tag_ids.remove(tagme_id)

        # Add AI_Tagged
        tagged_id = await self.stash_service.find_or_create_tag("AI_Tagged")
        if tagged_id not in all_tag_ids:
            all_tag_ids.append(tagged_id)

        # Update scene
        await self.stash_service.update_scene(scene_id, {"tag_ids": all_tag_ids})

        return len(new_tag_ids)

    async def _apply_markers_to_scene(
        self,
        scene_id: str,
        markers_to_add: list[dict],
    ) -> int:
        """Apply markers to a scene and return count of markers added."""
        markers_added = 0

        for marker_data in markers_to_add:
            marker_tags = []
            for tag_name in marker_data.get("tags", []):
                tag_id = await self.stash_service.find_or_create_tag(tag_name)
                if tag_id:
                    marker_tags.append(tag_id)

            marker = {
                "scene_id": scene_id,
                "seconds": marker_data["seconds"],
                "title": marker_data.get("title", ""),
                "tag_ids": marker_tags,
            }

            await self.stash_service.create_marker(marker)
            markers_added += 1

        return markers_added

    async def _update_scene_status_tags(
        self,
        scene_id: str,
        current_tags: list[dict],
        has_tagme: bool,
        is_error: bool = False,
    ) -> None:
        """Update scene status tags (AI_TagMe, AI_Tagged, AI_Errored)."""
        existing_tag_ids = [t.get("id") for t in current_tags if t.get("id")]

        if is_error:
            # Add AI_Errored tag
            error_tag_id = await self.stash_service.find_or_create_tag("AI_Errored")
            if error_tag_id not in existing_tag_ids:
                existing_tag_ids.append(error_tag_id)
        else:
            # Add AI_Tagged tag
            tagged_id = await self.stash_service.find_or_create_tag("AI_Tagged")
            if tagged_id not in existing_tag_ids:
                existing_tag_ids.append(tagged_id)

        # Remove AI_TagMe if present
        if has_tagme:
            tagme_id = await self.stash_service.find_or_create_tag("AI_TagMe")
            if tagme_id in existing_tag_ids:
                existing_tag_ids.remove(tagme_id)

        await self.stash_service.update_scene(scene_id, {"tag_ids": existing_tag_ids})

    async def _extract_changes_from_video_detection(
        self, video_changes: list
    ) -> tuple[list[str], list[dict]]:
        """Extract tags and markers from video detection changes."""
        tags_to_add = []
        markers_to_add = []

        for change in video_changes:
            if change.field == "tags" and change.action == "add":
                tags_to_add.append(change.proposed_value)
            elif change.field == "markers" and change.action == "add":
                markers_to_add.append(change.proposed_value)

        return tags_to_add, markers_to_add

    async def _get_scenes_for_analysis(
        self,
        scene_ids: Optional[list[str]],
        filters: Optional[dict],
    ) -> list[dict]:
        """Get scenes for analysis based on scene IDs or filters."""
        if scene_ids:
            scenes_data = []
            for scene_id in scene_ids:
                scene = await self.stash_service.get_scene(scene_id)
                if scene:
                    scenes_data.append(scene)
            return scenes_data
        else:
            scenes, _ = await self.stash_service.get_scenes(filter=filters)
            return scenes

    async def _get_database_session(self) -> AsyncSession:
        """Get database session for analysis."""
        from app.core.database import get_async_db

        async for session in get_async_db():
            return session

        raise RuntimeError("Failed to get database session")

    def _build_empty_result(self) -> dict[str, Any]:
        """Build empty result for no scenes."""
        return {
            "status": "completed",
            "scenes_processed": 0,
            "scenes_updated": 0,
            "tags_added": 0,
            "markers_added": 0,
            "errors": [],
        }

    async def _process_scene_for_video_tags(
        self,
        scene_data: dict,
        scene_index: int,
        total_scenes: int,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Process a single scene for video tag detection.

        Returns dict with: scene_modified, tags_added, markers_added, error
        """
        scene_id = scene_data.get("id", "")
        result: dict[str, Any] = {
            "scene_modified": False,
            "tags_added": 0,
            "markers_added": 0,
            "error": None,
        }

        # Get current tags early for error handling
        current_tags = scene_data.get("tags", [])
        current_tag_names = [
            t.get("name", "") for t in current_tags if isinstance(t, dict)
        ]
        has_tagme = "AI_TagMe" in current_tag_names

        try:
            # Report progress
            if progress_callback:
                progress = int((scene_index / total_scenes) * 90)
                await progress_callback(
                    progress,
                    f"Processing scene {scene_index + 1}/{total_scenes}: {scene_data.get('title', 'Untitled')}",
                )

            # Get current markers
            current_markers = scene_data.get("markers", [])

            # Detect video tags
            video_changes, _ = await self.video_tag_detector.detect(
                scene_data=scene_data,
                existing_tags=current_tag_names,
                existing_markers=current_markers,
            )

            if video_changes:
                # Extract and apply changes
                tags_to_add, markers_to_add = (
                    await self._extract_changes_from_video_detection(video_changes)
                )

                # Apply tag changes
                if tags_to_add:
                    result["tags_added"] = await self._apply_tags_to_scene(
                        scene_id, scene_data, tags_to_add, has_tagme
                    )
                    result["scene_modified"] = True

                # Apply marker changes
                if markers_to_add:
                    result["markers_added"] = await self._apply_markers_to_scene(
                        scene_id, markers_to_add
                    )
                    result["scene_modified"] = True
            else:
                # No changes detected, just update status tags
                if has_tagme:
                    await self._update_scene_status_tags(
                        scene_id, current_tags, has_tagme, is_error=False
                    )

        except Exception as e:
            logger.error(f"Error processing scene {scene_id}: {e}")
            result["error"] = {
                "scene_id": scene_id,
                "title": scene_data.get("title", "Untitled"),
                "error": str(e),
            }

            # Try to add error tag
            try:
                await self._update_scene_status_tags(
                    scene_id, current_tags, has_tagme, is_error=True
                )
            except Exception as tag_error:
                logger.error(f"Failed to add error tag: {tag_error}")

        return result

    async def analyze_and_apply_video_tags(
        self,
        scene_ids: Optional[list[str]] = None,
        filters: Optional[dict] = None,
        job_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Analyze scenes for video tags and apply changes immediately.

        This method is specifically for video tag analysis that applies changes
        immediately rather than creating a plan.

        Args:
            scene_ids: Specific scene IDs to analyze
            filters: Filters for scene selection
            job_id: Associated job ID for progress tracking
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with results including processed scenes and applied changes
        """
        # Get database session
        db = await self._get_database_session()

        try:
            # Report initial progress
            if progress_callback:
                await progress_callback(0, "Starting video tag analysis")

            # Get scenes to analyze
            scenes_data = await self._get_scenes_for_analysis(scene_ids, filters)

            total_scenes = len(scenes_data)
            if total_scenes == 0:
                return self._build_empty_result()

            # Initialize counters
            scenes_processed = 0
            scenes_updated = 0
            tags_added = 0
            markers_added = 0
            errors = []

            # Process each scene
            for i, scene_data in enumerate(scenes_data):
                result = await self._process_scene_for_video_tags(
                    scene_data, i, total_scenes, progress_callback
                )

                # Update counters
                if result["scene_modified"]:
                    scenes_updated += 1

                tags_added += result["tags_added"]
                markers_added += result["markers_added"]

                if result["error"]:
                    errors.append(result["error"])

                scenes_processed += 1

            # Final progress
            if progress_callback:
                await progress_callback(
                    100,
                    f"Completed: {scenes_updated}/{scenes_processed} scenes updated",
                )

            return {
                "status": "completed",
                "scenes_processed": scenes_processed,
                "scenes_updated": scenes_updated,
                "tags_added": tags_added,
                "markers_added": markers_added,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Failed to analyze video tags: {str(e)}")
            if progress_callback:
                await progress_callback(100, f"Failed: {str(e)}")
            raise
        finally:
            await db.close()

    async def _refresh_cache(self) -> None:
        """Refresh cached entities from Stash."""
        try:
            # Get all studios
            studios_data = await self.stash_service.get_all_studios()
            self._cache["studios"] = [s["name"] for s in studios_data if s.get("name")]

            # Get all performers with aliases
            performers_data = await self.stash_service.get_all_performers()
            self._cache["performers"] = [
                {"name": p["name"], "aliases": p.get("aliases", [])}
                for p in performers_data
                if p.get("name")
            ]

            # Get all tags
            tags_data = await self.stash_service.get_all_tags()
            self._cache["tags"] = [t["name"] for t in tags_data if t.get("name")]

            self._cache["last_refresh"] = datetime.utcnow()

            logger.info(
                f"Cache refreshed: {len(self._cache['studios']) if isinstance(self._cache['studios'], list) else 0} studios, "
                f"{len(self._cache['performers']) if isinstance(self._cache['performers'], list) else 0} performers, "
                f"{len(self._cache['tags']) if isinstance(self._cache['tags'], list) else 0} tags"
            )

        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")

    async def _sync_and_get_scenes(
        self, scene_ids: Optional[list[str]], filters: Optional[dict], db: AsyncSession
    ) -> list[Scene]:
        """Sync scenes from Stash to database and return them.

        Args:
            scene_ids: Optional list of scene IDs to sync
            filters: Optional filters for scene selection
            db: Database session

        Returns:
            List of synced Scene objects
        """
        if scene_ids:
            logger.debug(f"Syncing scenes by IDs: {scene_ids}")
            return await self.scene_sync_utils.sync_scenes_by_ids(
                scene_ids=scene_ids, db=db, update_existing=True
            )
        else:
            logger.debug(f"Getting scenes by filters: {filters}")
            # For filtered queries, we need to get IDs first then sync
            stash_scenes = await self._get_stash_scenes_by_filters(filters)
            scene_ids_to_sync = [s["id"] for s in stash_scenes if s.get("id")]
            if scene_ids_to_sync:
                return await self.scene_sync_utils.sync_scenes_by_ids(
                    scene_ids=scene_ids_to_sync, db=db, update_existing=True
                )
            return []

    async def _get_stash_scenes_by_filters(
        self, filters: Optional[dict]
    ) -> list[dict[str, Any]]:
        """Get scenes by filters from Stash API.

        Args:
            filters: Scene filters

        Returns:
            List of scene dictionaries from Stash
        """
        # Default filters
        if not filters:
            filters = {}

        try:
            # Use get_scenes which returns (scenes, total_count)
            scenes, _ = await self.stash_service.get_scenes(
                filter=filters, page=1, per_page=1000  # Get many at once
            )
            return scenes
        except Exception as e:
            logger.error(f"Failed to get scenes with filters: {e}")
            return []

    def _scene_to_dict(self, scene: Any) -> dict:
        """Convert scene object to dictionary.

        Args:
            scene: Scene object

        Returns:
            Scene data dictionary
        """
        return {
            "id": scene.id,
            "title": scene.title or "",
            "file_path": (
                scene.file_path
                if hasattr(scene, "file_path") and scene.file_path
                else getattr(scene, "path", "")
            ),
            "details": scene.details or "",
            "duration": scene.duration or 0,
            "width": scene.width or 0,
            "height": scene.height or 0,
            "frame_rate": getattr(scene, "framerate", getattr(scene, "frame_rate", 0))
            or 0,
            "performers": (
                scene.performers if isinstance(scene.performers, list) else []
            ),
            "tags": scene.tags if isinstance(scene.tags, list) else [],
            "studio": scene.studio,
        }

    def _dict_to_scene(self, data: dict) -> Any:
        """Convert dictionary to scene-like object.

        Args:
            data: Scene data dictionary

        Returns:
            Scene-like object
        """

        class SceneLike:
            def __init__(self, data: dict[str, Any]) -> None:
                self.id = data.get("id")
                self.title = data.get("title", "")
                self.path = data.get("path", data.get("file", {}).get("path", ""))
                self.details = data.get("details", "")
                self.duration = data.get("file", {}).get("duration", 0)
                self.width = data.get("file", {}).get("width", 0)
                self.height = data.get("file", {}).get("height", 0)
                self.frame_rate = data.get("file", {}).get("frame_rate", 0)
                self.framerate = data.get("file", {}).get(
                    "frame_rate", 0
                )  # Add framerate alias
                self.performers = data.get("performers", [])
                self.tags = data.get("tags", [])
                self.studio = data.get("studio")

            def get_primary_path(self) -> str:
                return str(self.path)

        return SceneLike(data)

    def _generate_plan_name(
        self,
        options: AnalysisOptions,
        scene_count: int,
        scenes: Optional[list[Scene]] = None,
    ) -> str:
        """Generate a descriptive plan name.

        Args:
            options: Analysis options
            scene_count: Number of scenes
            scenes: Optional list of scenes for more descriptive naming

        Returns:
            Plan name
        """
        # Try to create a descriptive name based on the scenes
        if scenes:
            name = self._generate_descriptive_name(scenes, scene_count)
            if name:
                return name

        # Fallback to original naming if no scene data available
        return self._generate_fallback_name(options, scene_count)

    def _generate_descriptive_name(
        self, scenes: list[Scene], scene_count: int
    ) -> Optional[str]:
        """Generate a descriptive name based on scene attributes."""
        # Extract common attributes from scenes
        studios, performers, dates = self._extract_scene_attributes(scenes[:20])

        # Build name parts
        name_parts = self._build_name_parts(studios, performers, dates)

        if name_parts:
            name_parts.append(f"({scene_count} scenes)")
            timestamp = datetime.utcnow().strftime("%m-%d %H:%M")
            return f"{' - '.join(name_parts)} - {timestamp}"

        return None

    def _extract_scene_attributes(self, scenes: list[Scene]) -> tuple[set, set, set]:
        """Extract common attributes from scenes."""
        studios = set()
        performers = set()
        dates = set()

        for scene in scenes:
            if hasattr(scene, "studio") and scene.studio:
                studios.add(scene.studio.name)
            if hasattr(scene, "performers"):
                for performer in scene.performers:
                    performers.add(performer.name)
            if hasattr(scene, "stash_date") and scene.stash_date:
                try:
                    year = scene.stash_date.year
                    dates.add(str(year))
                except Exception:
                    pass

        return studios, performers, dates

    def _build_name_parts(self, studios: set, performers: set, dates: set) -> list[str]:
        """Build name parts from extracted attributes."""
        name_parts = []

        if len(studios) == 1:
            name_parts.append(f"{list(studios)[0]}")
        elif len(studios) <= 3:
            name_parts.append(f"{', '.join(sorted(studios))}")

        if len(performers) == 1:
            name_parts.append(f"{list(performers)[0]}")
        elif len(performers) <= 2:
            name_parts.append(f"{', '.join(sorted(performers))}")

        if len(dates) == 1:
            name_parts.append(f"{list(dates)[0]}")
        elif len(dates) <= 2:
            name_parts.append(f"{'-'.join(sorted(dates))}")

        return name_parts

    def _generate_fallback_name(
        self, options: AnalysisOptions, scene_count: int
    ) -> str:
        """Generate fallback name based on analysis options."""
        parts = []

        if options.detect_studios:
            parts.append("Studios")
        if options.detect_performers:
            parts.append("Performers")
        if options.detect_tags:
            parts.append("Tags")
        if options.detect_details:
            parts.append("Details")

        if not parts:
            parts = ["General"]

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        return f"{', '.join(parts)} Analysis - {scene_count} scenes - {timestamp}"

    async def _create_empty_plan(self, db: Optional[AsyncSession]) -> AnalysisPlan:
        """Create an empty analysis plan when no scenes are found."""
        logger.warning("No scenes found to analyze")
        if db:
            return await self.plan_manager.create_plan(
                name="Empty Analysis",
                changes=[],
                metadata={"reason": "No scenes found"},
                db=db,
            )
        # Return a mock plan for cases where no scenes are found
        return AnalysisPlan(
            name="Empty Analysis",
            metadata={"reason": "No scenes found"},
            status="draft",
        )

    def _calculate_statistics(self, changes: list[SceneChanges]) -> dict[str, Any]:
        """Calculate statistics from analysis results.

        Args:
            changes: List of scene changes

        Returns:
            Statistics dictionary
        """
        stats: dict[str, Any] = {
            "total_scenes": len(changes),
            "scenes_with_changes": 0,
            "scenes_with_errors": 0,
            "total_changes": 0,
            "changes_by_field": {},
            "average_confidence": 0.0,
        }

        total_confidence = 0.0
        confidence_count = 0

        for scene_changes in changes:
            if scene_changes.error:
                stats["scenes_with_errors"] = stats.get("scenes_with_errors", 0) + 1
            elif scene_changes.has_changes():
                stats["scenes_with_changes"] = stats.get("scenes_with_changes", 0) + 1

                for change in scene_changes.changes:
                    stats["total_changes"] = stats.get("total_changes", 0) + 1

                    # Count by field
                    field = change.field
                    field_stats = stats["changes_by_field"]
                    if isinstance(field_stats, dict):
                        field_stats[field] = field_stats.get(field, 0) + 1

                    # Sum confidence
                    total_confidence += change.confidence
                    confidence_count += 1

        # Calculate average confidence
        if confidence_count > 0:
            stats["average_confidence"] = total_confidence / confidence_count

        return stats

    def _create_analysis_metadata(
        self,
        options: AnalysisOptions,
        scenes: list[Scene],
        all_changes: list[SceneChanges],
    ) -> dict[str, Any]:
        """Create metadata for analysis plan.

        Args:
            options: Analysis options
            scenes: List of analyzed scenes
            all_changes: List of scene changes

        Returns:
            Metadata dictionary
        """
        metadata = {
            "description": f"Analysis of {len(scenes)} scenes",
            "settings": {
                "detect_studios": options.detect_studios,
                "detect_performers": options.detect_performers,
                "detect_tags": options.detect_tags,
                "detect_details": options.detect_details,
                "confidence_threshold": options.confidence_threshold,
            },
            "statistics": self._calculate_statistics(all_changes),
            "ai_model": self.ai_client.model,
        }

        # Add cost information if cost tracker is available
        if hasattr(self, "cost_tracker"):
            metadata["api_usage"] = self.cost_tracker.get_summary()

        return metadata

    async def _mark_scenes_as_analyzed(
        self, scenes: list[Scene], db: AsyncSession
    ) -> None:
        """Mark scenes as analyzed in the database.

        Args:
            scenes: List of scenes to mark
            db: Database session
        """
        try:
            from sqlalchemy import select

            from app.models.scene import Scene as DBScene

            scene_ids = [s.id if hasattr(s, "id") else s.get("id") for s in scenes]
            logger.debug(f"Marking {len(scene_ids)} scenes as analyzed")

            result = await db.execute(select(DBScene).where(DBScene.id.in_(scene_ids)))
            db_scenes = result.scalars().all()

            logger.debug(
                f"Found {len(db_scenes)} scenes in database to mark as analyzed"
            )

            for scene in db_scenes:
                scene.analyzed = True  # type: ignore[assignment]

            await db.flush()
            logger.info(f"Successfully marked {len(db_scenes)} scenes as analyzed")

        except Exception as e:
            logger.error(f"Failed to mark scenes as analyzed: {str(e)}", exc_info=True)
            # Don't fail the entire operation if marking scenes fails
            # The analysis plan is already created

    async def _report_initial_progress(
        self, job_id: Optional[str], scene_count: int, progress_callback: Optional[Any]
    ) -> None:
        """Report initial progress for analysis job.

        Args:
            job_id: Optional job ID
            scene_count: Number of scenes to analyze
            progress_callback: Optional progress callback
        """
        if job_id:
            await self._update_job_progress(
                job_id, 0, f"Analyzing {scene_count} scenes"
            )

        if progress_callback:
            await progress_callback(0, f"Starting analysis of {scene_count} scenes")

    async def _update_job_progress(
        self,
        job_id: str,
        progress: int,
        message: str,
        status: Optional[JobStatus] = None,
    ) -> None:
        """Update job progress (placeholder for actual implementation).

        Args:
            job_id: Job ID
            progress: Progress percentage
            message: Progress message
            status: Optional status update
        """
        # TODO: Implement actual job progress update
        logger.info(f"Job {job_id}: {progress}% - {message}")

    async def _on_progress(
        self,
        job_id: str,
        completed_batches: int,
        total_batches: int,
        processed_scenes: int,
        total_scenes: int,
        progress_callback: Optional[Any] = None,
    ) -> None:
        """Progress callback for batch processing.

        Args:
            job_id: Associated job ID
            completed_batches: Number of completed batches
            total_batches: Total number of batches
            processed_scenes: Number of processed scenes
            total_scenes: Total number of scenes
            progress_callback: Optional external progress callback
        """
        progress = int((completed_batches / total_batches) * 100)
        message = f"Processed {processed_scenes}/{total_scenes} scenes ({completed_batches}/{total_batches} batches)"

        # Update job progress
        if job_id:
            await self._update_job_progress(job_id, progress, message)

        # Call external progress callback
        if progress_callback:
            await progress_callback(progress, message)

    async def apply_plan(
        self,
        plan_id: str,
        auto_approve: bool = False,
        job_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
    ) -> ApplyResult:
        """Apply an analysis plan to update scene metadata in Stash.

        Args:
            plan_id: ID of the plan to apply
            auto_approve: Whether to auto-approve all changes
            job_id: Associated job ID for progress tracking
            progress_callback: Optional callback for progress updates

        Returns:
            Result of applying the plan
        """
        # Get database session
        from app.core.database import get_async_db

        db: Optional[AsyncSession] = None
        async for session in get_async_db():
            db = session
            break

        if not db:
            raise RuntimeError("Failed to get database session")

        try:
            # Convert plan_id to int
            plan_id_int = int(plan_id)

            # Report initial progress
            if progress_callback:
                await progress_callback(0, f"Loading plan {plan_id}")

            # Get the plan
            plan = await self.plan_manager.get_plan(plan_id_int, db)
            if not plan:
                raise ValueError(f"Plan {plan_id} not found")

            total_changes = plan.get_change_count()

            if progress_callback:
                await progress_callback(5, f"Applying {total_changes} changes")

            # Apply the plan
            result = await self.plan_manager.apply_plan(
                plan_id=plan_id_int,
                db=db,
                stash_service=self.stash_service,
                apply_filters=None,  # Apply all changes
            )

            # Calculate progress
            progress = 100
            success_rate = (
                (result.applied_changes / result.total_changes * 100)
                if result.total_changes > 0
                else 0
            )
            message = f"Applied {result.applied_changes}/{result.total_changes} changes ({success_rate:.1f}% success)"

            if progress_callback:
                await progress_callback(progress, message)

            # Add scene information to result
            result.scenes_analyzed = plan.metadata.get("scene_count", 0)

            return result

        except Exception as e:
            logger.error(f"Failed to apply plan {plan_id}: {str(e)}")
            if progress_callback:
                await progress_callback(100, f"Failed: {str(e)}")
            raise
        finally:
            await db.close()
