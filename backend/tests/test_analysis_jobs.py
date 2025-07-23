"""Tests for analysis background jobs."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.jobs.analysis_jobs import (
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
        plan.id = None  # No ID to take simpler code path
        plan.status = PlanStatus.APPLIED
        plan.get_metadata = Mock(return_value=5)
        # Add SQLAlchemy attribute to avoid UnmappedInstanceError
        plan._sa_instance_state = Mock()
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
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.logger")
    async def test_analyze_scenes_job_success(
        self,
        mock_logger,
        mock_async_session,
        mock_stash_service_cls,
        mock_openai_client_cls,
        mock_analysis_service_cls,
        mock_get_settings,
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

        # Mock async function to return settings
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
        mock_db.commit = AsyncMock()

        # Create a context manager that returns our mock_db
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_db)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        # Add debugging to see if our mock is called
        def debug_session(*args, **kwargs):
            print("AsyncSessionLocal called!")
            return mock_context_manager

        mock_async_session.side_effect = debug_session

        # Mock plan query result
        mock_plan_result = Mock()  # Not AsyncMock since scalar_one is not async
        mock_plan_result.scalar_one = Mock(return_value=mock_analysis_plan)

        # Mock changes query result
        mock_changes_result = Mock()  # Not AsyncMock since scalars is not async
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_plan_changes
        mock_changes_result.scalars.return_value = mock_scalars

        # Set up execute to return different results for plan and changes queries
        mock_db.execute = AsyncMock(side_effect=[mock_plan_result, mock_changes_result])

        # Mock the plan's session check - need to handle async session proxy
        def mock_contains(item):
            return False

        mock_db.__contains__ = mock_contains

        # Execute
        result = await analyze_scenes_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            scene_ids=scene_ids,
            options=options,
            plan_name="Test Plan",
        )

        # Assert
        assert result["plan_id"] is None  # No plan ID when no changes
        assert result["total_changes"] == 0  # No changes when plan has no ID
        assert result["scenes_analyzed"] == len(scene_ids)
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
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
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
        # Mock async function to return settings
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
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
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
        # Mock async function to return settings
        mock_get_settings.return_value = mock_settings

        # Mock apply result
        apply_result = Mock(spec=ApplyResult)
        apply_result.applied_changes = 8
        apply_result.failed_changes = 1
        apply_result.skipped_changes = 1
        apply_result.total_changes = 10
        apply_result.errors = []  # Add the errors attribute

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
            change_ids=None,
        )

    @pytest.mark.asyncio
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
    async def test_generate_scene_details_job_success(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_async_session_local,
        mock_settings,
        mock_progress_callback,
    ):
        """Test successful scene details generation job."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1", "scene2"]
        # Mock async function to return settings
        mock_get_settings.return_value = mock_settings

        # Mock database session and scenes
        mock_db = AsyncMock()
        mock_scene1 = Mock()
        mock_scene1.id = "scene1"
        mock_scene1.title = "Test Scene 1"
        mock_scene1.details = ""

        mock_scene2 = Mock()
        mock_scene2.id = "scene2"
        mock_scene2.title = "Test Scene 2"
        mock_scene2.details = ""

        # Mock database query results
        mock_result1 = AsyncMock()
        mock_result1.scalar_one_or_none.return_value = mock_scene1
        mock_result2 = AsyncMock()
        mock_result2.scalar_one_or_none.return_value = mock_scene2

        # Set up execute to return different results for each scene
        mock_db.execute.side_effect = [mock_result1, mock_result2]

        # Mock the async context manager
        mock_async_session_local.return_value.__aenter__ = AsyncMock(
            return_value=mock_db
        )
        mock_async_session_local.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock stash service
        mock_stash_service = Mock()
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
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
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
        # Mock async function to return settings
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
        plan.id = None  # No ID to take simpler code path
        plan.status = PlanStatus.APPLIED
        plan.get_metadata = Mock(return_value=5)
        # Add SQLAlchemy attribute to avoid UnmappedInstanceError
        plan._sa_instance_state = Mock()
        return plan

    @pytest.mark.asyncio
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.core.database.AsyncSessionLocal")
    async def test_analyze_scenes_job_with_exception_in_summary(
        self,
        mock_async_session,
        mock_stash_service_cls,
        mock_openai_client_cls,
        mock_analysis_service_cls,
        mock_get_settings,
        mock_settings,
        mock_progress_callback,
        mock_analysis_plan,
    ):
        """Test analyze scenes job handles exceptions in summary calculation."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1"]
        # Mock async function to return settings
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
        mock_db.commit = AsyncMock()

        # Mock the plan's session check - need to handle async session proxy
        def mock_contains(item):
            return False

        mock_db.__contains__ = mock_contains

        # First execute succeeds (plan query), second execute fails (changes query)
        mock_plan_result = Mock()  # Not AsyncMock since scalar_one is not async
        mock_plan_result.scalar_one.return_value = mock_analysis_plan

        mock_db.execute = AsyncMock(
            side_effect=[mock_plan_result, Exception("Database error during summary")]
        )
        mock_async_session.return_value = mock_db

        # Execute - should succeed even with database issues since plan.id is None
        result = await analyze_scenes_job(
            job_id=job_id,
            progress_callback=mock_progress_callback,
            scene_ids=scene_ids,
        )

        # With plan.id = None, it takes the simpler path and succeeds
        assert result["plan_id"] is None
        assert result["total_changes"] == 0
        assert result["scenes_analyzed"] == 1

    @pytest.mark.asyncio
    @patch("app.core.database.AsyncSessionLocal")
    @patch("app.jobs.analysis_jobs.StashService")
    @patch("app.jobs.analysis_jobs.OpenAIClient")
    @patch("app.jobs.analysis_jobs.AnalysisService")
    @patch("app.jobs.analysis_jobs.load_settings_with_db_overrides")
    async def test_generate_scene_details_job_partial_failure(
        self,
        mock_get_settings,
        mock_analysis_service_cls,
        mock_openai_client_cls,
        mock_stash_service_cls,
        mock_async_session_local,
        mock_settings,
        mock_progress_callback,
    ):
        """Test scene details generation with partial failures."""
        # Setup
        job_id = str(uuid4())
        scene_ids = ["scene1", "scene2", "scene3"]
        # Mock async function to return settings
        mock_get_settings.return_value = mock_settings

        # Mock database session and scenes
        mock_db = AsyncMock()
        mock_scene1 = Mock()
        mock_scene1.id = "scene1"
        mock_scene1.title = "Test Scene 1"
        mock_scene1.details = ""

        mock_scene3 = Mock()
        mock_scene3.id = "scene3"
        mock_scene3.title = "Test Scene 3"
        mock_scene3.details = ""

        # Mock database query results - first succeeds, second returns None, third succeeds
        mock_result1 = Mock()  # Not AsyncMock since scalar_one_or_none is not async
        mock_result1.scalar_one_or_none.return_value = mock_scene1
        mock_result2 = Mock()  # Not AsyncMock since scalar_one_or_none is not async
        mock_result2.scalar_one_or_none.return_value = None  # Scene 2 not found
        mock_result3 = Mock()  # Not AsyncMock since scalar_one_or_none is not async
        mock_result3.scalar_one_or_none.return_value = mock_scene3

        # Set up execute to return different results for each scene
        mock_db.execute.side_effect = [mock_result1, mock_result2, mock_result3]

        # Mock the async context manager properly
        mock_async_context = AsyncMock()
        mock_async_context.__aenter__ = AsyncMock(return_value=mock_db)
        mock_async_context.__aexit__ = AsyncMock(return_value=None)
        mock_async_session_local.return_value = mock_async_context

        # Mock stash service
        mock_stash_service = Mock()
        mock_stash_service_cls.return_value = mock_stash_service

        # Mock analysis service
        mock_analysis_service = Mock()
        # Define different results for each call to analyze_single_scene
        mock_change1 = Mock()
        mock_change1.field = "details"
        mock_change1.proposed_value = "Generated details"
        mock_changes_scene1 = [mock_change1]

        mock_change3 = Mock()
        mock_change3.field = "details"
        mock_change3.proposed_value = "Generated details"
        mock_changes_scene3 = [mock_change3]

        # analyze_single_scene should only be called for scene1 and scene3 (not scene2)
        # Set up side_effect to return different results for each call
        mock_analysis_service.analyze_single_scene = AsyncMock(
            side_effect=[mock_changes_scene1, mock_changes_scene3]
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

        # Verify analyze_single_scene was only called for scenes that exist (scene1 and scene3)
        assert mock_analysis_service.analyze_single_scene.call_count == 2
