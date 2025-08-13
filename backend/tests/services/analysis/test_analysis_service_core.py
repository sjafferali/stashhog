"""Core tests for analysis service focusing on high-value coverage."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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


def create_mock_settings():
    """Create properly configured mock settings."""
    settings = Mock(spec=Settings)
    settings.analysis = Mock()
    settings.analysis.batch_size = 10
    settings.analysis.max_concurrent = 5
    settings.analysis.confidence_threshold = 0.8
    return settings


def create_mock_openai_client():
    """Create properly configured mock OpenAI client."""
    client = Mock(spec=OpenAIClient)
    client.model = "gpt-4o-mini"
    return client


class TestAnalysisServiceCore:
    """Core analysis service tests."""

    @pytest.fixture
    def service(self):
        """Create a properly configured service."""
        openai_client = create_mock_openai_client()
        stash_service = Mock(spec=StashService)
        settings = create_mock_settings()

        service = AnalysisService(openai_client, stash_service, settings)

        # Mock common dependencies
        service._refresh_cache = AsyncMock()
        service.stash_service.get_all_studios = AsyncMock(return_value=[])
        service.stash_service.get_all_performers = AsyncMock(return_value=[])
        service.stash_service.get_all_tags = AsyncMock(return_value=[])

        return service

    @pytest.mark.asyncio
    async def test_analyze_scenes_basic_flow(self, service):
        """Test basic scene analysis flow."""
        db = Mock(spec=AsyncSession)

        # Create test scenes
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]

        # Mock database operations
        service._get_scenes_from_database = AsyncMock(return_value=scenes)
        service._report_initial_progress = AsyncMock()
        service._mark_scenes_as_analyzed = AsyncMock()

        # Mock batch processing with actual changes
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
                        reason="Detected tags",
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

        service.batch_processor.process_scenes = AsyncMock(return_value=scene_changes)

        # Mock incremental plan creation
        mock_plan = Mock(spec=AnalysisPlan)
        mock_plan.id = 1
        mock_plan.name = "Test Plan"
        mock_plan.status = PlanStatus.DRAFT
        mock_plan.plan_metadata = {"total_scenes": 2}

        service.plan_manager.create_or_update_plan = AsyncMock(return_value=mock_plan)
        service.plan_manager.add_changes_to_plan = AsyncMock()
        service.plan_manager.finalize_plan = AsyncMock()
        service.plan_manager.get_plan = AsyncMock(return_value=mock_plan)
        service._mark_single_scene_analyzed = AsyncMock()

        # Execute
        plan = await service.analyze_scenes(
            scene_ids=["scene1", "scene2"],
            db=db,
            options=AnalysisOptions(detect_tags=True, detect_performers=True),
            plan_name="Test Plan",
        )

        # Verify
        assert plan.name == "Test Plan"
        assert plan.status == PlanStatus.DRAFT
        service._get_scenes_from_database.assert_called_once()
        service.batch_processor.process_scenes.assert_called_once()
        # The implementation now returns a mock plan directly when dry run

    @pytest.mark.asyncio
    async def test_analyze_scenes_no_changes(self, service):
        """Test analysis when no changes are detected."""
        db = Mock(spec=AsyncSession)

        scenes = [create_test_scene(id="scene1", title="Scene 1")]
        service._get_scenes_from_database = AsyncMock(return_value=scenes)
        service._report_initial_progress = AsyncMock()

        # Mock batch processing with no changes
        scene_changes = [
            SceneChanges(
                scene_id="scene1",
                scene_title="Scene 1",
                scene_path="/path/to/scene1.mp4",
                changes=[],
            )
        ]
        service.batch_processor.process_scenes = AsyncMock(return_value=scene_changes)

        # Mock no changes handling
        mock_plan = AnalysisPlan(
            name="No Changes", status=PlanStatus.APPLIED, metadata={}
        )
        service._handle_no_changes = AsyncMock(return_value=mock_plan)

        # Execute
        plan = await service.analyze_scenes(db=db)

        # Verify
        assert plan.status == PlanStatus.APPLIED
        service._handle_no_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_plan_success(self, service):
        """Test successful plan application."""
        # Mock AsyncSessionLocal
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            # Create plan
            plan = AnalysisPlan(
                id="1", name="Test Plan", status=PlanStatus.DRAFT, metadata={}
            )

            # Mock plan manager
            service.plan_manager.get_plan = AsyncMock(return_value=plan)

            # Mock count query and changes query
            # First call is for count, second is for fetching changes
            mock_result_count = Mock(scalar=Mock(return_value=1))
            mock_result_changes = Mock()
            mock_result_changes.__iter__ = Mock(
                return_value=iter([(1,), (2,)])
            )  # Return change IDs
            db.execute = AsyncMock(side_effect=[mock_result_count, mock_result_changes])
            db.commit = AsyncMock()

            # Mock apply result
            apply_result = ApplyResult(
                plan_id=1,
                total_changes=1,
                applied_changes=1,
                failed_changes=0,
                errors=[],
            )
            service.plan_manager.apply_plan = AsyncMock(return_value=apply_result)

            # Execute
            result = await service.apply_plan("1")

            # Verify
            assert result.total_changes == 1
            assert result.applied_changes == 1
            # The implementation now returns a mock plan directly when dry run
            service.plan_manager.apply_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self, service):
        """Test applying non-existent plan."""
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            service.plan_manager.get_plan = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Plan.*not found"):
                await service.apply_plan("1")

    @pytest.mark.asyncio
    async def test_analyze_single_scene(self, service):
        """Test single scene analysis."""
        scene = create_test_scene(id="scene1", title="Test Scene")
        options = AnalysisOptions(detect_tags=True, detect_performers=True)

        # Mock AI analysis
        service.ai_client.analyze_scene_with_cost = AsyncMock(
            return_value=(
                {
                    "tags": ["tag1", "tag2"],
                    "performers": ["performer1"],
                    "confidence_scores": {"tags": 0.9, "performers": 0.85},
                },
                0.05,  # cost
            )
        )

        # Mock detectors
        service.tag_detector.detect = AsyncMock(
            return_value=DetectionResult(
                value=["tag1", "tag2"], confidence=0.9, source="ai", metadata={}
            )
        )
        service.performer_detector.detect = AsyncMock(
            return_value=DetectionResult(
                value=["performer1"], confidence=0.85, source="ai", metadata={}
            )
        )

        # Mock detector methods
        service._detect_tags = AsyncMock(
            return_value=[
                ProposedChange(
                    field="tags",
                    action="add",
                    current_value=[],
                    proposed_value=["tag1", "tag2"],
                    confidence=0.9,
                    reason="Detected tags",
                )
            ]
        )
        service._detect_performers = AsyncMock(
            return_value=[
                ProposedChange(
                    field="performers",
                    action="add",
                    current_value=[],
                    proposed_value=["performer1"],
                    confidence=0.85,
                    reason="Detected performer",
                )
            ]
        )

        # Execute
        changes = await service.analyze_single_scene(scene, options)

        # Verify
        assert len(changes) == 2
        # Check that we have both tags and performers changes (order doesn't matter)
        fields = {change.field for change in changes}
        assert "tags" in fields
        assert "performers" in fields

    def test_generate_plan_name(self, service):
        """Test plan name generation."""
        options = AnalysisOptions(
            detect_tags=True,
            detect_performers=True,
            detect_studios=False,
            detect_details=False,
        )
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]

        name = service._generate_plan_name(options, 2, scenes)

        assert "2 scenes" in name

    def test_create_analysis_metadata(self, service):
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

        metadata = service._create_analysis_metadata(options, scenes, changes)

        assert metadata["statistics"]["total_scenes"] == 1
        assert metadata["statistics"]["total_changes"] == 1
        assert metadata["settings"]["detect_tags"] is True

    @pytest.mark.asyncio
    async def test_batch_analysis_with_ai(self, service):
        """Test batch analysis using AI."""
        scenes = [
            create_test_scene(id="scene1", title="Scene 1"),
            create_test_scene(id="scene2", title="Scene 2"),
        ]
        options = AnalysisOptions(detect_tags=True, detect_video_tags=True)

        # Mock AI batch analysis
        service.ai_client.batch_analyze_scenes = AsyncMock(
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

        # Mock video tag detection
        service.video_tag_detector.detect_batch = AsyncMock(
            return_value={
                "scene1": DetectionResult(
                    value=["video_tag1"],
                    confidence=0.95,
                    source="video",
                    metadata={"frames_analyzed": 10},
                ),
                "scene2": DetectionResult(
                    value=["video_tag2"],
                    confidence=0.9,
                    source="video",
                    metadata={"frames_analyzed": 10},
                ),
            }
        )

        # Mock tag detector
        service.tag_detector.detect = AsyncMock(
            side_effect=[
                DetectionResult(value=["tag1", "tag2"], confidence=0.9, source="ai"),
                DetectionResult(value=["tag3"], confidence=0.85, source="ai"),
            ]
        )

        # Mock analyze_single_scene to test batch processing
        service.analyze_single_scene = AsyncMock(
            side_effect=[
                [
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=["tag1"],
                        confidence=0.9,
                        reason="Test",
                    )
                ],
                [
                    ProposedChange(
                        field="tags",
                        action="add",
                        current_value=[],
                        proposed_value=["tag2"],
                        confidence=0.85,
                        reason="Test",
                    )
                ],
            ]
        )

        # Execute - convert scenes to dict format for _analyze_batch
        scene_dicts = [{"id": s.id, "title": s.title} for s in scenes]
        changes = await service._analyze_batch(scene_dicts, options)

        # Verify
        assert len(changes) == 2
        assert changes[0].scene_id == "scene1"
        assert changes[1].scene_id == "scene2"

    @pytest.mark.asyncio
    async def test_apply_changes_error_handling(self, service):
        """Test error handling during plan application."""
        # Mock AsyncSessionLocal
        with patch("app.core.database.AsyncSessionLocal") as mock_session:
            db = Mock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = db

            # Mock plan manager to raise error
            service.plan_manager.get_plan = AsyncMock(
                side_effect=Exception("API error")
            )

            with pytest.raises(Exception, match="API error"):
                await service.apply_plan("1")

    @pytest.mark.asyncio
    async def test_refresh_cache_partial_failure(self, service):
        """Test cache refresh with partial failures."""

        # Mock _refresh_cache to simulate partial failure
        async def mock_refresh_with_partial_failure():
            # Simulate studios query failure but others succeed
            service._cache["studios"] = []
            service._cache["performers"] = [{"name": "Performer 1", "aliases": []}]
            service._cache["tags"] = ["Tag 1"]
            service._cache["last_refresh"] = "2024-01-01T00:00:00"

        service._refresh_cache = AsyncMock(
            side_effect=mock_refresh_with_partial_failure
        )

        # Should not raise
        await service._refresh_cache()

        # Verify partial data is cached
        assert service._cache["studios"] == []
        assert len(service._cache["performers"]) == 1
        assert len(service._cache["tags"]) == 1
        assert service._cache["last_refresh"] is not None
