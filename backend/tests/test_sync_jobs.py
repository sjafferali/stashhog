"""Tests for sync job functions."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.sync_jobs import (
    register_sync_jobs,
    sync_all_job,
    sync_performers_job,
    sync_scenes_job,
    sync_studios_job,
    sync_tags_job,
)
from app.models.job import JobType
from app.services.job_service import JobService
from app.services.sync.models import SyncResult, SyncStatus


class TestSyncJobs:
    """Test sync job functions."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings object."""
        settings = Mock()
        settings.stash.url = "http://test.stash"
        settings.stash.api_key = "test-api-key"
        return settings

    @pytest.fixture
    def mock_sync_result(self):
        """Create a mock sync result."""
        return SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status=SyncStatus.SUCCESS,
            total_items=100,
            processed_items=100,
            created_items=20,
            updated_items=50,
            skipped_items=30,
            failed_items=0,
        )

    @pytest.fixture
    def mock_progress_callback(self):
        """Mock progress callback function."""
        return Mock()

    @pytest.mark.asyncio
    async def test_sync_all_job_success(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test successful sync_all job execution."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService") as mock_stash_service_class:
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=True,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"
        assert result["total_items"] == 100
        assert result["processed_items"] == 100
        assert result["created_items"] == 20
        assert result["updated_items"] == 50
        assert result["failed_items"] == 0
        assert result["success_rate"] == 1.0

        # Verify service calls
        mock_stash_service_class.assert_called_once_with(
            stash_url="http://test.stash", api_key="test-api-key"
        )
        mock_sync_service_class.assert_called_once_with(
            mock_stash_service_class.return_value, mock_db
        )
        mock_sync_service.sync_all.assert_called_once_with(
            job_id="test-job-123",
            force=True,
            progress_callback=mock_progress_callback,
            cancellation_token=None,
        )

    @pytest.mark.asyncio
    async def test_sync_all_job_failure(self, mock_settings, mock_progress_callback):
        """Test sync_all job with failure."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.side_effect = Exception("Sync failed")

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act & Assert
                        with pytest.raises(Exception, match="Sync failed"):
                            await sync_all_job(
                                job_id="test-job-123",
                                progress_callback=mock_progress_callback,
                                force=False,
                            )

    @pytest.mark.asyncio
    async def test_sync_scenes_job_success(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test successful sync_scenes job execution."""
        # Arrange
        scene_ids = ["scene1", "scene2", "scene3"]
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_scenes.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_scenes_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            scene_ids=scene_ids,
                            force=True,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"
        assert result["total_items"] == 100

        # Verify service calls
        mock_sync_service.sync_scenes.assert_called_once_with(
            scene_ids=scene_ids,
            job_id="test-job-123",
            force=True,
            progress_callback=mock_progress_callback,
            cancellation_token=None,
        )

    @pytest.mark.asyncio
    async def test_sync_scenes_job_empty_list(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test sync_scenes job with empty scene list."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_scenes.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_scenes_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            scene_ids=None,
                            force=False,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        mock_sync_service.sync_scenes.assert_called_once_with(
            scene_ids=None,
            job_id="test-job-123",
            force=False,
            progress_callback=mock_progress_callback,
            cancellation_token=None,
        )

    @pytest.mark.asyncio
    async def test_sync_performers_job_success(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test successful sync_performers job execution."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_performers.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_performers_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=True,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"
        mock_sync_service.sync_performers.assert_called_once_with(
            job_id="test-job-123", force=True, progress_callback=mock_progress_callback
        )

    @pytest.mark.asyncio
    async def test_sync_tags_job_success(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test successful sync_tags job execution."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_tags.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_tags_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=False,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"
        mock_sync_service.sync_tags.assert_called_once_with(
            job_id="test-job-123", force=False, progress_callback=mock_progress_callback
        )

    @pytest.mark.asyncio
    async def test_sync_studios_job_success(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test successful sync_studios job execution."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_studios.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_studios_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=True,
                        )

        # Assert
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"
        mock_sync_service.sync_studios.assert_called_once_with(
            job_id="test-job-123", force=True, progress_callback=mock_progress_callback
        )

    @pytest.mark.asyncio
    async def test_sync_job_with_partial_status(
        self, mock_settings, mock_progress_callback
    ):
        """Test sync job that returns partial status."""
        # Arrange
        partial_result = SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status=SyncStatus.PARTIAL,
            total_items=100,
            processed_items=100,
            created_items=20,
            updated_items=50,
            failed_items=5,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = partial_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                        )

        # Assert
        assert result["status"] == "partial"
        assert result["failed_items"] == 5
        assert result["success_rate"] == 0.95

    def test_register_sync_jobs(self):
        """Test registering sync job handlers."""
        # Arrange
        mock_job_service = Mock(spec=JobService)

        # Act
        register_sync_jobs(mock_job_service)

        # Assert
        assert mock_job_service.register_handler.call_count == 5
        mock_job_service.register_handler.assert_any_call(JobType.SYNC, sync_all_job)
        mock_job_service.register_handler.assert_any_call(
            JobType.SYNC_SCENES, sync_scenes_job
        )
        mock_job_service.register_handler.assert_any_call(
            JobType.SYNC_PERFORMERS, sync_performers_job
        )
        mock_job_service.register_handler.assert_any_call(
            JobType.SYNC_TAGS, sync_tags_job
        )
        mock_job_service.register_handler.assert_any_call(
            JobType.SYNC_STUDIOS, sync_studios_job
        )

    @pytest.mark.asyncio
    async def test_sync_job_with_enum_status_value(
        self, mock_settings, mock_progress_callback
    ):
        """Test handling of status with .value attribute."""
        # Arrange
        mock_status = Mock()
        mock_status.value = "custom_status"

        custom_result = SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status=mock_status,  # Mock with .value attribute
            total_items=10,
            processed_items=10,
            created_items=5,
            updated_items=5,
            failed_items=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = custom_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                        )

        # Assert
        assert result["status"] == "custom_status"

    @pytest.mark.asyncio
    async def test_sync_job_kwargs_handling(
        self, mock_settings, mock_sync_result, mock_progress_callback
    ):
        """Test that extra kwargs are handled properly."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = mock_sync_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act - passing extra kwargs
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=True,
                            extra_param="should_be_ignored",
                            another_param=123,
                        )

        # Assert - job should complete successfully despite extra kwargs
        assert result["job_id"] == "test-job-123"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_sync_job_progress_tracking(
        self, mock_settings, mock_progress_callback
    ):
        """Test that progress callbacks are properly invoked during sync."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()

        # Simulate progressive sync updates
        async def simulate_sync_all(
            job_id, force, progress_callback, cancellation_token
        ):
            # Simulate progress updates
            progress_callback(10, "Starting sync...")
            progress_callback(50, "Processing items...")
            progress_callback(90, "Finalizing...")
            progress_callback(100, "Complete")

            return SyncResult(
                job_id=job_id,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                status=SyncStatus.SUCCESS,
                total_items=100,
                processed_items=100,
                created_items=20,
                updated_items=50,
                failed_items=0,
            )

        mock_sync_service.sync_all.side_effect = simulate_sync_all

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            force=False,
                        )

        # Assert
        assert result["status"] == "success"
        # Verify progress callbacks were made
        assert mock_progress_callback.call_count == 4
        mock_progress_callback.assert_any_call(10, "Starting sync...")
        mock_progress_callback.assert_any_call(50, "Processing items...")
        mock_progress_callback.assert_any_call(90, "Finalizing...")
        mock_progress_callback.assert_any_call(100, "Complete")

    @pytest.mark.asyncio
    async def test_sync_job_database_error(self, mock_settings, mock_progress_callback):
        """Test sync job handling database connection errors."""
        # Arrange
        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                    # Simulate database connection error
                    mock_session.return_value.__aenter__.side_effect = Exception(
                        "Database connection failed"
                    )

                    # Act & Assert
                    with pytest.raises(Exception, match="Database connection failed"):
                        await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                        )

    @pytest.mark.asyncio
    async def test_sync_scenes_job_with_invalid_scene_ids(
        self, mock_settings, mock_progress_callback
    ):
        """Test sync_scenes job with invalid scene IDs."""
        # Arrange
        invalid_scene_ids = ["invalid1", "invalid2"]
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()

        # Simulate partial failure
        partial_result = SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status=SyncStatus.PARTIAL,
            total_items=2,
            processed_items=2,
            created_items=0,
            updated_items=0,
            failed_items=0,  # Start with 0, add_error will increment
        )
        partial_result.add_error("scene", "invalid1", "Scene not found in Stash")
        partial_result.add_error("scene", "invalid2", "Scene not found in Stash")

        mock_sync_service.sync_scenes.return_value = partial_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_scenes_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                            scene_ids=invalid_scene_ids,
                            force=False,
                        )

        # Assert
        assert (
            result["status"] == "completed_with_errors"
        )  # Changed from "partial" to match new error handling
        assert result["failed_items"] == 2
        assert result["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_sync_job_with_stash_service_error(
        self, mock_settings, mock_progress_callback
    ):
        """Test sync job handling Stash service initialization errors."""
        # Arrange
        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService") as mock_stash_service_class:
                # Simulate Stash service initialization error
                mock_stash_service_class.side_effect = Exception(
                    "Failed to connect to Stash"
                )

                # Act & Assert
                with pytest.raises(Exception, match="Failed to connect to Stash"):
                    await sync_all_job(
                        job_id="test-job-123",
                        progress_callback=mock_progress_callback,
                    )

    @pytest.mark.asyncio
    async def test_sync_job_with_failed_status(
        self, mock_settings, mock_progress_callback
    ):
        """Test sync job that completely fails."""
        # Arrange
        failed_result = SyncResult(
            job_id="test-job-123",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status=SyncStatus.FAILED,
            total_items=10,
            processed_items=10,
            created_items=0,
            updated_items=0,
            failed_items=10,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = failed_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                        )

        # Assert
        assert result["status"] == "failed"
        assert result["failed_items"] == 10
        assert result["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_sync_job_duration_calculation(
        self, mock_settings, mock_progress_callback
    ):
        """Test that duration is properly calculated in results."""
        # Arrange
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=45.5)

        timed_result = SyncResult(
            job_id="test-job-123",
            started_at=start_time,
            completed_at=end_time,
            status=SyncStatus.SUCCESS,
            total_items=100,
            processed_items=100,
            created_items=50,
            updated_items=50,
            failed_items=0,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()
        mock_sync_service.sync_all.return_value = timed_result

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Act
                        result = await sync_all_job(
                            job_id="test-job-123",
                            progress_callback=mock_progress_callback,
                        )

        # Assert
        assert result["duration_seconds"] == 45.5

    @pytest.mark.asyncio
    async def test_multiple_sync_job_types_error_handling(
        self, mock_settings, mock_progress_callback
    ):
        """Test error handling across different sync job types."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_sync_service = AsyncMock()

        # Different errors for different sync types
        mock_sync_service.sync_performers.side_effect = ValueError(
            "Invalid performer data"
        )
        mock_sync_service.sync_tags.side_effect = RuntimeError("Tag sync failed")
        mock_sync_service.sync_studios.side_effect = ConnectionError("Network error")

        with patch(
            "app.jobs.sync_jobs.load_settings_with_db_overrides",
            return_value=mock_settings,
        ):
            with patch("app.jobs.sync_jobs.StashService"):
                with patch("app.jobs.sync_jobs.SyncService") as mock_sync_service_class:
                    with patch("app.jobs.sync_jobs.AsyncSessionLocal") as mock_session:
                        # Setup mocks
                        mock_session.return_value.__aenter__.return_value = mock_db
                        mock_sync_service_class.return_value = mock_sync_service

                        # Test performers job
                        with pytest.raises(ValueError, match="Invalid performer data"):
                            await sync_performers_job(
                                job_id="test-job-1",
                                progress_callback=mock_progress_callback,
                            )

                        # Test tags job
                        with pytest.raises(RuntimeError, match="Tag sync failed"):
                            await sync_tags_job(
                                job_id="test-job-2",
                                progress_callback=mock_progress_callback,
                            )

                        # Test studios job
                        with pytest.raises(ConnectionError, match="Network error"):
                            await sync_studios_job(
                                job_id="test-job-3",
                                progress_callback=mock_progress_callback,
                            )
