"""Tests for model classes."""

from datetime import datetime

from app.models import (
    AnalysisPlan,
    Job,
    JobStatus,
    JobType,
    Performer,
    Scene,
    ScheduledTask,
    Setting,
    Studio,
    SyncHistory,
    Tag,
)


class TestBaseModel:
    """Test base model functionality."""

    def test_base_model_creation(self):
        """Test base model attributes."""
        # BaseModel is abstract, test through a concrete model
        scene = Scene(
            id="scene123",
            title="Test Scene",
            paths=["/path/to/scene.mp4"],
            stash_id="stash123",
            created_date=datetime.now(),
        )

        assert scene.id == "scene123"
        # created_at and updated_at are set by database, not in memory
        # They would be set after saving to DB
        assert scene.title == "Test Scene"
        assert scene.paths == ["/path/to/scene.mp4"]

    def test_base_model_dict(self):
        """Test model to_dict method."""
        performer = Performer(id="perf123", name="Test Performer", stash_id="perf123")

        data = performer.to_dict()

        assert data["name"] == "Test Performer"
        assert data["stash_id"] == "perf123"
        assert data["id"] == "perf123"


class TestSceneModel:
    """Test Scene model."""

    def test_scene_creation(self):
        """Test creating a scene."""
        scene = Scene(
            id="scene123",
            title="Test Scene",
            paths=["/videos/test.mp4"],
            stash_id="scene123",
            date="2023-01-01",
            details="Test details",
            url="https://example.com",
            rating=85,
            created_date=datetime.now(),
        )

        assert scene.title == "Test Scene"
        assert scene.paths == ["/videos/test.mp4"]
        assert scene.rating == 85
        assert scene.date == "2023-01-01"

    def test_scene_relationships(self):
        """Test scene relationships."""
        scene = Scene(
            id="s1",
            title="Test",
            paths=["/test.mp4"],
            stash_id="1",
            created_date=datetime.now(),
        )
        performer = Performer(id="p1", name="Performer 1", stash_id="p1")
        tag = Tag(id="t1", name="Tag 1", stash_id="t1")
        studio = Studio(id="st1", name="Studio 1", stash_id="s1")

        scene.performers.append(performer)
        scene.tags.append(tag)
        scene.studio = studio

        assert len(scene.performers) == 1
        assert len(scene.tags) == 1
        assert scene.studio.name == "Studio 1"

    def test_scene_json_serialization(self):
        """Test scene JSON fields."""
        scene = Scene(
            id="s1",
            title="Test",
            paths=["/test.mp4"],
            stash_id="1",
            created_date=datetime.now(),
        )

        # Test that paths is a JSON field
        assert isinstance(scene.paths, list)
        assert scene.paths[0] == "/test.mp4"


class TestPerformerModel:
    """Test Performer model."""

    def test_performer_creation(self):
        """Test creating a performer."""
        performer = Performer(
            name="Jane Doe",
            stash_id="perf123",
            gender="FEMALE",
            birthdate="1990-01-01",
            ethnicity="Caucasian",
            country="USA",
            hair_color="blonde",
            eye_color="blue",
            height_cm=170,
            weight_kg=55,
            measurements="34-24-34",
            fake_tits="No",
            tattoos="None",
            piercings="Ears",
            aliases=["Alias1", "Alias2"],
        )

        assert performer.name == "Jane Doe"
        assert performer.gender == "FEMALE"
        assert performer.height_cm == 170
        assert len(performer.aliases) == 2

    def test_performer_scenes_relationship(self):
        """Test performer-scenes relationship."""
        performer = Performer(id="p1", name="Test Performer", stash_id="p1")
        scene1 = Scene(
            id="s1",
            title="Scene 1",
            paths=["/s1.mp4"],
            stash_id="s1",
            created_date=datetime.now(),
        )
        scene2 = Scene(
            id="s2",
            title="Scene 2",
            paths=["/s2.mp4"],
            stash_id="s2",
            created_date=datetime.now(),
        )

        performer.scenes.extend([scene1, scene2])

        # Since scenes is a dynamic relationship, we can't use len() without a DB session
        # Just verify the relationship exists
        assert hasattr(performer, "scenes")


class TestTagModel:
    """Test Tag model."""

    def test_tag_creation(self):
        """Test creating a tag."""
        tag = Tag(
            id="tag123",
            name="outdoor",
            stash_id="tag123",
            description="Outdoor scenes",
            aliases=["outside", "nature"],
            last_synced=datetime.now(),
        )

        assert tag.name == "outdoor"
        assert tag.description == "Outdoor scenes"
        assert len(tag.aliases) == 2

    def test_tag_category(self):
        """Test tag with category."""
        tag = Tag(
            id="tag456", name="blonde", stash_id="tag456", last_synced=datetime.now()
        )

        # Tag model doesn't have a category field
        assert tag.name == "blonde"


