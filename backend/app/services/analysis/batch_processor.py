"""Batch processing for efficient scene analysis."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

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
        scenes: List[Scene],
        analyzer: Callable,
        progress_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
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

        # Process batches concurrently
        results = []
        completed = 0

        # Create tasks for all batches
        tasks = []
        for batch_idx, batch in enumerate(batches):
            task = self._process_batch_with_progress(
                batch, batch_idx, analyzer, progress_callback, error_callback
            )
            tasks.append(task)

        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for batch_idx, batch_result in enumerate(batch_results):
            if isinstance(batch_result, BaseException):
                logger.error(f"Batch {batch_idx} failed: {batch_result}")
                if error_callback:
                    await error_callback(batch_idx, batch_result)
                # Add empty results for failed batch
                for scene in batches[batch_idx]:
                    # Handle both Scene objects and dictionaries
                    if isinstance(scene, dict):
                        scene_id = str(scene.get("id", ""))
                        scene_title = str(scene.get("title", "Untitled"))
                        scene_path = scene.get(
                            "path", scene.get("file", {}).get("path", "")
                        )
                    else:
                        scene_id = str(scene.id)
                        scene_title = str(scene.title or "Untitled")
                        scene_path = scene.get_primary_path() or ""

                    results.append(
                        SceneChanges(
                            scene_id=scene_id,
                            scene_title=scene_title,
                            scene_path=scene_path,
                            changes=[],
                            error=str(batch_result),
                        )
                    )
            else:
                results.extend(batch_result)

            completed += 1
            if progress_callback:
                await progress_callback(
                    completed, total_batches, len(results), len(scenes)
                )

        logger.info(f"Completed processing {len(results)} scenes")
        return results

    async def process_batch(
        self, batch: List[Scene], analyzer: Callable
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
                        "file_path": scene.get(
                            "path", scene.get("file", {}).get("path", "")
                        ),
                        "details": scene.get("details", ""),
                        "duration": scene.get("file", {}).get("duration", 0),
                        "width": scene.get("file", {}).get("width", 0),
                        "height": scene.get("file", {}).get("height", 0),
                        "frame_rate": scene.get("file", {}).get("frame_rate", 0),
                        "performers": scene.get("performers", []),
                        "tags": scene.get("tags", []),
                        "studio": scene.get("studio"),
                    }
                else:
                    # Scene is an object, convert it to dictionary
                    scene_dict = {
                        "id": scene.id,
                        "title": scene.title,
                        "file_path": scene.get_primary_path() or "",
                        "details": scene.details,
                        "duration": scene.duration,
                        "width": scene.width,
                        "height": scene.height,
                        "frame_rate": scene.framerate,
                        "performers": [
                            {"id": p.id, "name": p.name} for p in scene.performers
                        ],
                        "tags": [{"id": t.id, "name": t.name} for t in scene.tags],
                        "studio": (
                            {"id": scene.studio.id, "name": scene.studio.name}
                            if scene.studio
                            else None
                        ),
                    }
                batch_data.append(scene_dict)

            # Analyze the batch
            result = await analyzer(batch_data)
            return result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Return error results for all scenes in batch
            results = []
            for scene in batch:
                results.append(
                    SceneChanges(
                        scene_id=str(scene.id),
                        scene_title=str(scene.title or "Untitled"),
                        scene_path=scene.get_primary_path() or "",
                        changes=[],
                        error=str(e),
                    )
                )
            return results

    async def _process_batch_with_progress(
        self,
        batch: List[Scene],
        batch_idx: int,
        analyzer: Callable,
        progress_callback: Optional[Callable],
        error_callback: Optional[Callable],
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

    def _create_batches(self, scenes: List[Scene]) -> List[List[Scene]]:
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

    def estimate_processing_time(
        self, scene_count: int, seconds_per_scene: float = 2.0
    ) -> Dict[str, float]:
        """Estimate processing time for given number of scenes.

        Args:
            scene_count: Number of scenes to process
            seconds_per_scene: Estimated seconds per scene

        Returns:
            Dictionary with time estimates
        """
        if scene_count == 0:
            return {
                "total_seconds": 0,
                "total_minutes": 0,
                "batches": 0,
                "parallel_factor": 1,
            }

        # Calculate batches
        batch_count = (scene_count + self.batch_size - 1) // self.batch_size

        # Calculate parallel processing factor
        parallel_factor = min(batch_count, self.max_concurrent)

        # Estimate time
        total_seconds = (scene_count * seconds_per_scene) / parallel_factor

        return {
            "total_seconds": total_seconds,
            "total_minutes": total_seconds / 60,
            "batches": batch_count,
            "parallel_factor": parallel_factor,
            "scenes_per_batch": self.batch_size,
        }

    def adjust_batch_size(self, new_size: int) -> None:
        """Adjust batch size dynamically.

        Args:
            new_size: New batch size
        """
        if new_size < 1:
            raise ValueError("Batch size must be at least 1")
        if new_size > 100:
            raise ValueError("Batch size cannot exceed 100")

        self.batch_size = new_size
        logger.info(f"Batch size adjusted to {new_size}")

    def adjust_concurrency(self, new_limit: int) -> None:
        """Adjust concurrent batch limit.

        Args:
            new_limit: New concurrency limit
        """
        if new_limit < 1:
            raise ValueError("Concurrency must be at least 1")
        if new_limit > 10:
            raise ValueError("Concurrency cannot exceed 10")

        self.max_concurrent = new_limit
        self._semaphore = asyncio.Semaphore(new_limit)
        logger.info(f"Concurrency adjusted to {new_limit}")
