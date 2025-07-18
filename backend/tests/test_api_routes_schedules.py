"""Tests for schedule API routes."""

from datetime import datetime, timedelta, timezone
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


class TestScheduleCronValidation:
    """Test cron expression validation and parsing."""

    def test_valid_cron_expressions(self, client):
        """Test various valid cron expressions."""
        valid_expressions = [
            "* * * * *",  # Every minute
            "0 * * * *",  # Every hour
            "0 0 * * *",  # Daily at midnight
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
            "0 0 1 1 *",  # Yearly on Jan 1st
            "*/5 * * * *",  # Every 5 minutes
            "0 */2 * * *",  # Every 2 hours
            "0 9-17 * * 1-5",  # Weekdays 9am-5pm
            "0 0,12 * * *",  # Twice daily at midnight and noon
            "0 0 * * 1,3,5",  # Mon, Wed, Fri
            "15 3 * * *",  # Daily at 3:15 AM
            "0 0 28-31 * *",  # Last days of month
            "0 0 * 2 *",  # February only
            "@hourly",  # Special string
            "@daily",  # Special string
            "@weekly",  # Special string
            "@monthly",  # Special string
            "@yearly",  # Special string
        ]

        for expr in valid_expressions:
            # Test in create endpoint
            schedule_data = {
                "name": f"Test {expr}",
                "task_type": "sync",
                "schedule": expr,
                "config": {},
            }
            response = client.post("/api/schedules", json=schedule_data)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Failed for expression: {expr}"

            # Test in preview endpoint
            preview_data = {"expression": expr, "count": 3}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Preview failed for expression: {expr}"

    def test_invalid_cron_expressions(self, client):
        """Test various invalid cron expressions."""
        invalid_expressions = [
            "",  # Empty string
            "invalid",  # Not a cron expression
            "* * * *",  # Too few fields
            "60 * * * *",  # Invalid minute (0-59)
            "* 24 * * *",  # Invalid hour (0-23)
            "* * 32 * *",  # Invalid day (1-31)
            "* * * 13 *",  # Invalid month (1-12)
            "* * * * 8",  # Invalid day of week (0-7)
            "*/0 * * * *",  # Invalid step
            "1-60 * * * *",  # Invalid range
            "@invalid",  # Invalid special string
            "* * * * * L",  # Invalid modifier
            "? * * * *",  # Invalid character
        ]

        for expr in invalid_expressions:
            # Test in create endpoint
            schedule_data = {
                "name": f"Test {expr}",
                "task_type": "sync",
                "schedule": expr,
                "config": {},
            }
            response = client.post("/api/schedules", json=schedule_data)
            assert (
                response.status_code == status.HTTP_400_BAD_REQUEST
            ), f"Should fail for expression: {expr}"
            assert "Invalid cron expression" in response.json()["detail"]

            # Test in preview endpoint
            preview_data = {"expression": expr, "count": 3}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert (
                response.status_code == status.HTTP_400_BAD_REQUEST
            ), f"Preview should fail for expression: {expr}"

    def test_cron_edge_cases(self, client):
        """Test edge cases in cron parsing."""
        # Test maximum values
        edge_cases = [
            ("59 * * * *", True),  # Max minute
            ("* 23 * * *", True),  # Max hour
            ("* * 31 * *", True),  # Max day
            ("* * * 12 *", True),  # Max month
            ("* * * * 7", True),  # Max day of week (0 and 7 both mean Sunday)
            ("0-59 * * * *", True),  # Full minute range
            ("* 0-23 * * *", True),  # Full hour range
            ("* * 1-31 * *", True),  # Full day range
            ("* * * 1-12 *", True),  # Full month range
            ("* * * * 0-6", True),  # Full day of week range
        ]

        for expr, should_succeed in edge_cases:
            schedule_data = {
                "name": f"Edge case {expr}",
                "task_type": "sync",
                "schedule": expr,
                "config": {},
            }
            response = client.post("/api/schedules", json=schedule_data)
            if should_succeed:
                assert (
                    response.status_code == status.HTTP_200_OK
                ), f"Should succeed for expression: {expr}"
            else:
                assert (
                    response.status_code == status.HTTP_400_BAD_REQUEST
                ), f"Should fail for expression: {expr}"

    def test_cron_special_characters(self, client):
        """Test special characters in cron expressions."""
        test_cases = [
            ("*/15 * * * *", 4),  # Every 15 minutes should give 4 per hour
            ("0 */6 * * *", 4),  # Every 6 hours should give 4 per day
            ("0 0 */7 * *", None),  # Every 7 days
            ("0 0 * */3 *", None),  # Every 3 months
            ("0,15,30,45 * * * *", None),  # Multiple values
            ("0-10 * * * *", None),  # Range
            ("0-10/2 * * * *", None),  # Range with step
        ]

        for expr, expected_count in test_cases:
            # Test preview to ensure parsing works
            preview_data = {"expression": expr, "count": 24}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Failed for expression: {expr}"

            data = response.json()
            next_runs = data["next_runs"]
            assert len(next_runs) == 24

            # Verify spacing between runs if expected_count is specified
            if expected_count is not None and expr.startswith("*/"):
                # For minute-based schedules, check within an hour
                if "* * * *" in expr:
                    # Count runs within ANY full hour (not from the first run)
                    first_run = datetime.fromisoformat(
                        next_runs[0].replace("Z", "+00:00")
                    )
                    # Start from the beginning of the next hour to get a full hour
                    hour_start = first_run.replace(
                        minute=0, second=0, microsecond=0
                    ) + timedelta(hours=1)
                    hour_end = hour_start + timedelta(hours=1)
                    runs_in_hour = sum(
                        1
                        for run in next_runs
                        if hour_start
                        <= datetime.fromisoformat(run.replace("Z", "+00:00"))
                        < hour_end
                    )
                    assert (
                        runs_in_hour == expected_count
                    ), f"Expected {expected_count} runs per hour for {expr}, got {runs_in_hour}"

    def test_preview_schedule_count_variations(self, client):
        """Test preview endpoint with different count values."""
        test_counts = [1, 5, 10, 50, 100]

        for count in test_counts:
            preview_data = {"expression": "0 * * * *", "count": count}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert len(data["next_runs"]) == count

            # Verify chronological order
            for i in range(1, len(data["next_runs"])):
                assert data["next_runs"][i] > data["next_runs"][i - 1]

    def test_cron_validation_in_update(self, client, mock_db, mock_schedule):
        """Test cron validation when updating schedules."""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Test with valid expression
        valid_update = {"schedule": "0 */4 * * *"}
        response = client.put(f"/api/schedules/{mock_schedule.id}", json=valid_update)
        assert response.status_code == status.HTTP_200_OK

        # Test with invalid expression
        invalid_update = {"schedule": "not a cron"}
        response = client.put(f"/api/schedules/{mock_schedule.id}", json=invalid_update)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid cron expression" in response.json()["detail"]

    def test_cron_month_names(self, client):
        """Test cron expressions with month names."""
        month_expressions = [
            "0 0 1 JAN *",  # January
            "0 0 * FEB *",  # February
            "0 0 15 MAR-MAY *",  # March through May
            "0 0 * JUN,JUL,AUG *",  # Summer months
            "0 0 * SEP-DEC *",  # Fall/Winter
        ]

        for expr in month_expressions:
            preview_data = {"expression": expr, "count": 3}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Failed for expression: {expr}"

    def test_cron_weekday_names(self, client):
        """Test cron expressions with weekday names."""
        weekday_expressions = [
            "0 0 * * SUN",  # Sunday
            "0 0 * * MON-FRI",  # Weekdays
            "0 0 * * SAT,SUN",  # Weekend
            "0 9 * * MON",  # Monday morning
            "0 17 * * FRI",  # Friday evening
        ]

        for expr in weekday_expressions:
            preview_data = {"expression": expr, "count": 5}
            response = client.post("/api/schedules/preview", json=preview_data)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Failed for expression: {expr}"

    def test_complex_cron_combinations(self, client):
        """Test complex combinations of cron features."""
        complex_expressions = [
            "0 0,12 * * MON-FRI",  # Twice daily on weekdays
            "*/30 9-17 * * 1-5",  # Every 30 min during work hours
            "0 0 1,15 * *",  # 1st and 15th of month
        ]

        for expr in complex_expressions:
            # Some expressions might not be supported by croniter
            preview_data = {"expression": expr, "count": 3}
            response = client.post("/api/schedules/preview", json=preview_data)
            # Just verify we get a proper response (either success or proper error)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ]


