"""Batch processing for efficient scene analysis."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.models.scene import Scene

from .models import SceneChanges

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process scenes in batches for efficient analysis."""

    def __init__(self, batch_size: int = 10, max_concurrent: int = 3):
        """Initialize batch processor.

        Args:
            batch_size: Number of scenes per batch
            max_concurrent: Maximum concurrent batches
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process_scenes(
        self,
        scenes: List[Union[Scene, Dict[str, Any], Any]],
        analyzer: Callable,
        progress_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        cancellation_token: Optional[Any] = None,
    ) -> List[SceneChanges]:
        """Process scenes in batches with progress tracking.

        Args:
            scenes: List of scenes to process
            analyzer: Async function to analyze a batch of scenes
            progress_callback: Optional callback for progress updates
            error_callback: Optional callback for errors

        Returns:
            List of scene changes for all scenes
        """
        if not scenes:
            return []

        # Create batches
        batches = self._create_batches(scenes)
        total_batches = len(batches)

        logger.info(f"Processing {len(scenes)} scenes in {total_batches} batches")

        # Process batches with cancellation checks
        results = []
        completed = 0

        # Process batches in controlled concurrency with cancellation checks
        batch_tasks = []
        batch_indices = []

        for batch_idx, batch in enumerate(batches):
            # Check for cancellation before processing each batch
            if cancellation_token and hasattr(cancellation_token, "check_cancellation"):
                await cancellation_token.check_cancellation()

            # Create task for this batch
            task = self._process_batch_with_progress(
                batch,
                batch_idx,
                analyzer,
                progress_callback,
                error_callback,
                cancellation_token,
            )
            batch_tasks.append(task)
            batch_indices.append(batch_idx)

            # Process batches in groups to allow cancellation checks
            if len(batch_tasks) >= self.max_concurrent or batch_idx == len(batches) - 1:
                # Wait for current group of tasks
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )

                # Process results
                for task_idx, batch_result in enumerate(batch_results):
                    actual_batch_idx = batch_indices[task_idx]
                    if isinstance(batch_result, BaseException):
                        logger.error(f"Batch {actual_batch_idx} failed: {batch_result}")
                        if error_callback:
                            await error_callback(actual_batch_idx, batch_result)
                        # Add empty results for failed batch
                        error_results = self._create_error_results(
                            batches[actual_batch_idx], str(batch_result)
                        )
                        results.extend(error_results)
                    else:
                        results.extend(batch_result)

                    completed += 1
                    if progress_callback:
                        await progress_callback(
                            completed, total_batches, len(results), len(scenes)
                        )

                # Clear for next group
                batch_tasks = []
                batch_indices = []

        logger.info(f"Completed processing {len(results)} scenes")
        return results

    async def process_batch(
        self, batch: List[Union[Scene, Dict[str, Any], Any]], analyzer: Callable
    ) -> List[SceneChanges]:
        """Process a single batch of scenes.

        Args:
            batch: Batch of scenes
            analyzer: Analysis function

        Returns:
            List of scene changes for the batch
        """
        try:
            # Convert scenes to dictionaries for analysis
            batch_data = []
            for scene in batch:
                # Handle both Scene objects and dictionaries
                if isinstance(scene, dict):
                    # Scene is already a dictionary, just ensure it has the right structure
                    scene_dict = {
                        "id": scene.get("id"),
                        "title": scene.get("title", ""),
                        "file_path": scene.get("file_path")
                        or scene.get("path", scene.get("file", {}).get("path", "")),
                        "details": scene.get("details", ""),
                        "duration": scene.get("file", {}).get("duration", 0),
                        "width": scene.get("file", {}).get("width", 0),
                        "height": scene.get("file", {}).get("height", 0),
                        "frame_rate": scene.get("file", {}).get("frame_rate", 0),
                        "performers": scene.get("performers", []),
                        "tags": scene.get("tags", []),
                        "studio": scene.get("studio"),
                    }
                    # Debug log for dictionary case
                    logger.debug(
                        f"Scene {scene_dict['id']} (dict) - file_path: {scene_dict['file_path']}"
                    )
                else:
                    # Scene is an object, convert it to dictionary
                    studio = getattr(scene, "studio", None)
                    studio_dict = None
                    if studio:
                        if isinstance(studio, dict):
                            studio_dict = {
                                "id": studio.get("id", ""),
                                "name": studio.get("name", ""),
                            }
                        else:
                            studio_dict = {
                                "id": getattr(studio, "id", ""),
                                "name": getattr(studio, "name", ""),
                            }

                    # Debug logging for file_path
                    scene_file_path = getattr(scene, "file_path", None)
                    logger.debug(
                        f"Scene {getattr(scene, 'id', 'unknown')} - file_path attribute: {scene_file_path}"
                    )

                    scene_dict = {
                        "id": getattr(scene, "id", ""),
                        "title": getattr(scene, "title", ""),
                        "file_path": (
                            scene_file_path  # First try file_path
                            or (
                                getattr(
                                    scene,
                                    "get_primary_path",
                                    lambda: getattr(scene, "path", ""),
                                )()
                                if hasattr(scene, "get_primary_path")
                                else getattr(scene, "path", "")
                            )
                        ),
                        "details": getattr(scene, "details", ""),
                        "duration": getattr(scene, "duration", 0),
                        "width": getattr(scene, "width", 0),
                        "height": getattr(scene, "height", 0),
                        "frame_rate": getattr(
                            scene, "framerate", getattr(scene, "frame_rate", 0)
                        ),
                        "performers": [
                            {
                                "id": (
                                    p.get("id", "")
                                    if isinstance(p, dict)
                                    else getattr(p, "id", "")
                                ),
                                "name": (
                                    p.get("name", "")
                                    if isinstance(p, dict)
                                    else getattr(p, "name", "")
                                ),
                            }
                            for p in getattr(scene, "performers", [])
                        ],
                        "tags": [
                            {
                                "id": (
                                    t.get("id", "")
                                    if isinstance(t, dict)
                                    else getattr(t, "id", "")
                                ),
                                "name": (
                                    t.get("name", "")
                                    if isinstance(t, dict)
                                    else getattr(t, "name", "")
                                ),
                            }
                            for t in getattr(scene, "tags", [])
                        ],
                        "studio": studio_dict,
                    }

                    # Debug log the final file_path in the dictionary
                    logger.debug(
                        f"Scene {scene_dict['id']} - final file_path in dict: {scene_dict['file_path']}"
                    )

                batch_data.append(scene_dict)

            # Analyze the batch
            result = await analyzer(batch_data)
            return result  # type: ignore[no-any-return]

        except asyncio.CancelledError:
            # Re-raise cancellation without logging
            raise
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Return error results for all scenes in batch
            return self._create_error_results(batch, str(e))

    async def _process_batch_with_progress(
        self,
        batch: List[Union[Scene, Dict[str, Any], Any]],
        batch_idx: int,
        analyzer: Callable,
        progress_callback: Optional[Callable],
        error_callback: Optional[Callable],
        cancellation_token: Optional[Any] = None,
    ) -> List[SceneChanges]:
        """Process a batch with semaphore control and progress tracking.

        Args:
            batch: Batch to process
            batch_idx: Batch index
            analyzer: Analysis function
            progress_callback: Progress callback
            error_callback: Error callback

        Returns:
            Batch results
        """
        async with self._semaphore:
            start_time = datetime.utcnow()

            try:
                # Check for cancellation at the start of batch processing
                if cancellation_token and hasattr(
                    cancellation_token, "check_cancellation"
                ):
                    await cancellation_token.check_cancellation()

                logger.debug(
                    f"Processing batch {batch_idx + 1} with {len(batch)} scenes"
                )
                results = await self.process_batch(batch, analyzer)

                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(f"Batch {batch_idx + 1} completed in {elapsed:.2f}s")

                return results

            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed: {e}")
                if error_callback:
                    await error_callback(batch_idx, e)
                raise

    def _create_batches(
        self, scenes: List[Union[Scene, Dict[str, Any], Any]]
    ) -> List[List[Union[Scene, Dict[str, Any], Any]]]:
        """Create batches from scene list.

        Args:
            scenes: List of scenes

        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(scenes), self.batch_size):
            batch = scenes[i : i + self.batch_size]
            batches.append(batch)
        return batches

    def _create_error_results(
        self, batch: List[Union[Scene, Dict[str, Any], Any]], error_message: str
    ) -> List[SceneChanges]:
        """Create error results for all scenes in a failed batch.

        Args:
            batch: Batch of scenes that failed
            error_message: Error message to include

        Returns:
            List of SceneChanges with error information
        """
        results = []
        for scene in batch:
            scene_id, scene_title, scene_path = self._extract_scene_info(scene)
            results.append(
                SceneChanges(
                    scene_id=scene_id,
                    scene_title=scene_title,
                    scene_path=scene_path,
                    changes=[],
                    error=error_message,
                )
            )
        return results

    def _extract_scene_info(
        self, scene: Union[Scene, Dict[str, Any], Any]
    ) -> Tuple[str, str, str]:
        """Extract scene ID, title, and path from scene object or dictionary.

        Args:
            scene: Scene object or dictionary

        Returns:
            Tuple of (scene_id, scene_title, scene_path)
        """
        if isinstance(scene, dict):
            scene_id = str(scene.get("id", ""))
            scene_title = str(scene.get("title", "Untitled"))
            scene_path = scene.get("path", scene.get("file", {}).get("path", ""))
        else:
            # Handle Scene-like objects
            scene_id = str(getattr(scene, "id", ""))
            scene_title = str(getattr(scene, "title", "Untitled") or "Untitled")
            scene_path = (
                getattr(
                    scene,
                    "get_primary_path",
                    lambda: getattr(scene, "path", ""),
                )()
                if hasattr(scene, "get_primary_path")
                else getattr(scene, "path", "")
            )
        return scene_id, scene_title, scene_path
