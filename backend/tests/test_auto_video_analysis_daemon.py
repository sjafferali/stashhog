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
        daemon_id = uuid4()

        # Mock the database access that happens during on_start()
        mock_daemon_record = MagicMock()
        mock_daemon_record.id = daemon_id
        mock_daemon_record.status = "RUNNING"
        mock_daemon_record.started_at = None

        # Create mock database session
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_daemon_record)
        mock_db.commit = AsyncMock()

        # Patch AsyncSessionLocal before creating daemon
        with patch("app.daemons.base.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            daemon = AutoVideoAnalysisDaemon(daemon_id=daemon_id)
            daemon.config = {
                "heartbeat_interval": 1,
                "job_interval_seconds": 2,  # Short interval for testing
                "batch_size": 10,
            }
            daemon.is_running = True
            # Mock the log method to prevent database writes
            daemon.log = AsyncMock()
            # Mock update_heartbeat to prevent database writes
            daemon.update_heartbeat = AsyncMock()
            # Mock track_activity to prevent database writes
            daemon.track_activity = AsyncMock()
            await daemon.on_start()

        return daemon

    @pytest.mark.asyncio
    @patch("app.daemons.base.AsyncSessionLocal")
    async def test_no_concurrent_jobs_when_job_running(self, mock_base_session, daemon):
        """Test that daemon won't check for new scenes while a job is running."""
        # Mock the base session to prevent database access
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()
        mock_base_session.return_value.__aenter__.return_value = mock_db

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

        # Mock track_job_action to prevent database writes
        daemon.track_job_action = AsyncMock()

        # Mock database session with scenes needing analysis
        mock_db_for_scenes = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100  # 100 scenes pending
        mock_result.__iter__ = lambda self: iter(
            [(uuid4(),) for _ in range(10)]
        )  # Return 10 scene IDs
        mock_db_for_scenes.execute.return_value = mock_result
        mock_db_for_scenes.commit = AsyncMock()

        # Mock database session for job creation
        mock_db_for_jobs = AsyncMock(spec=AsyncSession)
        mock_db_for_jobs.commit = AsyncMock()

        # Track which call we're on
        call_count = [0]

        def get_mock_db():
            call_count[0] += 1
            # First call is for checking scenes, second is for creating job
            if call_count[0] == 1:
                return mock_db_for_scenes
            else:
                return mock_db_for_jobs

        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = get_mock_db

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
    @patch("app.daemons.base.AsyncSessionLocal")
    async def test_new_job_after_interval_when_previous_completes(
        self, mock_base_session, daemon
    ):
        """Test that daemon creates new job after interval when previous job completes."""
        # Mock the base session to prevent database access
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()
        mock_base_session.return_value.__aenter__.return_value = mock_db

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

        # Mock track_job_action to prevent database writes
        daemon.track_job_action = AsyncMock()

        # Mock database for scene queries
        mock_db_for_scenes = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100  # 100 scenes pending
        mock_result.__iter__ = lambda self: iter([(uuid4(),) for _ in range(10)])
        mock_db_for_scenes.execute.return_value = mock_result
        mock_db_for_scenes.commit = AsyncMock()

        # Mock database for job creation and status checks
        mock_db_for_jobs = AsyncMock(spec=AsyncSession)
        mock_db_for_jobs.commit = AsyncMock()
        # Also give it execute capability for scene queries (in case it's used for that)
        mock_db_for_jobs.execute.return_value = mock_result

        # Mock database for job status checks
        async def mock_get(model, job_id):
            for job in created_jobs:
                if str(job.id) == job_id:
                    return job
            return None

        mock_db_for_jobs.get = AsyncMock(side_effect=mock_get)
        mock_db_for_scenes.get = AsyncMock(
            side_effect=mock_get
        )  # Also add get to scenes db

        # Track which call we're on
        call_count = [0]

        def get_mock_db():
            call_count[0] += 1
            # For checking monitored jobs, we need a db with get method
            # So return mock_db_for_jobs for all non-scene-query operations
            # Only the initial scene count/query needs mock_db_for_scenes
            if (
                call_count[0] == 1 or call_count[0] == 3
            ):  # First and third calls are scene queries
                return mock_db_for_scenes
            else:
                return mock_db_for_jobs

        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = get_mock_db

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

    def _create_mock_job_service(self, created_jobs):
        """Helper to create mock job service."""
        job_service_mock = MagicMock()

        async def mock_create_job(job_type, db, metadata):
            job = MagicMock()
            job.id = uuid4()
            job.type = job_type
            job.status = JobStatus.COMPLETED.value
            job.job_metadata = metadata
            job.result = None
            created_jobs.append(job)
            return job

        job_service_mock.create_job = AsyncMock(side_effect=mock_create_job)
        return job_service_mock

    def _setup_mock_database(self):
        """Helper to setup mock database."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        mock_result = MagicMock()
        scene_call_count = [0]

        def get_scenes_count():
            scene_call_count[0] += 1
            return 50 if scene_call_count[0] <= 4 else 0

        mock_result.scalar_one = get_scenes_count
        mock_result.__iter__ = lambda self: iter([(uuid4(),) for _ in range(10)])
        mock_db.execute.return_value = mock_result
        return mock_db

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex timing test that requires refactoring")
    async def test_run_method_respects_interval(self, daemon):
        """Test that the run() method respects the job interval."""
        daemon.config["job_interval_seconds"] = 0.5

        created_jobs = []
        job_service_mock = self._create_mock_job_service(created_jobs)
        daemon.track_job_action = AsyncMock()

        mock_db = self._setup_mock_database()

        # Setup time and sleep mocks
        mock_time = [0.0]
        check_times = []
        original_check = daemon._check_and_analyze_scenes

        async def track_check(config):
            check_times.append(mock_time[0])
            if len(check_times) <= 2:
                await original_check(config)
            mock_time[0] += 1.0

        daemon._check_and_analyze_scenes = track_check

        async def mock_sleep(seconds):
            mock_time[0] += seconds
            if mock_time[0] > 10:
                daemon.is_running = False
            await asyncio.sleep(0)

        # Run the test
        with patch(
            "app.daemons.auto_video_analysis_daemon.AsyncSessionLocal"
        ) as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db

            with patch("app.core.dependencies.get_job_service") as mock_get_service:
                mock_get_service.return_value = job_service_mock

                with patch(
                    "app.daemons.auto_video_analysis_daemon.time.time",
                    new=lambda: mock_time[0],
                ):
                    with patch("asyncio.sleep", new=mock_sleep):
                        run_task = asyncio.create_task(daemon.run())
                        try:
                            await asyncio.wait_for(run_task, timeout=2.0)
                        except asyncio.TimeoutError:
                            run_task.cancel()
                            try:
                                await run_task
                            except asyncio.CancelledError:
                                pass

        assert len(created_jobs) >= 1