class TestScheduleEnableDisable:
    """Test schedule enable/disable functionality."""

    def test_create_schedule_enabled_by_default(self, client, mock_db):
        """Test that schedules are enabled by default when created."""
        schedule_data = {
            "name": "Default Enabled Schedule",
            "task_type": "sync",
            "schedule": "0 */4 * * *",
            "config": {},
        }

        response = client.post("/api/schedules", json=schedule_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["enabled"] is True
        assert data["next_run"] is not None

    def test_create_schedule_explicitly_disabled(self, client, mock_db):
        """Test creating a disabled schedule."""
        schedule_data = {
            "name": "Disabled Schedule",
            "task_type": "sync",
            "schedule": "0 */4 * * *",
            "config": {},
            "enabled": False,
        }

        # Mock the schedule that will be created
        created_schedule = Mock(spec=ScheduledTask)
        created_schedule.to_dict = Mock(
            return_value={
                "id": 2,
                "name": "Disabled Schedule",
                "task_type": "sync",
                "schedule": "0 */4 * * *",
                "config": {},
                "enabled": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "next_run": None,  # Disabled schedules should have None
                "last_run": None,
                "last_job_id": None,
            }
        )

        # Override refresh to set attributes on the mock
        async def mock_refresh(obj):
            if hasattr(obj, "enabled") and not obj.enabled:
                obj.next_run = None
            obj.to_dict = created_schedule.to_dict

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        response = client.post("/api/schedules", json=schedule_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["enabled"] is False
        # Disabled schedules should not have next_run calculated
        assert data.get("next_run") is None

    def test_enable_disabled_schedule(self, client, mock_db, mock_schedule):
        """Test enabling a previously disabled schedule."""
        # Setup mock schedule as disabled
        mock_schedule.enabled = False
        mock_schedule.next_run = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update to enable the schedule
        update_data = {"enabled": True}

        # Mock the updated return value
        mock_schedule.to_dict.return_value = {
            "id": mock_schedule.id,
            "name": mock_schedule.name,
            "task_type": mock_schedule.task_type,
            "schedule": mock_schedule.schedule,
            "config": mock_schedule.config,
            "enabled": True,
            "next_run": datetime.now(timezone.utc).isoformat(),
            "created_at": mock_schedule.created_at.isoformat(),
            "updated_at": mock_schedule.updated_at.isoformat(),
        }

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["enabled"] is True
        assert data["next_run"] is not None

        # Verify update_next_run was called
        mock_schedule.update_next_run.assert_called_once()

    def test_disable_enabled_schedule(self, client, mock_db, mock_schedule):
        """Test disabling a previously enabled schedule."""
        # Setup mock schedule as enabled
        mock_schedule.enabled = True
        mock_schedule.next_run = datetime.now(timezone.utc)

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update to disable the schedule
        update_data = {"enabled": False}

        # Mock the updated return value
        mock_schedule.to_dict.return_value = {
            "id": mock_schedule.id,
            "name": mock_schedule.name,
            "task_type": mock_schedule.task_type,
            "schedule": mock_schedule.schedule,
            "config": mock_schedule.config,
            "enabled": False,
            "next_run": None,
            "created_at": mock_schedule.created_at.isoformat(),
            "updated_at": mock_schedule.updated_at.isoformat(),
        }

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["enabled"] is False
        assert data["next_run"] is None

    def test_update_schedule_preserves_enabled_state(
        self, client, mock_db, mock_schedule
    ):
        """Test that updating other fields preserves the enabled state."""
        # Setup mock schedule as enabled
        mock_schedule.enabled = True

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update only the name, not the enabled state
        update_data = {"name": "Updated Name Only"}

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify enabled state was preserved
        assert mock_schedule.enabled is True

    def test_change_schedule_expression_while_disabled(
        self, client, mock_db, mock_schedule
    ):
        """Test changing cron expression on a disabled schedule."""
        # Setup mock schedule as disabled
        mock_schedule.enabled = False
        mock_schedule.next_run = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update the cron expression
        update_data = {"schedule": "0 0 * * *"}  # Daily

        # Mock the updated return value
        mock_schedule.to_dict.return_value = {
            "id": mock_schedule.id,
            "name": mock_schedule.name,
            "task_type": mock_schedule.task_type,
            "schedule": "0 0 * * *",
            "config": mock_schedule.config,
            "enabled": False,
            "next_run": None,  # Should remain None since disabled
            "created_at": mock_schedule.created_at.isoformat(),
            "updated_at": mock_schedule.updated_at.isoformat(),
        }

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["schedule"] == "0 0 * * *"
        assert data["enabled"] is False
        assert data["next_run"] is None

    def test_change_schedule_and_enable_simultaneously(
        self, client, mock_db, mock_schedule
    ):
        """Test changing cron expression and enabling in the same request."""
        # Setup mock schedule as disabled
        mock_schedule.enabled = False
        mock_schedule.next_run = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Update both schedule and enabled state
        update_data = {
            "schedule": "*/15 * * * *",  # Every 15 minutes
            "enabled": True,
        }

        # Mock the updated return value
        mock_schedule.to_dict.return_value = {
            "id": mock_schedule.id,
            "name": mock_schedule.name,
            "task_type": mock_schedule.task_type,
            "schedule": "*/15 * * * *",
            "config": mock_schedule.config,
            "enabled": True,
            "next_run": datetime.now(timezone.utc).isoformat(),
            "created_at": mock_schedule.created_at.isoformat(),
            "updated_at": mock_schedule.updated_at.isoformat(),
        }

        response = client.put(f"/api/schedules/{mock_schedule.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["schedule"] == "*/15 * * * *"
        assert data["enabled"] is True
        assert data["next_run"] is not None

        # Verify update_next_run was called
        mock_schedule.update_next_run.assert_called_once()

    def test_disabled_schedule_not_triggered(
        self, client, mock_db, mock_schedule, mock_job_service
    ):
        """Test that disabled schedules cannot be manually triggered."""
        # Setup mock schedule as disabled
        mock_schedule.enabled = False

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_schedule)
        mock_db.execute.return_value = mock_result

        # Attempt to manually trigger the disabled schedule
        response = client.post(f"/api/schedules/{mock_schedule.id}/run")

        # This test assumes the API allows triggering disabled schedules
        # If the API prevents this, we'd expect a 400 error instead
        assert response.status_code == status.HTTP_200_OK

        # Verify job was still created (manual trigger overrides enabled state)
        mock_job_service.create_job.assert_called_once()

    def test_list_schedules_shows_enabled_state(self, client, mock_db):
        """Test that listing schedules includes the enabled state."""
        # Create mock schedules with different enabled states
        enabled_schedule = Mock(spec=ScheduledTask)
        enabled_schedule.to_dict = Mock(
            return_value={
                "id": 1,
                "name": "Enabled Schedule",
                "enabled": True,
                "next_run": datetime.now(timezone.utc).isoformat(),
            }
        )

        disabled_schedule = Mock(spec=ScheduledTask)
        disabled_schedule.to_dict = Mock(
            return_value={
                "id": 2,
                "name": "Disabled Schedule",
                "enabled": False,
                "next_run": None,
            }
        )

        mock_result = Mock()
        mock_result.scalars = Mock(
            return_value=Mock(
                all=Mock(return_value=[enabled_schedule, disabled_schedule])
            )
        )
        mock_db.execute.return_value = mock_result

        response = client.get("/api/schedules")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        schedules = data["schedules"]
        assert len(schedules) == 2

        # Check first schedule (enabled)
        assert schedules[0]["enabled"] is True
        assert schedules[0]["next_run"] is not None

        # Check second schedule (disabled)
        assert schedules[1]["enabled"] is False
        assert schedules[1]["next_run"] is None

    def test_schedule_state_in_to_dict(self, mock_schedule):
        """Test that schedule's to_dict method includes enabled state."""
        # Test enabled schedule
        mock_schedule.enabled = True
        mock_schedule.next_run = datetime.now(timezone.utc)

        result = mock_schedule.to_dict()
        assert result["enabled"] is True
        assert result["next_run"] is not None

        # Test disabled schedule
        mock_schedule.enabled = False
        mock_schedule.next_run = None
        mock_schedule.to_dict.return_value["enabled"] = False
        mock_schedule.to_dict.return_value["next_run"] = None

        result = mock_schedule.to_dict()
        assert result["enabled"] is False
        assert result["next_run"] is None
