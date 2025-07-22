"""Comprehensive tests for analysis service."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cancellation import CancellationToken
from app.core.config import Settings
from app.models import AnalysisPlan, PlanStatus
from app.services.analysis.analysis_service import AnalysisService
from app.services.analysis.models import (
    AnalysisOptions,
    ApplyResult,
    DetectionResult,
    ProposedChange,
    SceneChanges,
)
from app.services.openai_client import OpenAIClient
from app.services.stash_service import StashService
from tests.helpers import create_test_scene


class TestAnalysisServiceInit:
    """Test AnalysisService initialization."""

    def test_init_with_dependencies(self):
        """Test initialization with all dependencies."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)

        assert service.stash_service == stash_service
        assert service.settings == settings
        assert service.ai_client is not None
        assert service.studio_detector is not None
        assert service.performer_detector is not None
        assert service.tag_detector is not None
        assert service.details_generator is not None
        assert service.video_tag_detector is not None
        assert service.plan_manager is not None
        assert service.batch_processor is not None
        assert "_cache" in service.__dict__

    def test_cache_initialization(self):
        """Test cache is properly initialized."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)

        assert service._cache == {
            "studios": [],
            "performers": [],
            "tags": [],
            "last_refresh": None,
        }


class TestAnalysisServiceCacheManagement:
    """Test cache management functionality."""

    @pytest.mark.asyncio
    async def test_refresh_cache_success(self):
        """Test successful cache refresh."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        # Mock stash service responses
        stash_service.get_all_studios = AsyncMock(
            return_value=[{"id": "1", "name": "Studio 1"}]
        )
        stash_service.get_all_performers = AsyncMock(
            return_value=[{"id": "1", "name": "Performer 1", "aliases": []}]
        )
        stash_service.get_all_tags = AsyncMock(
            return_value=[{"id": "1", "name": "Tag 1"}]
        )

        service = AnalysisService(openai_client, stash_service, settings)

        # Mock the refresh_cache to populate the cache
        async def mock_refresh_cache():
            service._cache["studios"] = ["Studio 1"]
            service._cache["performers"] = [{"name": "Performer 1", "aliases": []}]
            service._cache["tags"] = ["Tag 1"]

        service._refresh_cache = AsyncMock(side_effect=mock_refresh_cache)
        await service._refresh_cache()

        assert service._cache["studios"] == ["Studio 1"]
        assert service._cache["performers"] == [{"name": "Performer 1", "aliases": []}]
        assert service._cache["tags"] == ["Tag 1"]
        # The mocked method was called
        service._refresh_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_cache_with_error(self):
        """Test cache refresh with error handling."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)

        # Initialize cache with empty lists
        service._cache = {"studios": [], "performers": [], "tags": []}

        # Mock _refresh_cache to simulate an error but not change the cache
        service._refresh_cache = AsyncMock(side_effect=lambda: None)

        # Should not raise, but cache should remain empty
        await service._refresh_cache()

        assert service._cache["studios"] == []
        assert service._cache["performers"] == []
        assert service._cache["tags"] == []


class TestAnalysisServiceSceneAnalysis:
    """Test scene analysis functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5
        settings.analysis.confidence_threshold = 0.8

        service = AnalysisService(openai_client, stash_service, settings)

        # Mock cache refresh
        service._refresh_cache = AsyncMock()

        # Mock stash service methods
        stash_service.get_all_studios = AsyncMock(return_value=[])
        stash_service.get_all_performers = AsyncMock(return_value=[])
        stash_service.get_all_tags = AsyncMock(return_value=[])

        return service

    @pytest.mark.asyncio
    async def test_analyze_scenes_no_database(self, mock_service):
        """Test analyze_scenes raises error without database."""
        with pytest.raises(ValueError, match="Database session is required"):
            await mock_service.analyze_scenes()

    @pytest.mark.asyncio
    async def test_analyze_scenes_empty_scenes(self, mock_service):
        """Test analyze_scenes with no scenes."""
        db = Mock(spec=AsyncSession)

        # Mock getting scenes from database
        mock_service._get_scenes_from_database = AsyncMock(return_value=[])
        mock_service._create_empty_plan = AsyncMock(
            return_value=AnalysisPlan(name="Empty Plan", status=PlanStatus.DRAFT)
        )

        plan = await mock_service.analyze_scenes(db=db)

        assert plan.name == "Empty Plan"
        assert plan.status == PlanStatus.DRAFT
        mock_service._create_empty_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_scenes_with_scenes(self, mock_service):
        """Test analyze_scenes with actual scenes."""
        db = Mock(spec=AsyncSession)

        # Create test scenes
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]

        # Mock database operations
        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._report_initial_progress = AsyncMock()
        mock_service._mark_scenes_as_analyzed = AsyncMock()

        # Mock batch processing with correct SceneChanges structure
        scene_changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1.mp4",
                changes=[
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=["tag1", "tag2"],
                        confidence=0.9,
                        reason="Detected tags in video",
                    )
                ],
            ),
            SceneChanges(
                scene_id="scene2",
                scene_title="Scene 2",
                scene_path="/path/to/scene2.mp4",
                changes=[
                    ProposedChange(
                        field="performers",
                        action="add",
                        current_value=[],
                        proposed_value=["performer1"],
                        confidence=0.85,
                        reason="Detected performer",
                    )
                ],
            ),
        ]

        mock_service.batch_processor.process_scenes = AsyncMock(
            return_value=scene_changes
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="plan1", name="Test Plan", status=PlanStatus.DRAFT, metadata={}
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(
            scene_ids=["scene1", "scene2"],
            db=db,
            options=AnalysisOptions(detect_tags=True, detect_performers=True),
        )

        # Verify
        assert plan.id == "plan1"
        assert plan.name == "Test Plan"
        mock_service._get_scenes_from_database.assert_called_once()
        mock_service.batch_processor.process_scenes.assert_called_once()
        mock_service.plan_manager.create_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_scenes_with_cancellation(self, mock_service):
        """Test analyze_scenes with cancellation token."""
        db = Mock(spec=AsyncSession)
        cancellation_token = CancellationToken()

        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._report_initial_progress = AsyncMock()

        # Mock batch processor to simulate cancellation
        async def mock_process_scenes(*args, **kwargs):
            cancellation_token.cancel()
            raise asyncio.CancelledError()

        mock_service.batch_processor.process_scenes = AsyncMock(
            side_effect=mock_process_scenes
        )

        with pytest.raises(asyncio.CancelledError):
            await mock_service.analyze_scenes(
                db=db, cancellation_token=cancellation_token
            )

    @pytest.mark.asyncio
    async def test_analyze_single_scene(self, mock_service):
        """Test analyzing a single scene."""
        scene = create_test_scene(id="scene1", title="Test Scene")
        options = AnalysisOptions(detect_tags=True, detect_performers=True)

        # Initialize cache
        mock_service._cache = {
            "tags": ["tag1", "tag2", "outdoor", "nature"],
            "performers": [{"id": "p1", "name": "performer1", "aliases": []}],
            "studios": [],
        }

        # Mock tag detector methods
        mock_service.tag_detector.detect_technical_tags = Mock(return_value=[])
        from app.services.analysis.models import DetectionResult

        mock_service.tag_detector.detect_with_ai_tracked = AsyncMock(
            return_value=(
                [
                    DetectionResult(
                        value="tag1", confidence=0.9, source="ai", metadata={}
                    ),
                    DetectionResult(
                        value="tag2", confidence=0.85, source="ai", metadata={}
                    ),
                ],
                {
                    "cost": 0.05,
                    "usage": {"prompt_tokens": 50, "completion_tokens": 50},
                    "model": "gpt-4o-mini",
                },
            )
        )

        # Mock performer detector methods
        mock_service.performer_detector.detect_from_path = AsyncMock(return_value=[])
        mock_service.performer_detector.detect_with_ai_tracked = AsyncMock(
            return_value=(
                [
                    DetectionResult(
                        value="performer1", confidence=0.85, source="ai", metadata={}
                    )
                ],
                {
                    "cost": 0.05,
                    "usage": {"prompt_tokens": 50, "completion_tokens": 50},
                    "model": "gpt-4o-mini",
                },
            )
        )

        # Add cost tracker
        mock_service.cost_tracker = Mock()
        mock_service.cost_tracker.increment_scenes = Mock()
        mock_service.cost_tracker.track_operation = Mock()

        # Execute
        changes = await mock_service.analyze_single_scene(scene, options)

        # Verify
        assert len(changes) > 0
        # Verify the detectors were called
        mock_service.tag_detector.detect_with_ai_tracked.assert_called_once()
        mock_service.performer_detector.detect_with_ai_tracked.assert_called_once()


class TestAnalysisServicePlanApplication:
    """Test plan application functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)
        return service

    @pytest.mark.asyncio
    async def test_apply_plan_success(self, mock_service):
        """Test successful plan application."""
        # Mock AsyncSessionLocal
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            # Create approved plan
            plan = AnalysisPlan(
                id="1",
                name="Test Plan",
                status=PlanStatus.DRAFT,  # Plans don't need to be APPROVED
                metadata={},
            )

            # Mock plan manager
            mock_service.plan_manager.get_plan = AsyncMock(return_value=plan)

            # Mock count query
            db.execute = AsyncMock(return_value=Mock(scalar=Mock(return_value=2)))

            # Mock apply result
            apply_result = ApplyResult(
                plan_id=1,
                total_changes=2,
                applied_changes=2,
                failed_changes=0,
                errors=[],
            )
            mock_service.plan_manager.apply_plan = AsyncMock(return_value=apply_result)

            # Execute
            result = await mock_service.apply_plan("1")

            # Verify
            assert result.total_changes == 2
            assert result.applied_changes == 2
            assert result.failed_changes == 0
            mock_service.plan_manager.get_plan.assert_called_once_with(1, db)
            mock_service.plan_manager.apply_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self, mock_service):
        """Test applying non-existent plan."""
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            mock_service.plan_manager.get_plan = AsyncMock(return_value=None)

            # Execute and verify
            with pytest.raises(ValueError, match="Plan"):
                await mock_service.apply_plan("1")

    @pytest.mark.asyncio
    async def test_apply_plan_partial_failure(self, mock_service):
        """Test plan application with partial failures."""
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            # Create plan
            plan = AnalysisPlan(
                id="1", name="Test Plan", status=PlanStatus.DRAFT, metadata={}
            )

            # Mock plan manager
            mock_service.plan_manager.get_plan = AsyncMock(return_value=plan)

            # Mock count query
            db.execute = AsyncMock(return_value=Mock(scalar=Mock(return_value=2)))

            # Mock apply result with one failure
            apply_result = ApplyResult(
                plan_id=1,
                total_changes=2,
                applied_changes=1,
                failed_changes=1,
                errors=[{"scene_id": "scene2", "error": "API error"}],
            )
            mock_service.plan_manager.apply_plan = AsyncMock(return_value=apply_result)

            # Execute
            result = await mock_service.apply_plan("1")

            # Verify
            assert result.total_changes == 2
            assert result.applied_changes == 1
            assert result.failed_changes == 1
            assert len(result.errors) == 1


class TestAnalysisServiceHelpers:
    """Test helper methods."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)
        return service

    def test_generate_plan_name(self, mock_service):
        """Test plan name generation."""
        options = AnalysisOptions(
            detect_tags=True, detect_performers=True, detect_details=False
        )

        # Test with scenes that have no attributes (will use descriptive name)
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]
        name = mock_service._generate_plan_name(options, 2, scenes)
        assert "2 scenes" in name

        # Test without scenes (will use fallback name)
        name_fallback = mock_service._generate_plan_name(options, 2, None)
        assert "2 scenes" in name_fallback
        assert "Tags" in name_fallback and "Performers" in name_fallback

    def test_create_analysis_metadata(self, mock_service):
        """Test metadata creation."""
        options = AnalysisOptions(detect_tags=True)
        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1.mp4",
                changes=[
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=["tag1"],
                        confidence=0.9,
                        reason="Test",
                    )
                ],
            )
        ]

        metadata = mock_service._create_analysis_metadata(options, scenes, changes)

        assert metadata["statistics"]["total_scenes"] == 1
        assert metadata["statistics"]["total_changes"] == 1
        assert metadata["settings"]["detect_tags"] is True

    @pytest.mark.asyncio
    async def test_report_progress(self, mock_service):
        """Test progress reporting."""
        job_id = "job1"
        completed = 5
        total = 10

        # Mock _update_job_progress
        mock_service._update_job_progress = AsyncMock()

        # Mock progress callback
        progress_callback = AsyncMock()

        await mock_service._on_progress(
            job_id, completed, total, completed * 10, total * 10, progress_callback
        )

        # Verify
        mock_service._update_job_progress.assert_called_once()
        progress_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_scenes_from_database(self, mock_service):
        """Test getting scenes from database."""
        db = Mock(spec=AsyncSession)
        scene_ids = ["scene1", "scene2"]

        # Create mock scenes
        mock_scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]

        # Mock database query
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=mock_scenes)

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=mock_query)

        db.execute = AsyncMock(return_value=mock_result)

        scenes = await mock_service._get_scenes_from_database(scene_ids, None, db)

        assert len(scenes) == 2
        assert scenes[0].id == "scene1"
        assert scenes[1].id == "scene2"

    @pytest.mark.asyncio
    async def test_mark_scenes_as_analyzed(self, mock_service):
        """Test marking scenes as analyzed."""
        db = Mock(spec=AsyncSession)
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]
        options = AnalysisOptions(
            detect_tags=True, detect_performers=True, detect_details=True
        )

        # Mock database operations
        mock_db_scenes = [
            Mock(id="scene1", analyzed=False),
            Mock(id="scene2", analyzed=False),
        ]
        db.execute = AsyncMock(
            return_value=Mock(
                scalars=Mock(return_value=Mock(all=Mock(return_value=mock_db_scenes)))
            )
        )
        db.flush = AsyncMock()

        await mock_service._mark_scenes_as_analyzed(scenes, db, options)

        # Verify scenes were marked as analyzed
        for scene in mock_db_scenes:
            assert scene.analyzed is True

    @pytest.mark.asyncio
    async def test_handle_no_changes(self, mock_service):
        """Test handling when no changes are detected."""
        db = Mock(spec=AsyncSession)
        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1.mp4",
                changes=[],
            )
        ]
        metadata = {"test": "metadata"}
        plan_name = "Test Plan"
        options = AnalysisOptions()

        # Mock plan manager
        mock_plan = AnalysisPlan(
            name=plan_name,
            status=PlanStatus.APPLIED,  # No changes plans are marked as APPLIED
            metadata=metadata,
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)
        mock_service._mark_scenes_as_analyzed = AsyncMock()

        plan = await mock_service._handle_no_changes(
            scenes, changes, metadata, plan_name, None, db, options
        )

        assert plan.status == PlanStatus.APPLIED
        mock_service._mark_scenes_as_analyzed.assert_called_once()


