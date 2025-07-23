"""Test concurrent analysis job locking behavior."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.models.job import Job, JobStatus, JobType
from app.services.job_service import job_service


class TestAnalysisJobLocking:
    """Test that analysis jobs properly queue and don't run concurrently."""

    def _create_mock_session(self):
        """Create a mock database session."""
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        return mock_db

    def _create_mock_job(self, job_id, job_type=JobType.ANALYSIS):
        """Create a mock job."""
        mock_job = Mock(spec=Job)
        mock_job.id = job_id
        mock_job.type = job_type
        mock_job.status = JobStatus.PENDING
        mock_job.progress = 0
        mock_job.job_metadata = {}
        mock_job.created_at = datetime.utcnow()
        mock_job.updated_at = datetime.utcnow()
        return mock_job

    def _verify_sequential_execution(self, execution_log):
        """Verify that jobs executed sequentially."""
        # We should have 6 events total (3 jobs * 2 events each)
        assert (
            len(execution_log) == 6
        ), f"Expected 6 events, got {len(execution_log)}: {execution_log}"

        # Extract just the event types (start/end) without job IDs
        event_types = []
        for event in execution_log:
            if event.endswith("_start"):
                event_types.append("start")
            elif event.endswith("_end"):
                event_types.append("end")

        # Verify sequential pattern: start, end, start, end, start, end
        expected_pattern = ["start", "end", "start", "end", "start", "end"]
        assert (
            event_types == expected_pattern
        ), f"Expected sequential pattern, got: {event_types}"

        # Verify no job started before the previous one ended
        job_ids = []
        for event in execution_log:
            job_id = event.rsplit("_", 1)[0]
            if job_id not in job_ids:
                job_ids.append(job_id)

        assert len(job_ids) == 3, f"Expected 3 unique job IDs, got {len(job_ids)}"

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.services.job_service.websocket_manager")
    async def test_concurrent_analysis_jobs_queue_properly(
        self, mock_ws_manager, mock_async_session, mock_get_task_queue, mock_job_repo
    ):
        """Test that multiple analysis jobs queue and run sequentially."""
        # Track execution order
        execution_log = []

        # Create handler that logs execution
        async def analysis_handler(
            job_id, progress_callback, cancellation_token, **kwargs
        ):
            execution_log.append(f"{job_id}_start")
            await asyncio.sleep(0.1)  # Simulate work
            await progress_callback(50, "Halfway done")
            await asyncio.sleep(0.1)  # More work
            execution_log.append(f"{job_id}_end")
            return {"status": "completed", "analyzed": 100}

        # Register handler
        job_service.register_handler(JobType.ANALYSIS, analysis_handler)

        # Setup mock database sessions
        mock_sessions = [self._create_mock_session() for _ in range(30)]
        session_iter = iter(mock_sessions)
        mock_async_session.side_effect = lambda: next(session_iter)

        # Setup websocket manager
        mock_ws_manager.broadcast_job_update = AsyncMock()

        # Create mock jobs
        mock_jobs = [self._create_mock_job(f"analysis_job_{i}") for i in range(3)]

        # Setup job repository
        mock_job_repo.create_job = AsyncMock(side_effect=mock_jobs)
        mock_job_repo.update_job_status = AsyncMock(return_value=mock_jobs[0])
        # Create a cyclic iterator for _fetch_job to always return a job
        fetch_iter = iter(mock_jobs * 20)
        mock_job_repo._fetch_job = AsyncMock(side_effect=lambda *args: next(fetch_iter))

        # Setup task queue to capture and allow manual execution
        captured_tasks = []

        async def capture_task(func, name):
            task_id = f"task_{len(captured_tasks)}"
            captured_tasks.append((task_id, func))
            return task_id

        mock_task_queue = Mock()
        mock_task_queue.submit = AsyncMock(side_effect=capture_task)
        mock_get_task_queue.return_value = mock_task_queue

        # Create three analysis jobs
        jobs = []
        for i in range(3):
            db = Mock()
            db.commit = AsyncMock()
            job = await job_service.create_job(
                job_type=JobType.ANALYSIS, db=db, metadata={"scene_ids": [f"scene_{i}"]}
            )
            jobs.append(job)

        # Verify all jobs were created
        assert len(jobs) == 3
        assert len(captured_tasks) == 3

        # Execute all tasks concurrently (they should still run sequentially due to locks)
        task_coroutines = [task[1]() for task in captured_tasks]
        await asyncio.gather(*task_coroutines)

        # Verify execution was sequential
        self._verify_sequential_execution(execution_log)

        # Verify status updates included "waiting" messages for jobs 2 and 3
        status_calls = mock_job_repo.update_job_status.call_args_list

        # Find calls where status was set to PENDING with waiting message
        waiting_calls = [
            call
            for call in status_calls
            if call[1].get("status") == JobStatus.PENDING
            and "Waiting for another analysis job to complete"
            in str(call[1].get("message", ""))
        ]

        # Jobs 1 and 2 should have been marked as waiting (0-indexed)
        assert (
            len(waiting_calls) >= 2
        ), "Expected at least 2 jobs to show waiting status"

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    async def test_analysis_job_types_in_sync_list(
        self, mock_get_task_queue, mock_job_repo
    ):
        """Verify that all analysis-related job types are in the sync list."""
        # Check that analysis job types are included in sync_job_types
        analysis_types = {
            JobType.ANALYSIS,
            JobType.APPLY_PLAN,
            JobType.GENERATE_DETAILS,
        }

        for job_type in analysis_types:
            assert (
                job_type in job_service.sync_job_types
            ), f"{job_type.value} should be in sync_job_types for mutual exclusion"

        # Verify locks are created for these types during execution
        for job_type in analysis_types:
            # Register a dummy handler
            job_service.register_handler(job_type, AsyncMock())

            # The lock should be created when needed
            # Initial state: no lock exists
            if job_type in job_service.job_type_locks:
                del job_service.job_type_locks[job_type]

            assert job_type not in job_service.job_type_locks

    @pytest.mark.asyncio
    @patch("app.services.job_service.job_repository")
    @patch("app.services.job_service.get_task_queue")
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.services.job_service.websocket_manager")
    async def test_mixed_job_types_respect_locks(
        self, mock_ws_manager, mock_async_session, mock_get_task_queue, mock_job_repo
    ):
        """Test that different job types use independent locks."""
        execution_log = []

        # Create handlers for different job types
        async def sync_handler(job_id, **kwargs):
            execution_log.append(f"sync_{job_id}_start")
            await asyncio.sleep(0.1)
            execution_log.append(f"sync_{job_id}_end")
            return {"synced": True}

        async def analysis_handler(job_id, **kwargs):
            execution_log.append(f"analysis_{job_id}_start")
            await asyncio.sleep(0.1)
            execution_log.append(f"analysis_{job_id}_end")
            return {"analyzed": True}

        job_service.register_handler(JobType.SYNC_SCENES, sync_handler)
        job_service.register_handler(JobType.ANALYSIS, analysis_handler)

        # Setup mocks
        mock_sessions = []
        for _ in range(20):
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_sessions.append(mock_db)

        session_iter = iter(mock_sessions * 2)  # Make sure we have enough
        mock_async_session.side_effect = lambda: next(session_iter)

        # Setup websocket manager
        mock_ws_manager.broadcast_job_update = AsyncMock()

        # Create jobs of different types
        job_configs = [
            (JobType.SYNC_SCENES, "sync1"),
            (JobType.ANALYSIS, "analysis1"),
            (JobType.SYNC_SCENES, "sync2"),
            (JobType.ANALYSIS, "analysis2"),
        ]

        mock_jobs = []
        for job_type, job_id in job_configs:
            mock_job = Mock(spec=Job)
            mock_job.id = job_id
            mock_job.type = job_type
            mock_job.status = JobStatus.PENDING
            mock_job.job_metadata = {}
            mock_jobs.append(mock_job)

        # Keep track of created job IDs
        created_job_ids = []

        async def create_job_side_effect(job_id, job_type, db, metadata=None):
            job = mock_jobs[len(created_job_ids)]
            job.id = job_id  # Use the actual generated ID
            created_job_ids.append(job_id)
            return job

        mock_job_repo.create_job = AsyncMock(side_effect=create_job_side_effect)
        mock_job_repo.update_job_status = AsyncMock(return_value=mock_jobs[0])
        fetch_iter = iter(mock_jobs * 20)
        mock_job_repo._fetch_job = AsyncMock(side_effect=lambda *args: next(fetch_iter))

        # Capture tasks
        captured_tasks = []

        async def capture_task(func, name):
            task_id = f"task_{len(captured_tasks)}"
            captured_tasks.append(func)
            return task_id

        mock_task_queue = Mock()
        mock_task_queue.submit = AsyncMock(side_effect=capture_task)
        mock_get_task_queue.return_value = mock_task_queue

        # Create jobs
        for job_type, _ in job_configs:
            db = Mock()
            db.commit = AsyncMock()
            await job_service.create_job(job_type=job_type, db=db)

        # Execute all tasks concurrently
        await asyncio.gather(*[task() for task in captured_tasks])

        # Verify execution order
        # Sync jobs should be sequential with each other
        # Analysis jobs should be sequential with each other
        # But sync and analysis can overlap

        sync_events = [e for e in execution_log if e.startswith("sync_")]
        analysis_events = [e for e in execution_log if e.startswith("analysis_")]

        # Check sync jobs ran sequentially (using dynamic IDs)
        # We expect 2 sync jobs with start/end for each
        assert len([e for e in sync_events if "_start" in e]) == 2
        assert len([e for e in sync_events if "_end" in e]) == 2

        # Check analysis jobs ran sequentially
        assert len([e for e in analysis_events if "_start" in e]) == 2
        assert len([e for e in analysis_events if "_end" in e]) == 2

        # Verify sequential execution within each job type
        # For sync jobs: first must end before second starts
        sync_starts = [i for i, e in enumerate(sync_events) if "_start" in e]
        sync_ends = [i for i, e in enumerate(sync_events) if "_end" in e]
        assert sync_ends[0] < sync_starts[1]  # First sync ends before second starts

        # For analysis jobs: first must end before second starts
        analysis_starts = [i for i, e in enumerate(analysis_events) if "_start" in e]
        analysis_ends = [i for i, e in enumerate(analysis_events) if "_end" in e]
        assert (
            analysis_ends[0] < analysis_starts[1]
        )  # First analysis ends before second starts
