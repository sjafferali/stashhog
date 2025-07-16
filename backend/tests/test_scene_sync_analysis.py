"""Test that scene sync works correctly during analysis."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.scene import Scene
from app.services.analysis.analysis_service import AnalysisService
from app.services.analysis.models import AnalysisOptions


@pytest.mark.asyncio
async def test_analyze_scenes_syncs_to_database():
    """Test that analyze_scenes syncs scene data to database before analysis."""
    # Mock dependencies
    mock_openai = MagicMock()
    mock_openai.model = "gpt-4"

    mock_stash = AsyncMock()
    mock_settings = Settings()

    # Mock Stash scene data
    stash_scene_data = {
        "id": "scene123",
        "title": "Test Scene",
        "details": "Test details",
        "organized": True,
        "file": {
            "duration": 120.5,
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
        },
        "paths": ["/path/to/scene.mp4"],
        "performers": [],
        "tags": [],
        "studio": None,
        "created_at": "2024-01-01T00:00:00Z",
    }

    # Mock stash service to return scene data
    mock_stash.get_scene.return_value = stash_scene_data

    # Create mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_query_result = AsyncMock()
    mock_query_result.scalar_one_or_none.return_value = None  # Scene doesn't exist yet
    mock_db.execute.return_value = mock_query_result

    # Initialize service
    service = AnalysisService(
        openai_client=mock_openai,
        stash_service=mock_stash,
        settings=mock_settings,
    )

    # Create mock scene that will be returned by sync
    mock_scene = Scene(
        id="scene123",
        title="Test Scene",
        details="Test details",
        analyzed=True,
        paths=["/path/to/scene.mp4"],
    )

    # Mock the scene_sync_utils to return the synced scene
    service.scene_sync_utils.sync_scenes_by_ids = AsyncMock(return_value=[mock_scene])

    # Mock the batch processor to avoid actual processing
    service.batch_processor.process_scenes = AsyncMock(return_value=[])

    # Mock plan manager
    mock_plan = MagicMock()
    mock_plan.id = "plan123"
    mock_plan.changes = []
    service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

    # Run analysis
    options = AnalysisOptions(
        detect_studios=True,
        detect_performers=True,
        detect_tags=True,
    )

    plan = await service.analyze_scenes(
        scene_ids=["scene123"],
        options=options,
        db=mock_db,
    )

    # Verify that scene_sync_utils was called
    service.scene_sync_utils.sync_scenes_by_ids.assert_called_once_with(
        scene_ids=["scene123"], db=mock_db, update_existing=True
    )

    # Verify plan was created
    assert plan is not None
    assert plan.id == "plan123"


@pytest.mark.asyncio
async def test_analyze_scenes_updates_existing_scene():
    """Test that analyze_scenes updates existing scenes in database."""
    # Mock dependencies
    mock_openai = MagicMock()
    mock_openai.model = "gpt-4"

    mock_stash = AsyncMock()
    mock_settings = Settings()

    # Create existing scene
    existing_scene = Scene(
        id="scene123",
        title="Old Title",
        details="Old details",
        analyzed=False,
    )

    # Mock Stash scene data with updated info
    stash_scene_data = {
        "id": "scene123",
        "title": "Updated Title",
        "details": "Updated details",
        "organized": True,
        "file": {
            "duration": 120.5,
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
        },
        "paths": ["/path/to/scene.mp4"],
        "performers": [],
        "tags": [],
        "studio": None,
        "created_at": "2024-01-01T00:00:00Z",
    }

    # Mock stash service to return scene data
    mock_stash.get_scene.return_value = stash_scene_data

    # Create mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_query_result = AsyncMock()
    mock_query_result.scalar_one_or_none.return_value = existing_scene
    mock_db.execute.return_value = mock_query_result

    # Initialize service
    service = AnalysisService(
        openai_client=mock_openai,
        stash_service=mock_stash,
        settings=mock_settings,
    )

    # Create updated scene that will be returned by sync
    updated_scene = Scene(
        id="scene123",
        title="Updated Title",
        details="Updated details",
        analyzed=True,
        paths=["/path/to/scene.mp4"],
    )

    # Mock the scene_sync_utils to return the updated scene
    service.scene_sync_utils.sync_scenes_by_ids = AsyncMock(
        return_value=[updated_scene]
    )

    # Mock the batch processor to avoid actual processing
    service.batch_processor.process_scenes = AsyncMock(return_value=[])

    # Mock plan manager
    mock_plan = MagicMock()
    mock_plan.id = "plan123"
    mock_plan.changes = []
    service.plan_manager.create_plan = AsyncMock(return_value=mock_plan)

    # Run analysis
    options = AnalysisOptions()

    plan = await service.analyze_scenes(
        scene_ids=["scene123"],
        options=options,
        db=mock_db,
    )

    # Verify that scene_sync_utils was called to update the scene
    service.scene_sync_utils.sync_scenes_by_ids.assert_called_once_with(
        scene_ids=["scene123"], db=mock_db, update_existing=True
    )

    # Verify plan was created
    assert plan is not None
    assert plan.id == "plan123"
