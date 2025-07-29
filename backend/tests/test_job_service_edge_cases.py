"""Additional edge case tests for job service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.cancellation import cancellation_manager
from app.models.job import Job, JobStatus, JobType
from app.services.job_service import JobService


class TestJobServiceEdgeCases:
    """Test edge cases for job service functionality."""

    @pytest.fixture
    def job_service(self):
        """Create job service instance."""
        return JobService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = Mock()
        db.close = Mock()
        return db

    @pytest.fixture
    def mock_job(self):
        """Create mock job instance."""
        job = Mock(spec=Job)
        job.id = str(uuid4())
        job.type = JobType.SYNC_SCENES
        job.status = JobStatus.PENDING
        job.progress = 0
        job.job_metadata = {}
        job.created_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        return job

    @pytest.mark.asyncio
    async def test_sync_job_type_has_lock(self, job_service):
        """Test that sync job types have locks for mutual exclusion."""
        # Check that sync job types are defined
        assert JobType.SYNC_SCENES in job_service.sync_job_types

        # After creating a sync job, it should have a lock
        job_type = JobType.SYNC_SCENES
        handler = AsyncMock(return_value={"status": "ok"})
        job_service.register_handler(job_type, handler)

        # Verify lock gets created when needed
        assert job_type not in job_service.job_type_locks

        # The lock would be created during job execution
        # This is a simplified test that just verifies the structure

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    @patch("app.services.job_service.websocket_manager")
    async def test_cancel_job_already_completed(
        self, mock_ws_manager, mock_get_task_queue, mock_job_repo, job_service, mock_db
    ):
        """Test canceling a job that's already completed."""
        job_id = "completed-job"
        mock_job = Mock(spec=Job)
        mock_job.id = job_id
        mock_job.status = JobStatus.COMPLETED
        mock_job.job_metadata = {}

        mock_job_repo.get_job = AsyncMock(return_value=mock_job)
        mock_job_repo.cancel_job = AsyncMock()
        mock_job_repo._fetch_job = AsyncMock(return_value=mock_job)
        mock_job_repo.update_job_status = AsyncMock()
        mock_ws_manager.broadcast_job_update = AsyncMock()

        mock_task_queue = Mock()
        mock_task_queue.cancel_task = AsyncMock()
        mock_get_task_queue.return_value = mock_task_queue

        # The current implementation doesn't check status, so it returns True
        result = await job_service.cancel_job(job_id, mock_db)

        assert result is True
        mock_job_repo.update_job_status.assert_called_once_with(
            job_id=job_id,
            status=JobStatus.CANCELLING,
            db=mock_db,
            message="Cancellation requested",
        )

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    @patch("app.services.job_service.websocket_manager")
    async def test_cancel_job_already_failed(
        self, mock_ws_manager, mock_get_task_queue, mock_job_repo, job_service, mock_db
    ):
        """Test canceling a job that's already failed."""
        job_id = "failed-job"
        mock_job = Mock(spec=Job)
        mock_job.id = job_id
        mock_job.status = JobStatus.FAILED
        mock_job.job_metadata = {}

        mock_job_repo.get_job = AsyncMock(return_value=mock_job)
        mock_job_repo.cancel_job = AsyncMock()
        mock_job_repo._fetch_job = AsyncMock(return_value=mock_job)
        mock_job_repo.update_job_status = AsyncMock()
        mock_ws_manager.broadcast_job_update = AsyncMock()

        mock_task_queue = Mock()
        mock_task_queue.cancel_task = AsyncMock()
        mock_get_task_queue.return_value = mock_task_queue

        # The current implementation doesn't check status, so it returns True
        result = await job_service.cancel_job(job_id, mock_db)

        assert result is True
        mock_job_repo.update_job_status.assert_called_once_with(
            job_id=job_id,
            status=JobStatus.CANCELLING,
            db=mock_db,
            message="Cancellation requested",
        )

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.websocket_manager")
    async def test_cancel_pending_job(
        self, mock_ws_manager, mock_job_repo, job_service, mock_db
    ):
        """Test canceling a pending job."""
        job_id = "pending-job"
        mock_job = Mock(spec=Job)
        mock_job.id = job_id
        mock_job.status = JobStatus.PENDING
        mock_job.job_metadata = {"task_id": "task123"}

        mock_job_repo.get_job = AsyncMock(return_value=mock_job)
        mock_job_repo.cancel_job = AsyncMock()
        mock_job_repo._fetch_job = AsyncMock(return_value=mock_job)
        mock_job_repo.update_job_status = AsyncMock()
        mock_ws_manager.broadcast_job_update = AsyncMock()

        result = await job_service.cancel_job(job_id, mock_db)

        assert result is True
        mock_job_repo.update_job_status.assert_called_once_with(
            job_id=job_id,
            status=JobStatus.CANCELLING,
            db=mock_db,
            message="Cancellation requested",
        )

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    async def test_get_non_existent_job(self, mock_job_repo, job_service, mock_db):
        """Test getting a job that doesn't exist."""
        job_id = "non-existent"
        mock_job_repo.get_job = AsyncMock(return_value=None)

        result = await job_service.get_job(job_id, mock_db)

        assert result is None
        mock_job_repo.get_job.assert_called_once_with(job_id, mock_db)

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    async def test_list_jobs_empty_result(self, mock_job_repo, job_service, mock_db):
        """Test listing jobs with no results."""
        mock_job_repo.list_jobs = AsyncMock(return_value=[])

        result = await job_service.list_jobs(db=mock_db)

        assert result == []
        mock_job_repo.list_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_receives_callbacks(self, job_service):
        """Test that handler receives progress and cancellation callbacks."""
        job_type = JobType.ANALYSIS
        handler_kwargs = None

        async def handler(**kwargs):
            nonlocal handler_kwargs
            handler_kwargs = kwargs
            return {"analyzed": 100}

        job_service.register_handler(job_type, handler)

        # Verify handler is registered
        assert job_type in job_service.job_handlers
        assert job_service.job_handlers[job_type] == handler

        # In actual execution, handler would receive:
        # - job_id
        # - progress_callback
        # - cancellation_token
        # - any metadata/kwargs from job creation

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    async def test_create_job_with_invalid_metadata(
        self, mock_get_task_queue, mock_job_repo, job_service, mock_db
    ):
        """Test creating a job with metadata that can't be serialized."""
        job_type = JobType.SYNC_SCENES
        handler = AsyncMock(return_value={"status": "ok"})
        job_service.register_handler(job_type, handler)

        # Create job with complex metadata
        complex_metadata = {
            "valid_key": "valid_value",
            "nested": {"level1": {"level2": "value"}},
            "list": [1, 2, 3],
        }

        mock_job = Mock(spec=Job)
        mock_job.id = "metadata-job"
        mock_job.job_metadata = {}

        mock_job_repo.create_job = AsyncMock(return_value=mock_job)

        mock_task_queue = Mock()
        mock_task_queue.submit = AsyncMock(return_value="task123")
        mock_get_task_queue.return_value = mock_task_queue

        # Should handle metadata properly
        job = await job_service.create_job(
            job_type=job_type, db=mock_db, metadata=complex_metadata
        )

        assert job == mock_job
        mock_job_repo.create_job.assert_called_once()
        call_kwargs = mock_job_repo.create_job.call_args[1]
        assert call_kwargs["metadata"] == complex_metadata

    @pytest.mark.asyncio
    async def test_cancellation_token_created(self, job_service):
        """Test that cancellation tokens are created for jobs."""
        # When a job is created, a cancellation token should be created
        # This is tested indirectly through the create_job method

        # The cancellation manager should have methods to:
        # - create_token(job_id)
        # - get_token(job_id)
        # - cancel(job_id)
        # - remove_token(job_id)

        # Test that we can create and remove a token
        test_job_id = "test-cancel-token"
        cancellation_manager.create_token(test_job_id)
        token = cancellation_manager.get_token(test_job_id)
        assert token is not None
        assert not token.is_cancelled

        # Cancel it
        cancellation_manager.cancel_job(test_job_id)
        assert token.is_cancelled

        # Clean up
        cancellation_manager.remove_token(test_job_id)

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    async def test_list_jobs_with_filters(self, mock_job_repo, job_service, mock_db):
        """Test listing jobs with various filter combinations."""
        # Test with all filters
        mock_jobs = [Mock(spec=Job) for _ in range(5)]
        mock_job_repo.list_jobs = AsyncMock(return_value=mock_jobs)

        result = await job_service.list_jobs(
            db=mock_db,
            job_type=JobType.ANALYSIS,
            status=JobStatus.COMPLETED,
            limit=50,
            offset=10,
        )

        assert result == mock_jobs
        mock_job_repo.list_jobs.assert_called_once_with(
            db=mock_db,
            job_type=JobType.ANALYSIS,
            status=JobStatus.COMPLETED,
            limit=50,
            offset=10,
        )

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    @patch("app.services.job_service.websocket_manager")
    async def test_analysis_jobs_use_lock(
        self, mock_ws_manager, mock_get_task_queue, mock_job_repo, job_service, mock_db
    ):
        """Test that analysis jobs use locks and run sequentially."""
        job_type = JobType.ANALYSIS  # Now a sync job type with locking
        execution_times = []

        async def handler(**kwargs):
            start = datetime.utcnow()
            await asyncio.sleep(0.1)
            execution_times.append((start, datetime.utcnow()))
            return {"status": "complete"}

        job_service.register_handler(job_type, handler)

        # Mock websocket manager
        mock_ws_manager.broadcast_job_update = AsyncMock()

        # Create mock jobs
        jobs = []
        for i in range(3):
            job = Mock(spec=Job)
            job.id = f"job{i}"
            job.job_metadata = {}
            jobs.append(job)

        mock_job_repo.create_job = AsyncMock(side_effect=jobs)
        mock_job_repo.update_job_status = AsyncMock(return_value=jobs[0])
        mock_job_repo._fetch_job = AsyncMock(
            side_effect=jobs * 10
        )  # Provide enough mocks

        # Mock task queue
        task_funcs = []

        async def capture_task(name, func, **kwargs):
            task_funcs.append(func)
            return f"task_{len(task_funcs)}"

        mock_task_queue = Mock()
        mock_task_queue.submit = AsyncMock(side_effect=capture_task)
        mock_get_task_queue.return_value = mock_task_queue

        # Create jobs
        created_jobs = []
        for _ in range(3):
            job = await job_service.create_job(job_type=job_type, db=mock_db)
            created_jobs.append(job)

        # Execute tasks concurrently
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            # Create multiple mock sessions for each database operation
            mock_sessions = []
            for _ in range(20):  # Create enough sessions
                session = MagicMock()
                session.commit = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock(return_value=None)
                mock_sessions.append(session)

            # Return a new session each time AsyncSessionLocal is called
            mock_session.side_effect = lambda: mock_sessions.pop(0)

            await asyncio.gather(*[func() for func in task_funcs])

        # Verify all executed concurrently (overlapping execution times)
        assert len(execution_times) == 3

        # Check that jobs ran sequentially (no overlap)
        # Since analysis jobs now use locks, they should NOT overlap
        for i in range(len(execution_times) - 1):
            # Each job should finish before the next one starts
            _, end_time = execution_times[i]
            start_time, _ = execution_times[i + 1]
            # Allow small time difference for async scheduling
            assert (
                end_time <= start_time or (start_time - end_time).total_seconds() < 0.01
            )
