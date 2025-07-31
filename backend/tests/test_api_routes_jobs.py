"""Tests for job API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.job import Job, JobStatus, JobType


def create_job_mock(**kwargs):
    """Create a job mock with all required fields."""
    job = Mock(spec=Job)
    # Set defaults
    job.id = kwargs.get("id", str(uuid4()))
    job.type = kwargs.get("type", JobType.SYNC_SCENES)
    job.status = kwargs.get("status", JobStatus.RUNNING)
    job.progress = kwargs.get("progress", 0)
    job.message = kwargs.get("message", "Processing...")
    job.result = kwargs.get("result", None)
    job.error = kwargs.get("error", None)
    job.created_at = kwargs.get("created_at", datetime.utcnow())
    job.updated_at = kwargs.get("updated_at", datetime.utcnow())
    job.started_at = kwargs.get("started_at", None)
    job.completed_at = kwargs.get("completed_at", None)
    job.job_metadata = kwargs.get("job_metadata", {})
    job.total_items = kwargs.get("total_items", None)
    job.processed_items = kwargs.get("processed_items", 0)
    return job


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = AsyncMock()
    db.execute = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test_user", "email": "test@example.com"}


@pytest.fixture
def mock_job_service():
    """Mock job service."""
    service = Mock()
    service.get_active_jobs = AsyncMock(return_value=[])
    service.get_job = AsyncMock(return_value=None)
    service.cancel_job = AsyncMock(return_value=True)
    service.enqueue = AsyncMock(return_value="test-job-id")
    service.create_job = AsyncMock()
    # Don't set get_job_logs by default - let tests set it when needed
    return service


@pytest.fixture
def client(mock_db, mock_user, mock_job_service):
    """Test client with mocked dependencies."""
    from app.core.dependencies import (
        get_analysis_service,
        get_job_service,
        get_openai_client,
        get_stash_client,
        get_stash_service,
        get_sync_service,
    )

    # Create additional mock services that might be needed
    mock_stash_client = Mock()
    mock_openai_client = Mock()
    mock_analysis_service = Mock()
    mock_sync_service = Mock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_stash_client] = lambda: mock_stash_client
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_client
    app.dependency_overrides[get_openai_client] = lambda: mock_openai_client
    app.dependency_overrides[get_analysis_service] = lambda: mock_analysis_service
    app.dependency_overrides[get_sync_service] = lambda: mock_sync_service

    # Skip lifespan events in tests to avoid initialization issues
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_job():
    """Create a mock job object."""
    job = Mock(spec=Job)
    job.id = str(uuid4())
    job.type = JobType.SYNC_SCENES
    job.status = JobStatus.RUNNING
    job.progress = 50.0
    job.message = "Processing..."
    job.result = None
    job.error = None
    job.created_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    job.started_at = datetime.utcnow()
    job.completed_at = None
    job.job_metadata = {"source": "api"}
    job.total_items = 100  # Add missing field
    job.processed_items = 50  # Add missing field
    job.to_dict = Mock(
        return_value={
            "id": job.id,
            "type": job.type.value,
            "status": job.status.value,
            "progress": job.progress,
            "message": job.message,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "metadata": job.job_metadata,
        }
    )
    return job


class TestJobRoutes:
    """Test job API routes."""

    def test_list_jobs(self, client, mock_db, mock_job, mock_job_service):
        """Test listing jobs."""
        # Mock job service already set up by fixture
        mock_job_service.get_active_jobs = AsyncMock(return_value=[])

        # Mock database query
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_job]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["id"] == str(mock_job.id)

    def test_list_jobs_filter_by_type(
        self, client, mock_db, mock_job, mock_job_service
    ):
        """Test filtering jobs by type."""
        # Mock job service already set up by fixture
        mock_job_service.get_active_jobs = AsyncMock(return_value=[])

        # Mock database query
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_job]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/api/jobs?job_type={JobType.SYNC_SCENES.value}")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1

    def test_list_jobs_filter_by_status(
        self, client, mock_db, mock_job, mock_job_service
    ):
        """Test filtering jobs by status."""
        # Mock job service already set up by fixture
        mock_job_service.get_active_jobs = AsyncMock(return_value=[])

        # Mock database query
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_job]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/api/jobs?status={JobStatus.RUNNING.value}")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1

    def test_get_job(self, client, mock_db, mock_job, mock_job_service):
        """Test getting a single job."""
        # Mock job service to return the job
        mock_job_service.get_job = AsyncMock(return_value=mock_job)
        # Add get_job_logs to prevent error when hasattr checks for it
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        response = client.get(f"/api/jobs/{mock_job.id}")

        # Debug the response if it fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_job.id)
        assert data["type"] == "sync_scenes"  # No longer mapped
        assert data["status"] == mock_job.status.value

    def test_get_job_not_found(self, client, mock_db, mock_job_service):
        """Test getting a job that doesn't exist."""
        # Mock job service to return None
        mock_job_service.get_job = AsyncMock(return_value=None)

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/jobs/nonexistent-id")

        assert response.status_code == 404

    def test_cancel_job(self, client, mock_db, mock_job, mock_job_service):
        """Test canceling a job."""
        # Mock job service to return the job and successful cancellation
        mock_job_service.get_job = AsyncMock(return_value=mock_job)
        mock_job_service.cancel_job = AsyncMock(return_value=True)

        response = client.post(f"/api/jobs/{mock_job.id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_job_service.cancel_job.assert_called_once_with(str(mock_job.id), mock_db)

    def test_retry_job(self, client, mock_db, mock_job_service):
        """Test retrying a failed job."""
        # Create a failed job to retry
        failed_job = Mock(spec=Job)
        failed_job.id = "test-id"
        failed_job.type = JobType.SYNC_SCENES
        failed_job.status = JobStatus.FAILED
        failed_job.job_metadata = {"source": "api", "param1": "value1"}
        failed_job.error = "Previous failure"

        # Mock database query to return the failed job
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = failed_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock job service to create a new job
        new_job_id = str(uuid4())
        new_job = Mock(spec=Job, id=new_job_id)
        mock_job_service.create_job = AsyncMock(return_value=new_job)

        response = client.post("/api/jobs/test-id/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_job_id"] == new_job_id
        assert "retried as new job" in data["message"]

        # Verify the job service was called correctly
        mock_job_service.create_job.assert_called_once_with(
            job_type=failed_job.type, metadata=failed_job.job_metadata, db=mock_db
        )

    def test_get_job_logs(self, client, mock_job_service):
        """Test getting job logs - endpoint doesn't exist."""
        # Mock the job service to return None
        mock_job_service.get_job = AsyncMock(return_value=None)
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        # This endpoint doesn't exist in the actual routes
        response = client.get("/api/jobs/test-id/logs")

        assert response.status_code == 404

    def test_job_stats(self, client, mock_job_service):
        """Test getting job statistics - endpoint doesn't exist."""
        # Mock the job service to return None
        mock_job_service.get_job = AsyncMock(return_value=None)
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        # This endpoint doesn't exist in the actual routes
        response = client.get("/api/jobs/stats")

        # Since /stats could be interpreted as a job_id, it may return 404 or 500
        assert response.status_code in [404, 500]

    def test_create_sync_job(self, client):
        """Test creating a sync job - endpoint doesn't exist."""
        # This endpoint doesn't exist in the actual routes
        response = client.post(
            "/api/jobs",
            json={"type": JobType.SYNC_SCENES.value, "metadata": {"full_sync": True}},
        )

        assert (
            response.status_code == 405
        )  # Method not allowed since POST is not defined

    def test_job_progress_updates(self, client, mock_job_service):
        """Test job progress endpoint - endpoint doesn't exist."""
        # Mock the job service to return None for non-existent job
        mock_job_service.get_job = AsyncMock(return_value=None)

        # This endpoint doesn't exist in the actual routes
        response = client.get("/api/jobs/test-id/progress")

        assert response.status_code == 404

    def test_job_lifecycle_completed(self, client, mock_db, mock_job_service):
        """Test complete job lifecycle from pending to completed."""
        # Create a job that transitions through states
        job_id = str(uuid4())

        # Add get_job_logs mock for all get_job calls
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        # Initial state: pending
        pending_job = create_job_mock(
            id=job_id,
            type=JobType.SYNC_SCENES,
            status=JobStatus.PENDING,
            progress=0,
            job_metadata={"source": "api"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_job_service.get_job = AsyncMock(return_value=pending_job)

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0

        # Transition to running
        running_job = create_job_mock(
            id=job_id,
            type=JobType.SYNC_SCENES,
            status=JobStatus.RUNNING,
            progress=50,
            job_metadata={
                "source": "api",
                "last_message": "Processing scenes...",
            },
            created_at=pending_job.created_at,
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            total_items=100,
            processed_items=50,
        )

        mock_job_service.get_job = AsyncMock(return_value=running_job)

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress"] == 50

        # Transition to completed
        completed_job = create_job_mock(
            id=job_id,
            type=JobType.SYNC_SCENES,
            status=JobStatus.COMPLETED,
            progress=100,
            job_metadata={"source": "api"},
            created_at=pending_job.created_at,
            updated_at=datetime.utcnow(),
            started_at=running_job.started_at,
            completed_at=datetime.utcnow(),
            result={"scenes_synced": 42, "duration": 120},
            total_items=100,
            processed_items=100,
        )

        mock_job_service.get_job = AsyncMock(return_value=completed_job)

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result"]["scenes_synced"] == 42

    def test_job_lifecycle_failed(self, client, mock_db, mock_job_service):
        """Test job lifecycle when job fails."""
        job_id = str(uuid4())

        # Add get_job_logs mock
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        # Create a failed job
        failed_job = create_job_mock(
            id=job_id,
            type=JobType.ANALYSIS,
            status=JobStatus.FAILED,
            progress=30,
            job_metadata={"scene_id": "test-scene"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error="OpenAI API rate limit exceeded",
            total_items=100,
            processed_items=30,
        )

        mock_job_service.get_job = AsyncMock(return_value=failed_job)

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "OpenAI API rate limit exceeded"
        assert data["progress"] == 30

    def test_job_lifecycle_cancelled(self, client, mock_db, mock_job_service):
        """Test job lifecycle when job is cancelled."""
        job_id = str(uuid4())

        # Add get_job_logs mock
        mock_job_service.get_job_logs = AsyncMock(return_value=None)

        # Start with a running job
        running_job = create_job_mock(
            id=job_id,
            type=JobType.ANALYSIS,
            status=JobStatus.RUNNING,
            progress=25,
            job_metadata={"batch_size": 100},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            total_items=100,
            processed_items=25,
        )

        mock_job_service.get_job = AsyncMock(return_value=running_job)
        mock_job_service.cancel_job = AsyncMock(return_value=True)

        # Cancel the job
        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Check cancelled state
        cancelled_job = create_job_mock(
            id=job_id,
            type=JobType.ANALYSIS,
            status=JobStatus.CANCELLED,
            progress=25,
            job_metadata=running_job.job_metadata,
            created_at=running_job.created_at,
            updated_at=datetime.utcnow(),
            started_at=running_job.started_at,
            completed_at=datetime.utcnow(),
            error="Cancelled by user",
            total_items=100,
            processed_items=25,
        )

        mock_job_service.get_job = AsyncMock(return_value=cancelled_job)

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["error"] == "Cancelled by user"

    def test_multiple_jobs_different_types(self, client, mock_db, mock_job_service):
        """Test handling multiple concurrent jobs of different types."""
        # Create jobs of different types
        sync_job = create_job_mock(
            type=JobType.SYNC,
            status=JobStatus.RUNNING,
            progress=40,
            job_metadata={"full_sync": True},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            total_items=100,
            processed_items=40,
        )

        analysis_job = create_job_mock(
            type=JobType.ANALYSIS,
            status=JobStatus.PENDING,
            progress=0,
            job_metadata={"scene_id": "scene-123"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        batch_job = create_job_mock(
            type=JobType.ANALYSIS,
            status=JobStatus.COMPLETED,
            progress=100,
            job_metadata={"batch_size": 50},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result={"analyzed": 50, "failed": 0},
            total_items=50,
            processed_items=50,
        )

        # Mock active jobs from queue
        mock_job_service.get_active_jobs = AsyncMock(
            return_value=[sync_job, analysis_job]
        )

        # Mock database query
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [batch_job]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 3

        # Verify different job types and statuses
        job_types = {job["type"] for job in data["jobs"]}
        job_statuses = {job["status"] for job in data["jobs"]}

        assert "sync" in job_types
        assert "scene_analysis" in job_types
        assert "scene_analysis" in job_types

        assert "running" in job_statuses
        assert "pending" in job_statuses
        assert "completed" in job_statuses

    def test_job_with_logs(self, client, mock_db, mock_job_service):
        """Test getting job with logs when available."""
        job_id = str(uuid4())

        # Create a job with logs
        job_with_logs = create_job_mock(
            id=job_id,
            type=JobType.SYNC_SCENES,
            status=JobStatus.RUNNING,
            progress=60,
            job_metadata={"source": "api"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            total_items=100,
            processed_items=60,
        )

        # Mock job service to return job and logs
        mock_job_service.get_job = AsyncMock(return_value=job_with_logs)
        # Add get_job_logs as AsyncMock (it was removed from fixture but route still checks hasattr)
        # Logs should be a list of strings as per the schema
        mock_job_service.get_job_logs = AsyncMock(
            return_value=[
                "2024-01-01T10:00:00 [INFO] Job started",
                "2024-01-01T10:01:00 [INFO] Processing scenes...",
                "2024-01-01T10:02:00 [ERROR] Failed to process scene 5",
            ]
        )

        response = client.get(f"/api/jobs/{job_id}")

        # Debug the response if it fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] is not None
        assert len(data["logs"]) == 3
        assert "Job started" in data["logs"][0]
        assert "[ERROR]" in data["logs"][2]

    def test_cancel_job_not_found(self, client, mock_db, mock_job_service):
        """Test canceling a job that doesn't exist."""
        # Mock job service to return None (not in active queue)
        mock_job_service.get_job = AsyncMock(return_value=None)

        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post("/api/jobs/nonexistent-id/cancel")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_cancel_already_completed_job(self, client, mock_db, mock_job_service):
        """Test canceling a job that is already completed."""
        job_id = str(uuid4())

        # Mock job service to return None (not in active queue)
        mock_job_service.get_job = AsyncMock(return_value=None)

        # Create a completed job in database
        completed_job = Mock(spec=Job)
        completed_job.id = job_id
        completed_job.status = "completed"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = completed_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 400
        assert "Cannot cancel a completed job" in response.json()["detail"]

    def test_cancel_already_failed_job(self, client, mock_db, mock_job_service):
        """Test canceling a job that has already failed."""
        job_id = str(uuid4())

        # Mock job service to return None (not in active queue)
        mock_job_service.get_job = AsyncMock(return_value=None)

        # Create a failed job in database
        failed_job = Mock(spec=Job)
        failed_job.id = job_id
        failed_job.status = "failed"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = failed_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 400
        assert "Cannot cancel a failed job" in response.json()["detail"]

    def test_cancel_job_service_failure(self, client, mock_job_service):
        """Test when job cancellation fails in the service."""
        job_id = str(uuid4())

        # Create an active job
        active_job = Mock(spec=Job)
        active_job.id = job_id
        active_job.type = JobType.SYNC_SCENES
        active_job.status = JobStatus.RUNNING

        # Mock job service to return job but fail cancellation
        mock_job_service.get_job = AsyncMock(return_value=active_job)
        mock_job_service.cancel_job = AsyncMock(return_value=False)

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 500
        assert "Failed to cancel job" in response.json()["detail"]

    def test_retry_job_not_found(self, client, mock_db):
        """Test retrying a job that doesn't exist."""
        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post("/api/jobs/nonexistent-id/retry")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_retry_running_job(self, client, mock_db):
        """Test retrying a job that is currently running."""
        job_id = str(uuid4())

        # Create a running job
        running_job = Mock(spec=Job)
        running_job.id = job_id
        running_job.status = "running"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = running_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/retry")
        assert response.status_code == 400
        assert "Cannot retry a running job" in response.json()["detail"]

    def test_retry_pending_job(self, client, mock_db):
        """Test retrying a job that is pending."""
        job_id = str(uuid4())

        # Create a pending job
        pending_job = Mock(spec=Job)
        pending_job.id = job_id
        pending_job.status = "pending"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = pending_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/retry")
        assert response.status_code == 400
        assert "Cannot retry a pending job" in response.json()["detail"]

    def test_retry_completed_job(self, client, mock_db):
        """Test retrying a job that completed successfully."""
        job_id = str(uuid4())

        # Create a completed job
        completed_job = Mock(spec=Job)
        completed_job.id = job_id
        completed_job.status = "completed"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = completed_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/retry")
        assert response.status_code == 400
        assert "Cannot retry a completed job" in response.json()["detail"]

    def test_retry_cancelled_job(self, client, mock_db, mock_job_service):
        """Test retrying a cancelled job."""
        job_id = str(uuid4())

        # Create a cancelled job
        cancelled_job = Mock(spec=Job)
        cancelled_job.id = job_id
        cancelled_job.type = JobType.ANALYSIS
        cancelled_job.status = "cancelled"  # String status for database job
        cancelled_job.job_metadata = {"scene_id": "test-scene", "retry_count": 1}
        cancelled_job.error = "Cancelled by user"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = cancelled_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock job service to create a new job
        new_job_id = str(uuid4())
        new_job = Mock(spec=Job, id=new_job_id)
        mock_job_service.create_job = AsyncMock(return_value=new_job)

        response = client.post(f"/api/jobs/{job_id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_job_id"] == new_job_id

        # Verify the job service was called with original metadata
        mock_job_service.create_job.assert_called_once_with(
            job_type=cancelled_job.type, metadata=cancelled_job.job_metadata, db=mock_db
        )

    def test_retry_job_preserves_metadata(self, client, mock_db, mock_job_service):
        """Test that retrying a job preserves all original metadata."""
        job_id = str(uuid4())

        # Create a failed job with complex metadata
        failed_job = Mock(spec=Job)
        failed_job.id = job_id
        failed_job.type = JobType.ANALYSIS
        failed_job.status = "failed"
        failed_job.job_metadata = {
            "batch_size": 100,
            "scene_ids": ["scene1", "scene2", "scene3"],
            "analysis_options": {
                "detect_performers": True,
                "detect_tags": True,
                "generate_details": False,
            },
            "priority": "high",
        }
        failed_job.error = "API timeout"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = failed_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock job service to create a new job
        new_job_id = str(uuid4())
        new_job = Mock(spec=Job, id=new_job_id)
        mock_job_service.create_job = AsyncMock(return_value=new_job)

        response = client.post(f"/api/jobs/{job_id}/retry")
        assert response.status_code == 200

        # Verify all metadata was preserved
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args[1]["metadata"] == failed_job.job_metadata
        assert call_args[1]["metadata"]["batch_size"] == 100
        assert call_args[1]["metadata"]["scene_ids"] == ["scene1", "scene2", "scene3"]
        assert call_args[1]["metadata"]["analysis_options"]["detect_performers"] is True

    def test_cancel_job_from_database(self, client, mock_db, mock_job_service):
        """Test canceling a job that exists only in database (not in active queue)."""
        job_id = str(uuid4())

        # Mock job service to return None (not in active queue)
        mock_job_service.get_job = AsyncMock(return_value=None)

        # Create a running job in database
        db_job = Mock(spec=Job)
        db_job.id = job_id
        db_job.status = "running"  # String status for database job

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = db_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(f"/api/jobs/{job_id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify the job status was updated in database
        assert db_job.status == "cancelled"
        assert db_job.error == "Cancelled by user"
        mock_db.commit.assert_called_once()
