"""Tests for schedule API routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models import Job, ScheduledTask
from app.models.job import JobStatus, JobType
from app.services.job_service import JobService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = AsyncMock()
    db.execute = AsyncMock()
    db.close = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"sub": "test_user", "email": "test@example.com"}


@pytest.fixture
def mock_job_service():
    """Mock job service."""
    service = Mock(spec=JobService)
    mock_job = Mock()
    mock_job.id = "job-456"
    service.create_job = AsyncMock(return_value=mock_job)
    return service


@pytest.fixture
def client(mock_db, mock_user, mock_job_service):
    """Test client with mocked dependencies."""
    # Create mock services
    from app.core.config import Settings
    from app.core.dependencies import (
        get_current_user,
        get_db,
        get_job_service,
        get_openai_client,
        get_settings,
        get_stash_service,
    )
    from app.services.stash_service import StashService

    mock_settings = Settings()
    mock_stash_service = Mock(spec=StashService)
    mock_openai_client = None

    async def override_get_db():
        yield mock_db

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_stash_service] = lambda: mock_stash_service
    app.dependency_overrides[get_openai_client] = lambda: mock_openai_client

    # Skip lifespan events in tests
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_schedule():
    """Create a mock scheduled task."""
    schedule = Mock(spec=ScheduledTask)
    schedule.id = 1
    schedule.name = "Test Schedule"
    schedule.task_type = "sync"
    schedule.schedule = "0 */6 * * *"
    schedule.config = {"param1": "value1"}
    schedule.enabled = True
    schedule.created_at = datetime.now(timezone.utc)
    schedule.updated_at = datetime.now(timezone.utc)
    schedule.last_run = None
    schedule.next_run = datetime.now(timezone.utc)
    schedule.last_job_id = None
    schedule.to_dict = Mock(
        return_value={
            "id": schedule.id,
            "name": schedule.name,
            "task_type": schedule.task_type,
            "schedule": schedule.schedule,
            "config": schedule.config,
            "enabled": schedule.enabled,
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat(),
            "last_run": None,
            "next_run": schedule.next_run.isoformat(),
            "last_job_id": None,
            "is_valid_schedule": True,
            "should_run": False,
            "seconds_until_next_run": 3600,
        }
    )
    schedule.update_next_run = Mock()
    schedule.is_valid_schedule = Mock(return_value=True)
    schedule.should_run_now = Mock(return_value=False)
    return schedule


@pytest.fixture
def mock_job():
    """Create a mock job."""
    job = Mock(spec=Job)
    job.id = "job-123"
    job.job_type = JobType.SYNC
    job.status = JobStatus.COMPLETED
    job.created_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)
    job.job_metadata = {"scheduled_task_id": 1}
    job.result = {"success": True}
    job.error = None
    return job


class TestScheduleRoutes:
    """Test schedule CRUD endpoints."""

    def test_list_schedules(self, client, mock_db, mock_schedule):
        """Test listing all schedules."""
        # Mock database result
        mock_result = Mock()
        mock_result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=[mock_schedule]))
        )
        mock_db.execute.return_value = mock_result

        response = client.get("/api/schedules")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "schedules" in data
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["name"] == "Test Schedule"

    def test_list_schedules_error(self, client, mock_db):
        """Test list schedules with database error."""
        mock_db.execute.side_effect = Exception("DB Error")

        response = client.get("/api/schedules")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve schedules" in response.json()["detail"]

    def test_create_schedule_success(self, client, mock_db):
        """Test creating a new schedule."""
        schedule_data = {
            "name": "New Schedule",
            "task_type": "sync",
            "schedule": "0 */4 * * *",
            "config": {"param": "value"},
            "enabled": True,
        }

        # Mock the created schedule
        created_schedule = Mock(spec=ScheduledTask)
        created_schedule.to_dict = Mock(
            return_value={
                **schedule_data,
                "id": 2,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "next_run": datetime.now(timezone.utc).isoformat(),
                "last_run": None,
                "last_job_id": None,
            }
        )

        mock_db.refresh = AsyncMock(side_effect=lambda x: setattr(x, "id", 2))

        response = client.post("/api/schedules", json=schedule_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == "New Schedule"
        assert data["task_type"] == "sync"
        assert data["schedule"] == "0 */4 * * *"

    def test_create_schedule_invalid_cron(self, client):
        """Test creating schedule with invalid cron expression."""
        schedule_data = {
            "name": "Bad Schedule",
            "task_type": "sync",
            "schedule": "invalid cron",
            "config": {},
        }

        response = client.post("/api/schedules", json=schedule_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid cron expression" in response.json()["detail"]

    def test_create_schedule_missing_fields(self, client):
        """Test creating schedule with missing required fields."""
        schedule_data = {
            "name": "Incomplete Schedule",
            # Missing task_type and schedule
        }

        response = client.post("/api/schedules", json=schedule_data)
        # Should get KeyError which is caught and returns 400
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_create_schedule_db_error(self, client, mock_db):
        """Test create schedule with database error."""
        schedule_data = {
            "name": "Error Schedule",
            "task_type": "sync",
            "schedule": "0 */4 * * *",
        }

        mock_db.commit.side_effect = Exception("DB Error")

        response = client.post("/api/schedules", json=schedule_data)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create schedule" in response.json()["detail"]

    def test_update_schedule_success(self, client, mock_db, mock_schedule):
        """Test updating an existing schedule."""
        schedule_id = 1

        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update the mock to reflect changes
        mock_schedule.to_dict.return_value.update(
            {
                "name": "Updated Schedule",
                "schedule": "0 */12 * * *",
                "enabled": False,
                "next_run": None,
            }
        )

        update_data = {
            "name": "Updated Schedule",
            "schedule": "0 */12 * * *",
            "enabled": False,
        }

        response = client.put(f"/api/schedules/{schedule_id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == "Updated Schedule"
        assert data["schedule"] == "0 */12 * * *"
        assert data["enabled"] is False

    def test_update_schedule_not_found(self, client, mock_db):
        """Test updating non-existent schedule."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        update_data = {"name": "Updated"}

        response = client.put("/api/schedules/999", json=update_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Schedule not found" in response.json()["detail"]

    def test_update_schedule_invalid_cron(self, client, mock_db, mock_schedule):
        """Test updating schedule with invalid cron expression."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        update_data = {"schedule": "invalid"}

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid cron expression" in response.json()["detail"]

    def test_delete_schedule_success(self, client, mock_db, mock_schedule):
        """Test deleting a schedule."""
        schedule_id = 1

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        response = client.delete(f"/api/schedules/{schedule_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Schedule deleted successfully"

        # Verify delete was called
        mock_db.delete.assert_called_once_with(mock_schedule)
        mock_db.commit.assert_called()

    def test_delete_schedule_not_found(self, client, mock_db):
        """Test deleting non-existent schedule."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        response = client.delete("/api/schedules/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Schedule not found" in response.json()["detail"]

    def test_run_schedule_now(self, client, mock_db, mock_schedule, mock_job_service):
        """Test manually triggering a scheduled task."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        response = client.post(f"/api/schedules/{mock_schedule.id}/run")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["job_id"] == "job-456"
        assert data["message"] == "Schedule triggered successfully"

        # Verify job was created with correct params
        mock_job_service.create_job.assert_called_once()
        call_args = mock_job_service.create_job.call_args
        assert call_args.kwargs["job_type"] == JobType.SYNC
        assert call_args.kwargs["metadata"]["param1"] == "value1"
        assert call_args.kwargs["metadata"]["scheduled_task_id"] == mock_schedule.id

    def test_run_schedule_now_not_found(self, client, mock_db):
        """Test running non-existent schedule."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        response = client.post("/api/schedules/999/run")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Schedule not found" in response.json()["detail"]

    def test_get_schedule_runs(self, client, mock_db, mock_schedule, mock_job):
        """Test getting run history for a schedule."""
        # Mock schedule query
        schedule_result = Mock()
        schedule_result.scalar_one_or_none = Mock(return_value=mock_schedule)

        # Mock jobs query
        jobs_result = Mock()
        jobs_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_job])))

        mock_db.execute.side_effect = [schedule_result, jobs_result]

        response = client.get(f"/api/schedules/{mock_schedule.id}/runs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "runs" in data
        assert "stats" in data
        assert len(data["runs"]) == 1

        # Check stats
        assert data["stats"]["total_runs"] == 1
        assert data["stats"]["successful_runs"] == 1
        assert data["stats"]["failed_runs"] == 0

    def test_get_schedule_runs_not_found(self, client, mock_db):
        """Test getting runs for non-existent schedule."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        response = client.get("/api/schedules/999/runs")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Schedule not found" in response.json()["detail"]

    def test_preview_schedule(self, client):
        """Test previewing schedule next run times."""
        preview_data = {"expression": "0 */2 * * *", "count": 3}

        response = client.post("/api/schedules/preview", json=preview_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "next_runs" in data
        assert len(data["next_runs"]) == 3

        # Verify times are in ascending order
        for i in range(1, len(data["next_runs"])):
            assert data["next_runs"][i] > data["next_runs"][i - 1]

    def test_preview_schedule_invalid_expression(self, client):
        """Test preview with invalid cron expression."""
        preview_data = {"expression": "invalid cron", "count": 5}

        response = client.post("/api/schedules/preview", json=preview_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid cron expression" in response.json()["detail"]

    def test_preview_schedule_missing_expression(self, client):
        """Test preview without expression."""
        preview_data = {"count": 5}

        response = client.post("/api/schedules/preview", json=preview_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Expression is required" in response.json()["detail"]

    def test_get_all_schedule_runs(self, client, mock_db, mock_job):
        """Test getting run history for all schedules."""
        # Mock jobs query
        jobs_result = Mock()
        jobs_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_job])))
        mock_db.execute.return_value = jobs_result

        response = client.get("/api/schedule-runs")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "runs" in data
        assert "stats" in data
        assert len(data["runs"]) == 1
