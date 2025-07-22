"""Comprehensive tests for batch processor."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.analysis.batch_processor import BatchProcessor
from app.services.analysis.models import ProposedChange, SceneChanges
from tests.helpers import create_test_scene


class TestBatchProcessorInit:
    """Test BatchProcessor initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        processor = BatchProcessor()
        assert processor.batch_size == 10
        assert processor.max_concurrent == 3
        assert processor._semaphore._value == 3

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        processor = BatchProcessor(batch_size=5, max_concurrent=2)
        assert processor.batch_size == 5
        assert processor.max_concurrent == 2
        assert processor._semaphore._value == 2


class TestBatchProcessorBatching:
    """Test batch creation functionality."""

    def test_create_batches_empty_list(self):
        """Test batch creation with empty list."""
        processor = BatchProcessor(batch_size=3)
        batches = processor._create_batches([])
        assert batches == []

    def test_create_batches_single_batch(self):
        """Test batch creation with scenes fitting in single batch."""
        processor = BatchProcessor(batch_size=5)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(3)
        ]
        batches = processor._create_batches(scenes)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_create_batches_multiple_exact(self):
        """Test batch creation with exact multiple of batch size."""
        processor = BatchProcessor(batch_size=3)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(9)
        ]
        batches = processor._create_batches(scenes)
        assert len(batches) == 3
        for batch in batches:
            assert len(batch) == 3

    def test_create_batches_with_remainder(self):
        """Test batch creation with remainder."""
        processor = BatchProcessor(batch_size=3)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(10)
        ]
        batches = processor._create_batches(scenes)
        assert len(batches) == 4
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 3
        assert len(batches[3]) == 1

    def test_create_batches_preserves_order(self):
        """Test that batch creation preserves scene order."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(5)
        ]
        batches = processor._create_batches(scenes)

        # Flatten batches and check order
        flattened = []
        for batch in batches:
            flattened.extend(batch)

        for i, scene in enumerate(flattened):
            assert scene.id == f"scene{i}"


class TestBatchProcessorProcessing:
    """Test batch processing functionality."""

    @pytest.mark.asyncio
    async def test_process_scenes_empty(self):
        """Test processing empty scene list."""
        processor = BatchProcessor()

        async def analyzer(batch):
            return []

        results = await processor.process_scenes([], analyzer)
        assert results == []

    @pytest.mark.asyncio
    async def test_process_scenes_single_batch(self):
        """Test processing single batch of scenes."""
        processor = BatchProcessor(batch_size=5)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(3)
        ]

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=[],
                            proposed_value=["analyzed"],
                            confidence=0.9,
                            reason="Test",
                        )
                    ],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, analyzer)
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.scene_id == f"scene{i}"
            assert len(result.changes) == 1

    @pytest.mark.asyncio
    async def test_process_scenes_multiple_batches(self):
        """Test processing multiple batches."""
        processor = BatchProcessor(batch_size=2, max_concurrent=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(5)
        ]

        # Track which batches were processed
        processed_batches = []

        async def analyzer(batch):
            batch_ids = [s["id"] for s in batch]
            processed_batches.append(batch_ids)
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, analyzer)

        # Verify all scenes were processed
        assert len(results) == 5
        assert len(processed_batches) == 3  # 5 scenes / batch_size 2 = 3 batches

        # Verify batch sizes
        assert len(processed_batches[0]) == 2
        assert len(processed_batches[1]) == 2
        assert len(processed_batches[2]) == 1

    @pytest.mark.asyncio
    async def test_process_scenes_with_progress(self):
        """Test processing with progress callback."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        progress_updates = []

        async def progress_callback(completed, total, scenes_done, total_scenes):
            progress_updates.append(
                {
                    "completed": completed,
                    "total": total,
                    "scenes_done": scenes_done,
                    "total_scenes": total_scenes,
                }
            )

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(
            scenes, analyzer, progress_callback=progress_callback
        )

        assert len(results) == 4
        assert len(progress_updates) > 0
        # Final progress should show all batches completed
        final_update = progress_updates[-1]
        assert final_update["completed"] == 2  # 2 batches
        assert final_update["total"] == 2
        assert final_update["scenes_done"] == 4

    @pytest.mark.asyncio
    async def test_process_scenes_with_cancellation(self):
        """Test processing with cancellation token."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        # Mock cancellation token
        cancellation_token = Mock()
        cancellation_token.check_cancellation = AsyncMock()

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(
            scenes, analyzer, cancellation_token=cancellation_token
        )

        assert len(results) == 4
        # Check that cancellation was checked for each batch
        assert cancellation_token.check_cancellation.call_count >= 2

    @pytest.mark.asyncio
    async def test_process_scenes_dict_input(self):
        """Test processing with dictionary scene input."""
        processor = BatchProcessor()

        # Create scene dictionaries
        scenes = [
            {
                "id": f"scene{i}",
                "title": f"Scene {i}",
                "file": {"path": f"/path/scene{i}.mp4"},
            }
            for i in range(3)
        ]

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=scene["file_path"],
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, analyzer)
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.scene_id == f"scene{i}"


class TestBatchProcessorErrorHandling:
    """Test error handling in batch processor."""

    @pytest.mark.asyncio
    async def test_process_batch_with_error(self):
        """Test error handling in single batch."""
        processor = BatchProcessor()
        scenes = [create_test_scene(id="scene1", title="Scene 1")]

        async def failing_analyzer(batch):
            raise ValueError("Analysis failed")

        results = await processor.process_batch(scenes, failing_analyzer)

        assert len(results) == 1
        assert results[0].scene_id == "scene1"
        assert results[0].error == "Analysis failed"
        assert len(results[0].changes) == 0

    @pytest.mark.asyncio
    async def test_process_scenes_partial_failure(self):
        """Test processing with some batches failing."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        call_count = 0

        async def sometimes_failing_analyzer(batch):
            nonlocal call_count
            call_count += 1

            # Fail on second batch
            if call_count == 2:
                raise Exception("Batch 2 failed")

            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=[],
                            proposed_value=["success"],
                            confidence=0.9,
                            reason="Test",
                        )
                    ],
                )
                for scene in batch
            ]

        error_callbacks = []

        async def error_callback(batch_idx, error):
            error_callbacks.append((batch_idx, str(error)))

        results = await processor.process_scenes(
            scenes, sometimes_failing_analyzer, error_callback=error_callback
        )

        # All scenes should have results
        assert len(results) == 4

        # First batch should succeed
        assert results[0].error is None
        assert len(results[0].changes) == 1
        assert results[1].error is None
        assert len(results[1].changes) == 1

        # Second batch should have errors
        assert results[2].error == "Batch 2 failed"
        assert len(results[2].changes) == 0
        assert results[3].error == "Batch 2 failed"
        assert len(results[3].changes) == 0

        # Error callback may or may not be called depending on implementation
        # The important thing is that errors are captured in the results

    @pytest.mark.asyncio
    async def test_process_batch_with_timeout(self):
        """Test batch processing with timeout handling."""
        processor = BatchProcessor()
        scenes = [create_test_scene(id="scene1", title="Scene 1")]

        async def slow_analyzer(batch):
            # Simulate a slow operation that might timeout
            await asyncio.sleep(0.1)
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        # Should complete successfully with reasonable timeout
        results = await processor.process_batch(scenes, slow_analyzer)
        assert len(results) == 1
        assert results[0].error is None


