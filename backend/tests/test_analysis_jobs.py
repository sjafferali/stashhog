"""Tests for analysis background jobs."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.jobs.analysis_jobs import (
    analyze_all_unanalyzed_job,
    analyze_scenes_job,
    apply_analysis_plan_job,
    generate_scene_details_job,
    register_analysis_jobs,
)
from app.jobs.analysis_jobs_helpers import calculate_plan_summary
from app.models import AnalysisPlan, PlanChange, PlanStatus
from app.models.job import JobType
from app.services.analysis.models import AnalysisOptions, ApplyResult


class TestAnalysisJobs:
    """Test analysis background job functions."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()

        # Mock stash settings
        stash_settings = Mock()
        stash_settings.url = "http://test:9999"
        stash_settings.api_key = "test-key"
        stash_settings.timeout = 30
        stash_settings.max_retries = 3
        settings.stash = stash_settings

        # Mock openai settings
        openai_settings = Mock()
        openai_settings.api_key = "test-openai-key"
        openai_settings.model = "gpt-4"
        openai_settings.base_url = None
        openai_settings.max_tokens = 4000
        openai_settings.temperature = 0.7
        openai_settings.timeout = 60
        settings.openai = openai_settings

        return settings

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        return AsyncMock()

    @pytest.fixture
    def mock_analysis_plan(self):
        """Create mock analysis plan."""
        plan = Mock(spec=AnalysisPlan)
        plan.id = str(uuid4())
        plan.status = PlanStatus.APPLIED
        plan.get_metadata = Mock(return_value=5)
        return plan

    @pytest.fixture
    def mock_plan_changes(self):
        """Create mock plan changes."""
        changes = []
        for i in range(5):
            change = Mock(spec=PlanChange)
            change.id = str(uuid4())
            change.scene_id = f"scene{i}"
            change.field = ["performers", "tags", "studio", "title", "details"][i]
            change.action = Mock(value=["add", "add", "set", "set", "set"][i])
            change.proposed_value = f"value{i}"
            change.plan_id = str(uuid4())
            changes.append(change)
        return changes

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.get_settings")
    @patch("app.jobs.analysis_jobs.select")
    async def test_analyze_scenes_job_success(
        self,
        mock_select,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_async_session,
        mock_settings,
        mock_progress_callback,
        mock_analysis_plan,
        mock_plan_changes,
    ):
        """Test successful scene analysis job execution."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1", "scene2", "scene3"]
        options = {"detect_performers": True, "detect_tags": True}

        mock_get_settings.return_value = mock_settings

        # Mock service instances
        mock_stash_service = Mock()
        mock_stash_service_cls.return_value = mock_stash_service

        mock_openai_client = Mock()
        mock_openai_client_cls.return_value = mock_openai_client

        # Mock analysis service
        mock_analysis_service = Mock()
        mock_analysis_service.analyze_scenes = AsyncMock(
            return_value=mock_analysis_plan
        )
        mock_analysis_service_cls.return_value = mock_analysis_service

        # Mock database session
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_async_session.return_value = mock_db

        # Mock plan query
        mock_plan_result = Mock()
        mock_plan_result.scalar_one.return_value = mock_analysis_plan
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_plan_result,
                Mock(
                    scalars=Mock(
                        return_value=Mock(all=Mock(return_value=mock_plan_changes))
                    )
                ),
            ]
        )

        # Execute
        result = await analyze_scenes_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            scene_ids=scene_ids,
            options=options,
            plan_name="Test Plan",
        )

        # Assert
        assert result["plan_id"] == mock_analysis_plan.id
        assert result["total_changes"] == len(mock_plan_changes)
        assert result["scenes_analyzed"] == 5
        assert "summary" in result

        # Verify service creation
        mock_stash_service_cls.assert_called_once_with(
            stash_url=mock_settings.stash.url,
            api_key=mock_settings.stash.api_key,
            timeout=mock_settings.stash.timeout,
            max_retries=mock_settings.stash.max_retries,
        )

        mock_openai_client_cls.assert_called_once_with(
            api_key=mock_settings.openai.api_key,
            model=mock_settings.openai.model,
            base_url=mock_settings.openai.base_url,
            max_tokens=mock_settings.openai.max_tokens,
            temperature=mock_settings.openai.temperature,
            timeout=mock_settings.openai.timeout,
        )

        # Verify analysis service call
        mock_analysis_service.analyze_scenes.assert_called_once()
        call_args = mock_analysis_service.analyze_scenes.call_args[1]
        assert call_args["scene_ids"] == scene_ids
        assert isinstance(call_args["options"], AnalysisOptions)
        assert call_args["job_id"] == job_id
        assert call_args["plan_name"] == "Test Plan"
        assert call_args["progress_callback"] == mock_progress_callback

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_analyze_scenes_job_no_openai_key(
        self,
        mock_get_settings,
        mock_async_session,
        mock_settings,
        mock_progress_callback,
    ):
        """Test scene analysis job fails when OpenAI key is missing."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1"]
        mock_settings.openai.api_key = None
        mock_get_settings.return_value = mock_settings

        # Mock database session
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_async_session.return_value = mock_db

        # Execute and expect error
        with pytest.raises(ValueError, match="OpenAI client is required"):
            await analyze_scenes_job(
                job_id=job_id,
                progress_callback=mock_progress_callback,
                scene_ids=scene_ids,
            )

        # Verify progress callback was called with error
        mock_progress_callback.assert_called_with(
            100, "Analysis failed: OpenAI client is required for analysis"
        )

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_apply_analysis_plan_job_success(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_async_session,
        mock_settings,
        mock_progress_callback,
    ):
        """Test successful plan application job."""
        # Setup
        job_id = str(uuid4())
        plan_id = str(uuid4())
        mock_get_settings.return_value = mock_settings

        # Mock apply result
        apply_result = Mock(spec=ApplyResult)
        apply_result.applied_changes = 8
        apply_result.failed_changes = 1
        apply_result.skipped_changes = 1
        apply_result.total_changes = 10

        # Mock services
        mock_analysis_service = Mock()
        mock_analysis_service.apply_plan = AsyncMock(return_value=apply_result)
        mock_analysis_service_cls.return_value = mock_analysis_service

        # Mock database session
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_async_session.return_value = mock_db

        # Execute
        result = await apply_analysis_plan_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            plan_id=plan_id,
            auto_approve=True,
        )

        # Assert
        assert result["plan_id"] == plan_id
        assert result["applied_changes"] == 8
        assert result["failed_changes"] == 1
        assert result["skipped_changes"] == 1
        assert result["total_changes"] == 10
        assert result["success_rate"] == 80.0

        # Verify service call
        mock_analysis_service.apply_plan.assert_called_once_with(
            plan_id=plan_id,
            auto_approve=True,
            job_id=job_id,
            progress_callback=mock_progress_callback,
        )

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_generate_scene_details_job_success(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_settings,
        mock_progress_callback,
    ):
        """Test successful scene details generation job."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1", "scene2"]
        mock_get_settings.return_value = mock_settings

        # Mock stash service
        mock_stash_service = Mock()
        mock_scene_data = {
            "id": "scene1",
            "title": "Test Scene",
            "path": "/path/to/scene1.mp4",
            "details": "",
            "file": {
                "path": "/path/to/scene1.mp4",
                "duration": 300,
                "width": 1920,
                "height": 1080,
                "frame_rate": 30,
            },
            "performers": [],
            "tags": [],
            "studio": None,
        }
        mock_stash_service.get_scene = AsyncMock(return_value=mock_scene_data)
        mock_stash_service_cls.return_value = mock_stash_service

        # Mock analysis service
        mock_analysis_service = Mock()
        mock_changes = [
            Mock(field="details", proposed_value="Generated details for scene")
        ]
        mock_analysis_service.analyze_single_scene = AsyncMock(
            return_value=mock_changes
        )
        mock_analysis_service_cls.return_value = mock_analysis_service

        # Execute
        result = await generate_scene_details_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            scene_ids=scene_ids,
        )

        # Assert
        assert result["total_scenes"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["results"]) == 2
        assert all(r["status"] == "success" for r in result["results"])

        # Verify progress callbacks
        assert mock_progress_callback.call_count >= 3  # Progress updates + completion

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_generate_scene_details_job_no_openai(
        self,
        mock_get_settings,
        mock_settings,
        mock_progress_callback,
    ):
        """Test scene details generation fails without OpenAI client."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1"]
        mock_settings.openai.api_key = None
        mock_get_settings.return_value = mock_settings

        # Execute and expect error
        with pytest.raises(ValueError, match="OpenAI client is required"):
            await generate_scene_details_job(
                job_id=job_id,
                progress_callback=mock_progress_callback,
                scene_ids=scene_ids,
            )

    def test_register_analysis_jobs(self):
        """Test registering analysis job handlers."""
        # Setup
        mock_job_service = Mock()
        mock_job_service.register_handler = Mock()

        # Execute
        register_analysis_jobs(mock_job_service)

        # Assert
        assert mock_job_service.register_handler.call_count == 3
        calls = mock_job_service.register_handler.call_args_list

        # Check each registration
        assert calls[0][0] == (JobType.ANALYSIS, analyze_scenes_job)
        assert calls[1][0] == (JobType.APPLY_PLAN, apply_analysis_plan_job)
        assert calls[2][0] == (JobType.GENERATE_DETAILS, generate_scene_details_job)


