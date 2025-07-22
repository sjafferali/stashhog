"""Tests for SceneService class."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.scene import Scene
from app.models.tag import Tag
from app.services.scene_service import SceneService
from app.services.stash_service import StashService


class TestSceneService:
    """Test SceneService functionality."""

    @pytest.fixture
    def mock_stash_service(self):
        """Create mock StashService."""
        mock = Mock(spec=StashService)
        mock.update_scene = AsyncMock()
        mock.find_or_create_tag = AsyncMock()
        return mock

    @pytest.fixture
    def scene_service(self, mock_stash_service):
        """Create SceneService instance."""
        return SceneService(mock_stash_service)

    @pytest.fixture
    def sample_scene(self):
        """Create sample scene."""
        scene = Scene(
            id="scene-123",
            title="Test Scene",
            organized=False,
            analyzed=False,
            video_analyzed=False,
            stash_created_at=datetime.now(timezone.utc),
            last_synced=datetime.now(timezone.utc),
        )
        scene.tags = []
        return scene

    @pytest.fixture
    def sample_tags(self):
        """Create sample tags."""
        return [
            Tag(id="tag-1", name="Tag 1", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-2", name="Tag 2", last_synced=datetime.now(timezone.utc)),
            Tag(id="tag-3", name="Tag 3", last_synced=datetime.now(timezone.utc)),
        ]

    @pytest.mark.asyncio
    async def test_init(self, mock_stash_service):
        """Test SceneService initialization."""
        service = SceneService(mock_stash_service)
        assert service.stash_service == mock_stash_service
        assert service.tag_repository is not None

    @pytest.mark.asyncio
    async def test_update_scene_with_sync_success(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test successful scene update in both systems."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Update scene
        updates = {"title": "Updated Title", "organized": True}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Verify database update
        updated_scene = await test_async_session.get(Scene, "scene-123")
        assert updated_scene.title == "Updated Title"
        assert updated_scene.organized is True

        # Verify Stash update was called
        scene_service.stash_service.update_scene.assert_called_once_with(
            "scene-123", updates
        )

    @pytest.mark.asyncio
    async def test_update_scene_with_sync_database_failure(
        self, scene_service, test_async_session
    ):
        """Test scene update when database update fails."""
        # Try to update non-existent scene
        updates = {"title": "Updated Title"}
        result = await scene_service.update_scene_with_sync(
            "non-existent", updates, test_async_session
        )

        assert result is False

        # Verify Stash update was not called
        scene_service.stash_service.update_scene.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_scene_with_sync_stash_failure(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test scene update when Stash update fails."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to fail
        scene_service.stash_service.update_scene.return_value = None

        # Update scene
        updates = {"title": "Updated Title"}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is False

        # Database update should still persist (by design)
        updated_scene = await test_async_session.get(Scene, "scene-123")
        assert updated_scene.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_scene_with_tags(
        self, scene_service, test_async_session, sample_scene, sample_tags
    ):
        """Test updating scene with tags."""
        # Add scene and tags to database
        test_async_session.add(sample_scene)
        for tag in sample_tags:
            test_async_session.add(tag)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Update scene with tags
        updates = {"title": "Updated Title", "tag_ids": ["tag-1", "tag-2"]}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Verify tags were updated
        updated_scene = await test_async_session.get(Scene, "scene-123")
        await test_async_session.refresh(updated_scene, ["tags"])
        assert len(updated_scene.tags) == 2
        tag_names = {tag.name for tag in updated_scene.tags}
        assert "Tag 1" in tag_names
        assert "Tag 2" in tag_names

        # Verify Stash was called with the updates (tag_ids is still included in the call to Stash)
        scene_service.stash_service.update_scene.assert_called_with(
            "scene-123", {"title": "Updated Title", "tag_ids": ["tag-1", "tag-2"]}
        )

    @pytest.mark.asyncio
    async def test_update_scene_video_analyzed(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test updating video_analyzed field."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Update video_analyzed
        updates = {"video_analyzed": True}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Verify update
        updated_scene = await test_async_session.get(Scene, "scene-123")
        assert updated_scene.video_analyzed is True

    @pytest.mark.asyncio
    async def test_update_scene_exception_handling(
        self, scene_service, test_async_session
    ):
        """Test exception handling in update_scene_with_sync."""
        # Mock database execute to raise exception
        with patch.object(
            test_async_session, "execute", side_effect=Exception("Database error")
        ):
            updates = {"title": "Updated Title"}
            result = await scene_service.update_scene_with_sync(
                "scene-123", updates, test_async_session
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_apply_tags_to_scene(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test applying tags to a scene."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock stash service methods
        scene_service.stash_service.find_or_create_tag.side_effect = [
            "new-tag-1",  # First new tag
            "new-tag-2",  # Second new tag
            "tagme-id",  # AI_TagMe
            "tagged-id",  # AI_Tagged
        ]
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Scene data with existing tags
        scene_data = {
            "tags": [
                {"id": "existing-1", "name": "Existing Tag"},
                {"id": "ai-old", "name": "Old_AI"},  # Should be removed
            ]
        }

        # Apply tags
        tags_added = await scene_service.apply_tags_to_scene(
            "scene-123",
            scene_data,
            ["New Tag 1", "New Tag 2"],
            True,  # has_tagme
            test_async_session,
        )

        assert tags_added == 2

        # Verify find_or_create_tag was called
        assert scene_service.stash_service.find_or_create_tag.call_count == 4

    @pytest.mark.asyncio
    async def test_apply_tags_to_scene_no_tagme(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test applying tags when scene doesn't have AI_TagMe."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock stash service methods
        scene_service.stash_service.find_or_create_tag.side_effect = [
            "new-tag-1",  # New tag
            "tagged-id",  # AI_Tagged
        ]
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Scene data without tags
        scene_data = {"tags": []}

        # Apply tags
        tags_added = await scene_service.apply_tags_to_scene(
            "scene-123", scene_data, ["New Tag"], False, test_async_session  # no tagme
        )

        assert tags_added == 1

    @pytest.mark.asyncio
    async def test_apply_tags_filtering_ai_tags(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test that existing AI tags are filtered out."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock stash service
        scene_service.stash_service.find_or_create_tag.side_effect = [
            "new-tag-1",
            "tagged-id",
        ]
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Scene data with AI tags that should be removed
        scene_data = {
            "tags": [
                {"id": "keep-1", "name": "Regular Tag"},
                {"id": "remove-1", "name": "Something_AI"},
                {"id": "remove-2", "name": "Another_AI"},
            ]
        }

        # Apply tags
        await scene_service.apply_tags_to_scene(
            "scene-123", scene_data, ["New Tag"], False, test_async_session
        )

        # Verify update was called
        # Should have kept regular tag, added new tag and AI_Tagged
        # but removed the _AI tags
        assert scene_service.stash_service.update_scene.called

    @pytest.mark.asyncio
    async def test_mark_scene_as_video_analyzed(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test marking a scene as video analyzed."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Mark as video analyzed
        result = await scene_service.mark_scene_as_video_analyzed(
            "scene-123", test_async_session
        )

        assert result is True

        # Verify update
        updated_scene = await test_async_session.get(Scene, "scene-123")
        assert updated_scene.video_analyzed is True

        # Verify Stash was called
        scene_service.stash_service.update_scene.assert_called_with(
            "scene-123", {"video_analyzed": True}
        )

    @pytest.mark.asyncio
    async def test_update_scene_tags_empty_list(
        self, scene_service, test_async_session, sample_scene, sample_tags
    ):
        """Test clearing all tags from a scene."""
        # Add scene with tags
        sample_scene.tags = sample_tags[:2]
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Clear tags
        updates = {"tag_ids": []}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Verify tags were cleared
        updated_scene = await test_async_session.get(Scene, "scene-123")
        await test_async_session.refresh(updated_scene, ["tags"])
        assert len(updated_scene.tags) == 0

    @pytest.mark.asyncio
    async def test_update_scene_invalid_tag_ids(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test updating scene with invalid tag IDs."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Update with non-existent tag IDs
        updates = {"tag_ids": ["invalid-1", "invalid-2"]}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Scene should have no tags (invalid IDs ignored)
        updated_scene = await test_async_session.get(Scene, "scene-123")
        await test_async_session.refresh(updated_scene, ["tags"])
        assert len(updated_scene.tags) == 0

    @pytest.mark.asyncio
    async def test_update_stash_exception_handling(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test exception handling when updating Stash."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to raise exception
        scene_service.stash_service.update_scene.side_effect = Exception(
            "Stash API error"
        )

        # Update scene
        updates = {"title": "Updated Title"}
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_scene_multiple_fields(
        self, scene_service, test_async_session, sample_scene
    ):
        """Test updating multiple fields at once."""
        # Add scene to database
        test_async_session.add(sample_scene)
        await test_async_session.commit()

        # Mock Stash update to succeed
        scene_service.stash_service.update_scene.return_value = {"id": "scene-123"}

        # Update multiple fields
        updates = {
            "title": "New Title",
            "details": "New details",
            "organized": True,
            "rating": 5,
            "url": "https://example.com",
        }
        result = await scene_service.update_scene_with_sync(
            "scene-123", updates, test_async_session
        )

        assert result is True

        # Verify all updates
        updated_scene = await test_async_session.get(Scene, "scene-123")
        assert updated_scene.title == "New Title"
        assert updated_scene.details == "New details"
        assert updated_scene.organized is True
        assert updated_scene.rating == 5
        assert updated_scene.url == "https://example.com"
