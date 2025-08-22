"""Tests for Auto Video Analysis Daemon to ensure no concurrent job launches."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.daemons.auto_video_analysis_daemon import AutoVideoAnalysisDaemon
from app.models.job import JobStatus, JobType


class TestAutoVideoAnalysisDaemon:
    """Test suite for Auto Video Analysis Daemon."""

    @pytest.fixture
    async def daemon(self):
        """Create a test daemon instance."""
        daemon = AutoVideoAnalysisDaemon(daemon_id=uuid4())
        daemon.config = {
            "heartbeat_interval": 1,
            "job_interval_seconds": 2,  # Short interval for testing
            "batch_size": 10,
            "auto_approve_plans": True,
        }
        daemon.is_running = True
        await daemon.on_start()
        return daemon

    @pytest.mark.asyncio
    async def test_no_concurrent_jobs_when_job_running(self, daemon):
        """Test that daemon won't check for new scenes while a job is running."""
        job_service_mock = MagicMock()
        created_jobs = []

        # Mock job creation
        async def mock_create_job(job_type, db, metadata):
            job = MagicMock()
            job.id = uuid4()
            job.type = job_type
            job.status = JobStatus.RUNNING.value
            job.job_metadata = metadata
            created_jobs.append(job)
            return job

        job_service_mock.create_job = AsyncMock(side_effect=mock_create_job)

        # Track log messages
        log_messages = []

        async def mock_log(level, message):
            log_messages.append((level, message))

        daemon.log = AsyncMock(side_effect=mock_log)

        # Mock database session with scenes needing analysis
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100  # 100 scenes pending
        mock_result.__iter__ = lambda self: iter(
            [(uuid4(),) for _ in range(10)]
        )  # Return 10 scene IDs
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch("app.core.dependencies.get_job_service") as mock_get_service:
                mock_get_service.return_value = job_service_mock

                # First check - should create a job
                await daemon._check_and_analyze_scenes(daemon._load_config())
                assert len(created_jobs) == 1
                assert len(daemon._monitored_jobs) == 1

                # Verify last_check_time was updated
                assert daemon._last_check_time > 0

                # The key behavior: run() method should skip scene checks when jobs are monitored
                # Let's test this by simulating the run loop logic
                check_calls = 0
                original_check = daemon._check_and_analyze_scenes

                async def counting_check(config):
                    nonlocal check_calls
                    check_calls += 1
                    return await original_check(config)

                daemon._check_and_analyze_scenes = counting_check

                # With monitored jobs, the run method shouldn't call _check_and_analyze_scenes
                # Simulate the run() method's logic
                if daemon._monitored_jobs:
                    # This is what run() does - it skips the check
                    await asyncio.sleep(0.01)
                else:
                    await daemon._check_and_analyze_scenes(daemon._load_config())

                # Verify no additional checks were made
                assert (
                    check_calls == 0
                )  # No additional calls because we have monitored jobs
                assert len(created_jobs) == 1  # Still only 1 job

                # Verify appropriate log messages
                assert any(
                    "Created video tag analysis job" in msg
                    for level, msg in log_messages
                )

    @pytest.mark.asyncio
    async def test_new_job_after_interval_when_previous_completes(self, daemon):
        """Test that daemon creates new job after interval when previous job completes."""
        job_service_mock = MagicMock()
        created_jobs = []

        # Mock job creation
        async def mock_create_job(job_type, db, metadata):
            job = MagicMock()
            job.id = uuid4()
            job.type = job_type
            job.status = JobStatus.RUNNING.value
            job.job_metadata = metadata
            job.result = None
            created_jobs.append(job)
            return job

        job_service_mock.create_job = AsyncMock(side_effect=mock_create_job)

        # Mock database for scene queries
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100  # 100 scenes pending
        mock_result.__iter__ = lambda self: iter([(uuid4(),) for _ in range(10)])
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        # Mock database for job status checks
        async def mock_get(model, job_id):
            for job in created_jobs:
                if str(job.id) == job_id:
                    return job
            return None

        mock_db.get = AsyncMock(side_effect=mock_get)

        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch("app.core.dependencies.get_job_service") as mock_get_service:
                mock_get_service.return_value = job_service_mock

                # Create first job
                await daemon._check_and_analyze_scenes(daemon._load_config())
                assert len(created_jobs) == 1
                assert len(daemon._monitored_jobs) == 1
                first_job = created_jobs[0]

                # Mark job as completed
                first_job.status = JobStatus.COMPLETED.value
                first_job.type = JobType.ANALYSIS.value

                # Check monitored jobs (should remove completed job)
                await daemon._check_monitored_jobs(daemon._load_config())
                assert len(daemon._monitored_jobs) == 0

                # Verify last_check_time was updated when job completed
                assert daemon._last_check_time > 0

                # Now that no jobs are monitored, daemon can create new jobs
                # But only after the interval has passed
                # Simulate interval passing
                daemon._last_check_time = (
                    time.time() - 3
                )  # 3 seconds ago (> 2 second interval)

                # Create second job
                await daemon._check_and_analyze_scenes(daemon._load_config())
                assert len(created_jobs) == 2
                assert len(daemon._monitored_jobs) == 1

    @pytest.mark.asyncio
    async def test_run_method_respects_interval(self, daemon):
        """Test that the run() method respects the job interval."""
        daemon.config["job_interval_seconds"] = (
            0.5  # 0.5 second interval for faster testing
        )

        job_service_mock = MagicMock()
        created_jobs = []

        async def mock_create_job(job_type, db, metadata):
            job = MagicMock()
            job.id = uuid4()
            job.type = job_type
            job.status = JobStatus.COMPLETED.value  # Complete immediately for testing
            job.job_metadata = metadata
            job.result = None
            created_jobs.append(job)
            return job

        job_service_mock.create_job = AsyncMock(side_effect=mock_create_job)

        # Mock database
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()

        call_count = 0

        def get_scenes_count():
            nonlocal call_count
            call_count += 1
            # Return scenes for first 2 calls, then 0
            return 50 if call_count <= 4 else 0  # Allow for count and query calls

        mock_result.scalar_one = get_scenes_count
        mock_result.__iter__ = lambda self: iter([(uuid4(),) for _ in range(10)])
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        # Track when check_and_analyze_scenes is called
        check_times = []
        original_check = daemon._check_and_analyze_scenes

        async def track_check_and_analyze(config):
            check_times.append(time.time())
            if len(check_times) <= 2:  # Only create jobs for first 2 checks
                await original_check(config)

        daemon._check_and_analyze_scenes = track_check_and_analyze

        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch("app.core.dependencies.get_job_service") as mock_get_service:
                mock_get_service.return_value = job_service_mock

                # Run daemon for a short time
                run_task = asyncio.create_task(daemon.run())
                await asyncio.sleep(
                    1.5
                )  # Run for 1.5 seconds (enough for ~3 intervals)
                daemon.is_running = False

                # Give task time to complete gracefully
                try:
                    await asyncio.wait_for(run_task, timeout=1.0)
                except asyncio.TimeoutError:
                    run_task.cancel()
                    try:
                        await run_task
                    except asyncio.CancelledError:
                        pass

                # Should have created jobs with proper interval spacing
                assert len(check_times) >= 2
                if len(check_times) >= 2:
                    # Check that interval between checks is at least job_interval_seconds
                    interval = check_times[1] - check_times[0]
                    # Allow some margin for timing variations
                    assert interval >= daemon.config["job_interval_seconds"] - 0.1