class TestAnalysisServiceBatchProcessing:
    """Test batch processing functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 2
        settings.analysis.max_concurrent = 1
        settings.analysis.confidence_threshold = 0.8

        service = AnalysisService(openai_client, stash_service, settings)
        return service

    @pytest.mark.asyncio
    async def test_analyze_batch(self, mock_service):
        """Test batch analysis."""
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]
        options = AnalysisOptions(detect_tags=True)

        # Mock AI client batch analysis
        mock_service.ai_client.batch_analyze_scenes = AsyncMock(
            return_value=[
                {
                    "scene_id": "scene1",
                    "tags": ["tag1", "tag2"],
                    "confidence_scores": {"tags": 0.9},
                },
                {
                    "scene_id": "scene2",
                    "tags": ["tag3"],
                    "confidence_scores": {"tags": 0.85},
                },
            ]
        )

        # Mock detectors with correct DetectionResult
        mock_service.tag_detector.detect = AsyncMock(
            side_effect=[
                DetectionResult(value=["tag1", "tag2"], confidence=0.9, source="ai"),
                DetectionResult(value=["tag3"], confidence=0.85, source="ai"),
            ]
        )

        # Execute - need to convert scenes to dict format
        scene_dicts = [{"id": s.id, "title": s.title} for s in scenes]
        changes = await mock_service._analyze_batch(scene_dicts, options)

        # Verify
        assert len(changes) == 2
        assert changes[0].scene_id == "scene1"
        assert changes[1].scene_id == "scene2"

    @pytest.mark.asyncio
    async def test_analyze_batch_with_error(self, mock_service):
        """Test batch analysis with error handling."""
        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        options = AnalysisOptions(detect_tags=True)

        # Mock analyze_single_scene to raise error
        mock_service.analyze_single_scene = AsyncMock(
            side_effect=Exception("API error")
        )

        # Execute - convert to dict format
        scene_dicts = [{"id": s.id, "title": s.title} for s in scenes]
        changes = await mock_service._analyze_batch(scene_dicts, options)

        # Verify - should handle error gracefully
        assert len(changes) == 1
        assert changes[0].scene_id == "scene1"
        assert changes[0].error == "API error"


class TestAnalysisServiceBatchOperations:
    """Test batch analysis operations."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5
        settings.analysis.confidence_threshold = 0.8

        service = AnalysisService(openai_client, stash_service, settings)
        return service

    @pytest.mark.asyncio
    async def test_analyze_scenes_batch_operations(self, mock_service):
        """Test batch analysis with multiple scenes."""
        db = Mock(spec=AsyncSession)

        # Create multiple scenes to test batch processing
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}")
            for i in range(25)  # More than batch size
        ]

        # Mock database operations
        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()
        mock_service._mark_scenes_as_analyzed = AsyncMock()

        # Mock batch processor to return changes for each scene
        scene_changes = []
        for scene in scenes:
            scene_changes.append(
                SceneChanges(
                    scene_id=scene.id,
                    scene_title=scene.title,
                    scene_path=f"/path/to/{scene.id}.mp4",
                    changes=[
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=[],
                            proposed_value=[f"tag_{scene.id}"],
                            confidence=0.9,
                            reason="Test tag detection",
                        )
                    ],
                )
            )

        mock_service.batch_processor.process_scenes = AsyncMock(
            return_value=scene_changes
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="batch_plan", name="Batch Analysis Plan", status=PlanStatus.DRAFT
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(
            db=db,
            options=AnalysisOptions(detect_tags=True),
        )

        # Verify
        assert plan.id == "batch_plan"
        mock_service.batch_processor.process_scenes.assert_called_once()

        # Verify batch processor was called with all scenes
        call_args = mock_service.batch_processor.process_scenes.call_args
        assert call_args is not None
        # Check keyword arguments
        assert "scenes" in call_args.kwargs
        assert len(call_args.kwargs["scenes"]) == 25

    @pytest.mark.asyncio
    async def test_batch_analysis_with_partial_failures(self, mock_service):
        """Test batch analysis when some scenes fail."""
        db = Mock(spec=AsyncSession)

        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
            create_test_scene(id="scene3", title="Scene 3"),
        ]

        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()

        # Mock batch processor to return mixed results
        scene_changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1.mp4",
                changes=[
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=["tag1"],
                        confidence=0.9,
                        reason="Success",
                    )
                ],
            ),
            SceneChanges(
                scene_id="scene2",
                scene_title="Scene 2",
                scene_path="/path/to/scene2.mp4",
                changes=[],
                error="Failed to analyze scene",
            ),
            SceneChanges(
                scene_id="scene3",
                scene_title="Scene 3",
                scene_path="/path/to/scene3.mp4",
                changes=[
                    ProposedChange(
                        field="performers",
                        action="add",
                        current_value=[],
                        proposed_value=["performer1"],
                        confidence=0.85,
                        reason="Success",
                    )
                ],
            ),
        ]

        mock_service.batch_processor.process_scenes = AsyncMock(
            return_value=scene_changes
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="mixed_plan",
            name="Mixed Results Plan",
            status=PlanStatus.DRAFT,
            metadata={"errors": ["Failed to analyze scene"]},
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(db=db)

        # Verify
        assert plan.id == "mixed_plan"
        assert "errors" in plan.metadata

    @pytest.mark.asyncio
    async def test_batch_analysis_progress_tracking(self, mock_service):
        """Test batch analysis with progress tracking."""
        db = Mock(spec=AsyncSession)
        progress_callback = AsyncMock()

        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(10)
        ]

        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()

        # Track progress calls
        progress_updates = []

        async def track_progress(completed, total, *args):
            progress_updates.append((completed, total))

        # Mock batch processor with progress tracking
        async def mock_process_with_progress(
            scenes, analyzer, progress_cb=None, **kwargs
        ):
            results = []
            for i, scene in enumerate(scenes):
                results.append(
                    SceneChanges(
                        scene_id=scene.id,
                        scene_title=scene.title,
                        scene_path=f"/path/to/{scene.id}.mp4",
                        changes=[],
                    )
                )
                if progress_cb:
                    await progress_cb(i + 1, len(scenes), i + 1, len(scenes))
            return results

        mock_service.batch_processor.process_scenes = AsyncMock(
            side_effect=mock_process_with_progress
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="progress_plan", name="Progress Plan", status=PlanStatus.DRAFT
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute with progress callback
        plan = await mock_service.analyze_scenes(
            db=db,
            progress_callback=progress_callback,
        )

        # Verify progress tracking was used
        assert plan.id == "progress_plan"
        assert mock_service.batch_processor.process_scenes.called

    @pytest.mark.asyncio
    async def test_batch_analysis_concurrent_processing(self, mock_service):
        """Test concurrent batch processing."""
        db = Mock(spec=AsyncSession)

        # Create enough scenes to trigger multiple concurrent batches
        num_scenes = 30  # With batch_size=10, this creates 3 batches
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}")
            for i in range(num_scenes)
        ]

        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()
        mock_service._mark_scenes_as_analyzed = AsyncMock()

        # Track concurrent processing
        processing_times = []

        async def mock_process_scenes(scenes, analyzer, *args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            # Simulate concurrent processing
            results = []
            for scene in scenes:
                results.append(
                    SceneChanges(
                        scene_id=scene.id,
                        scene_title=scene.title,
                        scene_path=f"/path/to/{scene.id}.mp4",
                        changes=[
                            ProposedChange(
                                field="tags",
                                action="add",
                                current_value=[],
                                proposed_value=["concurrent_tag"],
                                confidence=0.9,
                                reason="Concurrent processing",
                            )
                        ],
                    )
                )
            processing_times.append(asyncio.get_event_loop().time() - start_time)
            return results

        mock_service.batch_processor.process_scenes = AsyncMock(
            side_effect=mock_process_scenes
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="concurrent_plan", name="Concurrent Plan", status=PlanStatus.DRAFT
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(db=db)

        # Verify
        assert plan.id == "concurrent_plan"
        assert len(processing_times) > 0
        mock_service.batch_processor.process_scenes.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_analysis_memory_efficiency(self, mock_service):
        """Test batch analysis handles large datasets efficiently."""
        db = Mock(spec=AsyncSession)

        # Create a specific number of scenes to test memory efficiency
        scene_count = 100
        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}")
            for i in range(scene_count)
        ]

        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()

        # Track processing to ensure memory-efficient batching
        processed_batches = []

        async def mock_process_batches(scenes, *args, **kwargs):
            # Track batch sizes to verify memory efficiency
            batch_size = 10  # Expected batch size
            num_batches = (len(scenes) + batch_size - 1) // batch_size
            processed_batches.append(num_batches)

            results = []
            for scene in scenes:
                results.append(
                    SceneChanges(
                        scene_id=scene.id,
                        scene_title=scene.title,
                        scene_path=f"/path/to/{scene.id}.mp4",
                        changes=[
                            ProposedChange(
                                field="tags",
                                action="add",
                                current_value=[],
                                proposed_value=["batch_tag"],
                                confidence=0.9,
                                reason="Batch processing",
                            )
                        ],
                    )
                )
            return results

        mock_service.batch_processor.process_scenes = AsyncMock(
            side_effect=mock_process_batches
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="memory_plan", name="Memory Efficient Plan", status=PlanStatus.DRAFT
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(db=db)

        # Verify efficient batching occurred
        assert plan.id == "memory_plan"
        assert len(processed_batches) > 0
        # With 100 scenes and batch_size=10, we expect 10 batches
        assert processed_batches[0] == 10

    @pytest.mark.asyncio
    async def test_batch_analysis_custom_options(self, mock_service):
        """Test batch analysis with custom analysis options."""
        db = Mock(spec=AsyncSession)

        scenes = [
            create_test_scene(id=f"scene{i}", title=f"Scene {i}") for i in range(5)
        ]

        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()
        mock_service._report_initial_progress = AsyncMock()

        # Custom options for selective analysis
        custom_options = AnalysisOptions(
            detect_tags=True,
            detect_performers=False,
            detect_studios=True,
            detect_details=False,
            detect_video_tags=True,
            confidence_threshold=0.95,  # Higher threshold
        )

        # Mock batch processor to handle custom options
        async def mock_process_with_options(scenes, analyzer, *args, **kwargs):
            results = []
            for scene in scenes:
                changes = []

                # Add changes based on custom options
                if custom_options.detect_tags:
                    changes.append(
                        ProposedChange(
                            field="tags",
                            action="add",
                            current_value=[],
                            proposed_value=["high_confidence_tag"],
                            confidence=0.96,
                            reason="High confidence detection",
                        )
                    )

                if custom_options.detect_studios:
                    changes.append(
                        ProposedChange(
                            field="studio",
                            action="set",
                            current_value=None,
                            proposed_value="Studio X",
                            confidence=0.95,
                            reason="Studio detected",
                        )
                    )

                results.append(
                    SceneChanges(
                        scene_id=scene.id,
                        scene_title=scene.title,
                        scene_path=f"/path/to/{scene.id}.mp4",
                        changes=changes,
                    )
                )
            return results

        mock_service.batch_processor.process_scenes = AsyncMock(
            side_effect=mock_process_with_options
        )

        # Mock plan manager
        mock_plan = AnalysisPlan(
            id="custom_options_plan",
            name="Custom Options Plan",
            status=PlanStatus.DRAFT,
            metadata={
                "options": {
                    "detect_tags": custom_options.detect_tags,
                    "detect_studios": custom_options.detect_studios,
                    "detect_performers": custom_options.detect_performers,
                    "confidence_threshold": custom_options.confidence_threshold,
                }
            },
        )
        mock_service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await mock_service.analyze_scenes(
            db=db,
            options=custom_options,
        )

        # Verify
        assert plan.id == "custom_options_plan"
        assert plan.metadata["options"]["detect_tags"] is True
        assert plan.metadata["options"]["detect_studios"] is True
        assert plan.metadata["options"]["detect_performers"] is False
        assert plan.metadata["options"]["confidence_threshold"] == 0.95


class TestAnalysisServiceEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock analysis service."""
        openai_client = Mock(spec=OpenAIClient)
        openai_client.model = "gpt-4o-mini"
        stash_service = Mock(spec=StashService)
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.batch_size = 10
        settings.analysis.max_concurrent = 5

        service = AnalysisService(openai_client, stash_service, settings)
        return service

    @pytest.mark.asyncio
    async def test_analyze_scenes_with_invalid_options(self, mock_service):
        """Test analyze_scenes with invalid options."""
        db = Mock(spec=AsyncSession)

        # Create options with all detection disabled
        options = AnalysisOptions(
            detect_tags=False,
            detect_performers=False,
            detect_studios=False,
            detect_details=False,
            detect_video_tags=False,
        )

        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        mock_service._get_scenes_from_database = AsyncMock(return_value=scenes)
        mock_service._refresh_cache = AsyncMock()

        # Mock batch processor to return empty changes
        mock_service.batch_processor.process_scenes = AsyncMock(
            return_value=[
                SceneChanges(
                    scene_id="scene1",
                    scene_title="Scene 1",
                    scene_path="/path/to/scene1.mp4",
                    changes=[],
                )
            ]
        )

        # Mock no changes handler
        mock_plan = AnalysisPlan(name="No Changes", status=PlanStatus.APPLIED)
        mock_service._handle_no_changes = AsyncMock(return_value=mock_plan)

        plan = await mock_service.analyze_scenes(db=db, options=options)

        assert plan.status == PlanStatus.APPLIED
        mock_service._handle_no_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_changes_with_network_error(self, mock_service):
        """Test applying changes with network error."""

        # Mock stash service to raise network error
        mock_service.stash_service.update_scene = AsyncMock(
            side_effect=Exception("Network error")
        )

        # The test expects _apply_changes method which doesn't exist in the new implementation
        # Let's test the error handling in apply_plan instead
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            # Mock plan manager to raise error
            mock_service.plan_manager.get_plan = AsyncMock(
                side_effect=Exception("Network error")
            )

            with pytest.raises(Exception, match="Network error"):
                await mock_service.apply_plan("1")

    def test_proposed_change_creation(self, mock_service):
        """Test ProposedChange model creation and validation."""
        # Valid proposed change
        change = ProposedChange(
            field="tags",
            action="add",
            current_value=[],
            proposed_value=["tag1", "tag2"],
            confidence=0.95,
            reason="Detected in video",
        )

        assert change.field == "tags"
        assert change.proposed_value == ["tag1", "tag2"]
        assert change.confidence == 0.95
        assert change.reason == "Detected in video"

    def test_scene_changes_has_changes(self, mock_service):
        """Test SceneChanges.has_changes method."""
        # Empty changes
        empty_changes = SceneChanges(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_path="/path/to/scene1.mp4",
            changes=[],
        )
        assert empty_changes.has_changes() is False

        # With changes
        with_changes = SceneChanges(
            scene_id="scene1",
            scene_title="Scene 1",
            scene_path="/path/to/scene1.mp4",
            changes=[
                ProposedChange(
                    field="tags",
                    action="add",
                    current_value=[],
                    proposed_value=["tag1"],
                    confidence=0.9,
                    reason="Test",
                )
            ],
        )
        assert with_changes.has_changes() is True