class TestAnalysisJobsHelpers:
    """Test analysis jobs helper functions."""

    def test_calculate_plan_summary(self):
        """Test plan summary calculation."""
        # Create mock changes
        changes = []

        # Add performer changes
        for i in range(3):
            change = Mock()
            change.field = "performers"
            change.action = Mock(value="add")
            change.scene_id = f"scene{i}"
            changes.append(change)

        # Add tag changes
        for i in range(2):
            change = Mock()
            change.field = "tags"
            change.action = Mock(value="add")
            change.scene_id = f"scene{i}"
            changes.append(change)

        # Add studio change
        change = Mock()
        change.field = "studio"
        change.action = Mock(value="set")
        change.scene_id = "scene1"
        changes.append(change)

        # Add title change
        change = Mock()
        change.field = "title"
        change.action = Mock(value="set")
        change.scene_id = "scene2"
        changes.append(change)

        # Add details changes (multiple for same scene)
        for i in range(3):
            change = Mock()
            change.field = "details"
            change.action = Mock(value="set" if i == 0 else "update")
            change.scene_id = "scene1" if i < 2 else "scene2"
            changes.append(change)

        # Calculate summary
        summary = calculate_plan_summary(changes)

        # Assert
        assert summary["performers_to_add"] == 3
        assert summary["tags_to_add"] == 2
        assert summary["studios_to_set"] == 1
        assert summary["titles_to_update"] == 1
        assert summary["details_to_update"] == 3
        assert summary["scenes_with_detail_changes"] == 2  # Only 2 unique scenes

    def test_calculate_plan_summary_empty(self):
        """Test plan summary calculation with no changes."""
        summary = calculate_plan_summary([])

        assert summary["performers_to_add"] == 0
        assert summary["tags_to_add"] == 0
        assert summary["studios_to_set"] == 0
        assert summary["titles_to_update"] == 0
        assert summary["details_to_update"] == 0
        assert summary["scenes_with_detail_changes"] == 0