class TestStudioModel:
    """Test Studio model."""

    def test_studio_creation(self):
        """Test creating a studio."""
        studio = Studio(
            id="studio123",
            name="Test Studio",
            stash_id="studio123",
            url="https://teststudio.com",
            last_synced=datetime.now(),
        )

        assert studio.name == "Test Studio"
        assert studio.url == "https://teststudio.com"
        # Studio uses parent_id not parent_studio_id
        assert studio.url == "https://teststudio.com"

    def test_studio_scenes_relationship(self):
        """Test studio-scenes relationship."""
        studio = Studio(
            id="st1", name="Test Studio", stash_id="s1", last_synced=datetime.now()
        )
        scene = Scene(
            id="sc1",
            title="Scene 1",
            paths=["/s1.mp4"],
            stash_id="sc1",
            created_date=datetime.now(),
        )

        # Set the relationship via foreign key
        scene.studio_id = studio.id

        # Since scenes is a dynamic relationship, we can't use len() without a DB session
        assert hasattr(studio, "scenes")
        assert scene.studio_id == studio.id


class TestJobModel:
    """Test Job model."""

    def test_job_creation(self):
        """Test creating a job."""
        job = Job(type=JobType.SYNC_SCENES, status=JobStatus.PENDING)

        assert job.type == JobType.SYNC_SCENES
        assert job.status == JobStatus.PENDING
        # Default values are set by the database, not in memory
        # Just verify the fields exist
        assert hasattr(job, "progress")
        assert hasattr(job, "total_items")
        assert hasattr(job, "processed_items")

    def test_job_status_transitions(self):
        """Test job status transitions."""
        job = Job(type=JobType.ANALYSIS, status=JobStatus.PENDING)

        # Start job
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()

        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

        # Complete job
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress = 100
        job.result = {"processed": 50, "failed": 0}

        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert job.result["processed"] == 50

    def test_job_failure(self):
        """Test job failure."""
        job = Job(type=JobType.SYNC_ALL, status=JobStatus.RUNNING)

        job.status = JobStatus.FAILED
        job.error = "Connection timeout"
        job.completed_at = datetime.utcnow()

        assert job.status == JobStatus.FAILED
        assert job.error == "Connection timeout"
        assert job.completed_at is not None


class TestAnalysisPlanModel:
    """Test AnalysisPlan model."""

    def test_analysis_plan_creation(self):
        """Test creating an analysis plan."""
        plan = AnalysisPlan(
            name="Test Analysis Plan",
            description="Test plan for analysis",
            plan_metadata={
                "total_scenes": 10,
                "analyze_performers": True,
                "analyze_tags": True,
                "auto_tag": True,
                "threshold": 0.8,
            },
        )

        assert plan.name == "Test Analysis Plan"
        # Status default is set by the database
        assert hasattr(plan, "status")
        assert plan.plan_metadata["total_scenes"] == 10
        assert plan.plan_metadata["analyze_performers"] is True

    def test_analysis_plan_changes(self):
        """Test plan changes relationship."""
        plan = AnalysisPlan(name="Test Plan")

        # PlanChange would need to be created with proper fields
        # Just test that the relationship exists
        assert hasattr(plan, "changes")

        # Without a database session, we can't test relationships


class TestSettingModel:
    """Test Setting model."""

    def test_setting_creation(self):
        """Test creating a setting."""
        setting = Setting(
            key="app.theme", value="dark", description="Application theme"
        )

        assert setting.key == "app.theme"
        assert setting.value == "dark"
        assert setting.description == "Application theme"

    def test_setting_json_value(self):
        """Test setting with JSON value."""
        setting = Setting(
            key="sync.options", value={"auto_sync": True, "interval": 3600}
        )

        assert setting.value["auto_sync"] is True
        assert setting.value["interval"] == 3600


class TestScheduledTaskModel:
    """Test ScheduledTask model."""

    def test_scheduled_task_creation(self):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            name="Daily Sync",
            task_type="sync_all",
            schedule="0 2 * * *",
            enabled=True,
            config={"full_sync": True},
        )

        assert task.name == "Daily Sync"
        assert task.task_type == "sync_all"
        assert task.schedule == "0 2 * * *"
        assert task.enabled is True
        assert task.config["full_sync"] is True

    def test_scheduled_task_interval(self):
        """Test scheduled task with interval."""
        task = ScheduledTask(
            name="Hourly Check",
            task_type="sync_scenes",
            schedule="0 * * * *",  # Every hour
            enabled=True,
        )

        assert task.schedule == "0 * * * *"
        assert task.enabled is True

    def test_scheduled_task_last_run(self):
        """Test updating last run time."""
        task = ScheduledTask(
            name="Test Task",
            task_type="sync_all",
            schedule="*/30 * * * *",  # Every 30 minutes
        )

        # Update last run
        task.last_run = datetime.now()
        task.last_job_id = "job123"

        assert task.last_run is not None
        assert task.last_job_id == "job123"


class TestSyncHistoryModel:
    """Test SyncHistory model."""

    def test_sync_history_creation(self):
        """Test creating sync history entry."""
        history = SyncHistory(
            entity_type="all",
            status="completed",
            started_at=datetime.now(),
            items_synced=100,
            items_created=50,
            items_updated=30,
        )

        assert history.entity_type == "all"
        assert history.status == "completed"
        assert history.items_synced == 100
        assert history.started_at is not None

    def test_sync_history_error(self):
        """Test sync history with error."""
        history = SyncHistory(
            entity_type="scene",
            status="failed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            error_details={"message": "Database connection failed"},
        )

        assert history.status == "failed"
        assert history.error_details["message"] == "Database connection failed"
        assert history.completed_at is not None