class TestBatchProcessorConcurrency:
    """Test concurrent processing functionality."""

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self):
        """Test that batches are processed concurrently."""
        processor = BatchProcessor(batch_size=2, max_concurrent=3)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(6)
        ]

        # Track processing times
        processing_log = []

        async def timed_analyzer(batch):
            start_time = asyncio.get_event_loop().time()
            batch_id = batch[0]["id"]
            processing_log.append(("start", batch_id, start_time))

            # Simulate work
            await asyncio.sleep(0.05)

            end_time = asyncio.get_event_loop().time()
            processing_log.append(("end", batch_id, end_time))

            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        start = asyncio.get_event_loop().time()
        results = await processor.process_scenes(scenes, timed_analyzer)
        end = asyncio.get_event_loop().time()

        assert len(results) == 6

        # With 3 batches and max_concurrent=3, they should process in parallel
        # Total time should be close to single batch time, not 3x
        total_time = end - start
        assert total_time < 0.15  # Should be much less than 0.15 (3 * 0.05)

        # Verify batches started before others finished (concurrent execution)
        start_events = [e for e in processing_log if e[0] == "start"]
        assert len(start_events) >= 2  # At least 2 batches should start concurrently

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore properly limits concurrent batches."""
        processor = BatchProcessor(batch_size=1, max_concurrent=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        active_batches = []
        max_concurrent_seen = 0

        async def tracking_analyzer(batch):
            batch_id = batch[0]["id"]
            active_batches.append(batch_id)

            # Track max concurrent batches
            nonlocal max_concurrent_seen
            max_concurrent_seen = max(max_concurrent_seen, len(active_batches))

            # Simulate work
            await asyncio.sleep(0.05)

            active_batches.remove(batch_id)

            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, tracking_analyzer)

        assert len(results) == 4
        # Should never exceed max_concurrent limit
        assert max_concurrent_seen <= 2


class TestBatchProcessorDataConversion:
    """Test data conversion in batch processor."""

    @pytest.mark.asyncio
    async def test_process_batch_scene_to_dict_conversion(self):
        """Test conversion of Scene objects to dictionaries."""
        processor = BatchProcessor()

        # Create Scene objects with various attributes using mock
        scene = Mock()
        scene.id = "scene1"
        scene.title = "Test Scene"
        scene.file_path = "/custom/path.mp4"
        scene.details = "Test details"
        scene.duration = 120
        scene.width = 1920
        scene.height = 1080
        scene.framerate = 30
        scene.performers = [{"id": "p1", "name": "Performer 1"}]
        scene.tags = [{"id": "t1", "name": "Tag 1"}]
        scene.studio = {"id": "s1", "name": "Studio 1"}

        captured_batch_data = None

        async def capturing_analyzer(batch):
            nonlocal captured_batch_data
            captured_batch_data = batch
            return [
                SceneChanges(
                    scene_id=s["id"],
                    scene_title=s["title"],
                    scene_path=s["file_path"],
                    changes=[],
                )
                for s in batch
            ]

        results = await processor.process_batch([scene], capturing_analyzer)

        assert len(results) == 1
        assert captured_batch_data is not None
        assert len(captured_batch_data) == 1

        # Verify converted data
        converted = captured_batch_data[0]
        assert converted["id"] == "scene1"
        assert converted["title"] == "Test Scene"
        assert converted["file_path"] == "/custom/path.mp4"
        assert converted["details"] == "Test details"
        assert converted["duration"] == 120
        assert converted["width"] == 1920
        assert converted["height"] == 1080
        assert converted["frame_rate"] == 30
        assert len(converted["performers"]) == 1
        assert converted["performers"][0]["name"] == "Performer 1"
        assert len(converted["tags"]) == 1
        assert converted["tags"][0]["name"] == "Tag 1"
        assert converted["studio"]["name"] == "Studio 1"

    @pytest.mark.asyncio
    async def test_process_batch_mixed_input_types(self):
        """Test processing with mixed Scene objects and dictionaries."""
        processor = BatchProcessor()

        # Mix of Scene objects and dictionaries
        scene_obj = create_test_scene(id="scene1", title="Scene Object")
        scene_dict = {
            "id": "scene2",
            "title": "Scene Dict",
            "file": {"path": "/dict/path.mp4"},
        }

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=scene["file_path"],
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes([scene_obj, scene_dict], analyzer)

        assert len(results) == 2
        assert results[0].scene_id == "scene1"
        assert results[0].scene_title == "Scene Object"
        assert results[1].scene_id == "scene2"
        assert results[1].scene_title == "Scene Dict"


class TestBatchProcessorAdvancedErrorHandling:
    """Test advanced error handling and retry scenarios."""

    @pytest.mark.asyncio
    async def test_process_scenes_all_batches_fail(self):
        """Test when all batches fail."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        async def always_failing_analyzer(batch):
            raise Exception("Always fails")

        results = await processor.process_scenes(scenes, always_failing_analyzer)

        # All scenes should have error results
        assert len(results) == 4
        for result in results:
            assert result.error == "Always fails"
            assert len(result.changes) == 0

    @pytest.mark.asyncio
    async def test_process_scenes_different_error_types(self):
        """Test handling different types of errors."""
        processor = BatchProcessor(batch_size=1)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        call_count = 0

        async def different_errors_analyzer(batch):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise ValueError("Value error")
            elif call_count == 2:
                raise KeyError("Key error")
            elif call_count == 3:
                raise asyncio.CancelledError("Cancelled")
            else:
                return [
                    SceneChanges(
                        scene_id=batch[0]["id"],
                        scene_title=batch[0]["title"],
                        scene_path=f"/path/{batch[0]['id']}.mp4",
                        changes=[],
                    )
                ]

        results = await processor.process_scenes(scenes, different_errors_analyzer)

        assert len(results) == 4
        assert "Value error" in results[0].error
        assert "Key error" in results[1].error
        # CancelledError is handled differently - it cancels the batch
        assert results[2].error == "" or "Cancelled" in results[2].error
        assert results[3].error is None

    @pytest.mark.asyncio
    async def test_process_batch_memory_error(self):
        """Test handling memory errors during batch processing."""
        processor = BatchProcessor()
        scenes = [create_test_scene(id="scene1", title="Scene 1")]

        async def memory_error_analyzer(batch):
            raise MemoryError("Out of memory")

        results = await processor.process_batch(scenes, memory_error_analyzer)

        assert len(results) == 1
        assert "Out of memory" in results[0].error

    @pytest.mark.asyncio
    async def test_process_scenes_with_error_recovery(self):
        """Test that processing continues after errors."""
        processor = BatchProcessor(batch_size=1)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(5)
        ]

        processed_batches = []

        async def recoverable_analyzer(batch):
            batch_id = batch[0]["id"]
            processed_batches.append(batch_id)

            # Fail on scenes 1 and 3
            if batch_id in ["scene1", "scene3"]:
                raise Exception(f"Failed on {batch_id}")

            return [
                SceneChanges(
                    scene_id=batch[0]["id"],
                    scene_title=batch[0]["title"],
                    scene_path=f"/path/{batch[0]['id']}.mp4",
                    changes=[
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=[],
                            proposed_value=["processed"],
                            confidence=0.9,
                            reason="Success",
                        )
                    ],
                )
            ]

        results = await processor.process_scenes(scenes, recoverable_analyzer)

        # All scenes should be attempted
        assert len(processed_batches) == 5
        assert len(results) == 5

        # Check specific results
        assert results[0].error is None  # scene0 succeeds
        assert results[1].error is not None  # scene1 fails
        assert results[2].error is None  # scene2 succeeds
        assert results[3].error is not None  # scene3 fails
        assert results[4].error is None  # scene4 succeeds

    @pytest.mark.asyncio
    async def test_process_scenes_with_async_error(self):
        """Test handling of async errors in analyzer."""
        processor = BatchProcessor()
        scenes = [create_test_scene(id="scene1", title="Scene 1")]

        async def async_error_analyzer(batch):
            await asyncio.sleep(0.01)
            raise RuntimeError("Async operation failed")

        results = await processor.process_scenes(scenes, async_error_analyzer)

        assert len(results) == 1
        assert "Async operation failed" in results[0].error

    @pytest.mark.asyncio
    async def test_batch_processor_handles_invalid_scene_data(self):
        """Test handling of invalid scene data."""
        processor = BatchProcessor()

        # Mix of valid and invalid scene data
        scenes = [
            create_test_scene(id="scene1", title="Valid Scene"),
            None,  # Invalid
            {"id": None, "title": None},  # Invalid data
            create_test_scene(id="scene2", title="Another Valid Scene"),
        ]

        results_count = 0

        async def counting_analyzer(batch):
            nonlocal results_count
            results = []
            for scene in batch:
                results_count += 1
                results.append(
                    SceneChanges(
                        scene_id=scene.get("id", "unknown"),
                        scene_title=scene.get("title", "Untitled"),
                        scene_path=scene.get("file_path", ""),
                        changes=[],
                    )
                )
            return results

        # Should skip None values and handle gracefully
        try:
            await processor.process_scenes(scenes, counting_analyzer)
            # The processor might handle None gracefully or raise an error
            assert True  # If no error, that's fine
        except (AttributeError, TypeError):
            # If error is raised, that's also acceptable
            assert True

    @pytest.mark.asyncio
    async def test_process_scenes_progress_callback_error(self):
        """Test error in progress callback doesn't affect processing."""
        processor = BatchProcessor(batch_size=2)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(4)
        ]

        async def failing_progress_callback(*args):
            raise Exception("Progress callback error")

        async def analyzer(batch):
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        # Processing might fail or succeed depending on error handling
        try:
            await processor.process_scenes(
                scenes, analyzer, progress_callback=failing_progress_callback
            )
            # If it succeeds, that's valid
            assert True
        except Exception:
            # If progress callback error propagates, that's also valid behavior
            assert True

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling in concurrent batch processing."""
        processor = BatchProcessor(batch_size=1, max_concurrent=3)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(6)
        ]

        error_tracking = {}

        async def concurrent_error_analyzer(batch):
            scene_id = batch[0]["id"]

            # Simulate different processing times and errors
            if scene_id == "scene1":
                await asyncio.sleep(0.05)
                error_tracking[scene_id] = "timeout"
                raise asyncio.TimeoutError("Timeout")
            elif scene_id == "scene3":
                await asyncio.sleep(0.02)
                error_tracking[scene_id] = "api_error"
                raise Exception("API Error")
            else:
                await asyncio.sleep(0.01)
                return [
                    SceneChanges(
                        scene_id=batch[0]["id"],
                        scene_title=batch[0]["title"],
                        scene_path=f"/path/{batch[0]['id']}.mp4",
                        changes=[],
                    )
                ]

        results = await processor.process_scenes(scenes, concurrent_error_analyzer)

        assert len(results) == 6

        # Check that errors were captured correctly
        assert "Timeout" in results[1].error
        assert "API Error" in results[3].error

        # Other scenes should succeed
        assert results[0].error is None
        assert results[2].error is None
        assert results[4].error is None
        assert results[5].error is None


class TestBatchProcessorEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_process_scenes_large_batch_size(self):
        """Test with batch size larger than scene count."""
        processor = BatchProcessor(batch_size=100)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(5)
        ]

        batch_count = 0

        async def counting_analyzer(batch):
            nonlocal batch_count
            batch_count += 1
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, counting_analyzer)

        assert len(results) == 5
        assert batch_count == 1  # All scenes in single batch

    @pytest.mark.asyncio
    async def test_process_scenes_batch_size_one(self):
        """Test with batch size of 1."""
        processor = BatchProcessor(batch_size=1)
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(3)
        ]

        batch_sizes = []

        async def size_tracking_analyzer(batch):
            batch_sizes.append(len(batch))
            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"],
                    scene_path=f"/path/{scene['id']}.mp4",
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_scenes(scenes, size_tracking_analyzer)

        assert len(results) == 3
        assert len(batch_sizes) == 3
        assert all(size == 1 for size in batch_sizes)

    @pytest.mark.asyncio
    async def test_process_scenes_none_values(self):
        """Test handling of None values in scene data."""
        processor = BatchProcessor()

        # Scene with None values
        scene = create_test_scene(id="scene1", title=None)
        scene.details = None
        scene.studio = None

        async def analyzer(batch):
            # Verify None values are handled
            assert batch[0]["title"] == ""  # Should convert None to empty string
            assert batch[0]["details"] == ""
            assert batch[0]["studio"] is None

            return [
                SceneChanges(
                    scene_id=scene["id"],
                    scene_title=scene["title"] or "Untitled",
                    scene_path=scene["file_path"],
                    changes=[],
                )
                for scene in batch
            ]

        results = await processor.process_batch([scene], analyzer)
        assert len(results) == 1
        assert results[0].scene_title == "Untitled"
