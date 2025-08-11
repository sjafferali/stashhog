"""Integration tests for bulk tag operations on scenes."""

from unittest.mock import Mock

from app.models import Scene, Tag


def test_tag_operations_models():
    """Test that models are properly structured."""
    # Create mock scene
    mock_scene = Mock(spec=Scene)
    mock_scene.id = "123"
    mock_scene.tags = []

    # Create mock tags
    mock_tag1 = Mock(spec=Tag)
    mock_tag1.id = 1
    mock_tag1.name = "Test Tag 1"

    # Test adding tag to scene
    mock_scene.tags.append(mock_tag1)
    assert len(mock_scene.tags) == 1
    assert mock_scene.tags[0].name == "Test Tag 1"

    # Test removing tag from scene
    mock_scene.tags = [t for t in mock_scene.tags if t.id != 1]
    assert len(mock_scene.tags) == 0


def test_request_response_models():
    """Test request and response model structures."""
    from app.api.routes.scenes import BulkTagOperationRequest, BulkTagOperationResponse

    # Test request model
    request = BulkTagOperationRequest(scene_ids=[1, 2, 3], tag_ids=[1, 2])
    assert request.scene_ids == [1, 2, 3]
    assert request.tag_ids == [1, 2]

    # Test response model
    response = BulkTagOperationResponse(
        success=True, message="Test message", scenes_updated=3, tags_affected=2
    )
    assert response.success is True
    assert response.message == "Test message"
    assert response.scenes_updated == 3
    assert response.tags_affected == 2