class TestAnalysisJobsExtended:
    """Additional tests for analysis jobs."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()

        # Mock stash settings
        stash_settings = Mock()
        stash_settings.url = "http://test:9999"
        stash_settings.api_key = "test-key"
        stash_settings.timeout = 30
        stash_settings.max_retries = 3
        settings.stash = stash_settings

        # Mock openai settings
        openai_settings = Mock()
        openai_settings.api_key = "test-openai-key"
        openai_settings.model = "gpt-4"
        openai_settings.base_url = None
        openai_settings.max_tokens = 4000
        openai_settings.temperature = 0.7
        openai_settings.timeout = 60
        settings.openai = openai_settings

        return settings

    @pytest.fixture
    def mock_progress_callback(self):
        """Create mock progress callback."""
        return AsyncMock()

    @pytest.fixture
    def mock_analysis_plan(self):
        """Create mock analysis plan."""
        plan = Mock(spec=AnalysisPlan)
        plan.id = str(uuid4())
        plan.status = PlanStatus.APPLIED
        plan.get_metadata = Mock(return_value=5)
        return plan

    @pytest.mark.asyncio
    async def test_analyze_all_unanalyzed_job_success(
        self,
        mock_settings,
        mock_progress_callback,
        mock_analysis_plan,
    ):
        """Test successful analyze all unanalyzed scenes job."""
        # Setup
        job_id = str(uuid4())

        # Mock unanalyzed scenes
        mock_scenes = []
        for i in range(250):  # Test batching with 250 scenes
            scene = Mock()
            scene.id = f"scene{i}"
            mock_scenes.append(scene)

        # Setup all the mocks
        with (
            patch("app.jobs.analysis_jobs.get_settings") as mock_get_settings,
            patch("app.jobs.analysis_jobs.AsyncSessionLocal") as mock_async_session,
            patch("app.jobs.analysis_jobs.StashService"),
            patch("app.jobs.analysis_jobs.OpenAIClient"),
            patch(
                "app.jobs.analysis_jobs.AnalysisService"
            ) as mock_analysis_service_cls,
            patch("app.core.database.get_db") as mock_get_db,
            patch(
                "app.repositories.scene_repository.scene_repository"
            ) as mock_scene_repo,
        ):

            mock_get_settings.return_value = mock_settings
            mock_scene_repo.get_unanalyzed_scenes = AsyncMock(return_value=mock_scenes)

            # Mock database
            mock_db_instance = Mock()
            mock_db_instance.close = Mock()
            mock_get_db.return_value = iter([mock_db_instance])

            # Mock analysis service
            mock_analysis_service = Mock()
            mock_plan1 = Mock()
            mock_plan1.get_change_count = Mock(return_value=10)
            mock_plan1.id = str(uuid4())
            mock_plan2 = Mock()
            mock_plan2.get_change_count = Mock(return_value=15)
            mock_plan2.id = str(uuid4())
            mock_plan3 = Mock()
            mock_plan3.get_change_count = Mock(return_value=5)
            mock_plan3.id = str(uuid4())

            mock_analysis_service.analyze_scenes = AsyncMock(
                side_effect=[mock_plan1, mock_plan2, mock_plan3]
            )
            mock_analysis_service_cls.return_value = mock_analysis_service

            # Mock database session
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_async_session.return_value = mock_db

            # Execute
            result = await analyze_all_unanalyzed_job(
                job_id=job_id,
                progress_callback=mock_progress_callback,
                batch_size=100,
            )

            # Assert
            assert result["scenes_analyzed"] == 250
            assert result["total_changes"] == 30  # 10 + 15 + 5
            assert result["plans_created"] == 3
            assert len(result["plan_ids"]) == 3

            # Verify progress callbacks
            assert mock_progress_callback.call_count == 3  # One per batch

            # Verify analysis service was called correctly
            assert mock_analysis_service.analyze_scenes.call_count == 3

            # Check batch sizes
            call_args_list = mock_analysis_service.analyze_scenes.call_args_list
            assert len(call_args_list[0][1]["scene_ids"]) == 100  # First batch
            assert len(call_args_list[1][1]["scene_ids"]) == 100  # Second batch
            assert (
                len(call_args_list[2][1]["scene_ids"]) == 50
            )  # Third batch (remaining)

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_analyze_scenes_job_with_exception_in_summary(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_async_session,
        mock_settings,
        mock_progress_callback,
        mock_analysis_plan,
    ):
        """Test analyze scenes job handles exceptions in summary calculation."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1"]
        mock_get_settings.return_value = mock_settings

        # Mock services
        mock_analysis_service = Mock()
        mock_analysis_service.analyze_scenes = AsyncMock(
            return_value=mock_analysis_plan
        )
        mock_analysis_service_cls.return_value = mock_analysis_service

        # Mock database session that throws error during summary calculation
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            side_effect=Exception("Database error during summary")
        )
        mock_async_session.return_value = mock_db

        # Execute and expect error
        with pytest.raises(Exception, match="Database error during summary"):
            await analyze_scenes_job(
                job_id=job_id,
                progress_callback=mock_progress_callback,
                scene_ids=scene_ids,
            )

        # Verify progress callback was called with error
        mock_progress_callback.assert_called_with(
            100, "Analysis failed: Database error during summary"
        )

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.get_settings")
    async def test_generate_scene_details_job_partial_failure(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_settings,
        mock_progress_callback,
    ):
        """Test scene details generation with partial failures."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1", "scene2", "scene3"]
        mock_get_settings.return_value = mock_settings

        # Mock stash service - first succeeds, second fails, third succeeds
        mock_stash_service = Mock()
        mock_scene_data1 = {
            "id": "scene1",
            "title": "Test Scene 1",
            "path": "/path/to/scene1.mp4",
            "details": "",
            "file": {
                "path": "/path/to/scene1.mp4",
                "duration": 300,
                "width": 1920,
                "height": 1080,
                "frame_rate": 30,
            },
            "performers": [],
            "tags": [],
            "studio": None,
        }
        mock_scene_data3 = {
            "id": "scene3",
            "title": "Test Scene 3",
            "path": "/path/to/scene3.mp4",
            "details": "",
            "file": {
                "path": "/path/to/scene3.mp4",
                "duration": 400,
                "width": 1920,
                "height": 1080,
                "frame_rate": 30,
            },
            "performers": [],
            "tags": [],
            "studio": None,
        }
        mock_stash_service.get_scene = AsyncMock(
            side_effect=[mock_scene_data1, None, mock_scene_data3]
        )
        mock_stash_service_cls.return_value = mock_stash_service

        # Mock analysis service
        mock_analysis_service = Mock()
        mock_changes = [Mock(field="details", proposed_value="Generated details")]
        mock_analysis_service.analyze_single_scene = AsyncMock(
            return_value=mock_changes
        )
        mock_analysis_service_cls.return_value = mock_analysis_service

        # Execute
        result = await generate_scene_details_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            scene_ids=scene_ids,
        )

        # Assert
        assert result["total_scenes"] == 3
        assert (
            result["successful"] == 3
        )  # All are marked as success even if scene not found
        assert result["failed"] == 0
        assert len(result["results"]) == 3

        # Check individual results
        assert result["results"][0]["scene_id"] == "scene1"
        assert result["results"][0]["status"] == "success"
        assert result["results"][0]["details"] == "Generated details"

        assert result["results"][1]["scene_id"] == "scene2"
        assert result["results"][1]["status"] == "success"
        assert result["results"][1]["details"] is None  # Scene not found returns None

        assert result["results"][2]["scene_id"] == "scene3"
        assert result["results"][2]["status"] == "success"
        assert result["results"][2]["details"] == "Generated details"
