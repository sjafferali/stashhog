"""Tests for Scene repository."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene
from app.repositories.scene_repository import scene_repository


class TestSceneRepository:
    """Test cases for Scene repository."""

    @pytest.fixture
    async def sample_scenes(self, test_async_session: AsyncSession) -> list[Scene]:
        """Create sample scenes for testing."""
        scenes = []
        base_time = datetime.utcnow()

        # Create analyzed scenes
        for i in range(3):
            scene = Scene(
                id=f"analyzed-{i}",
                title=f"Analyzed Scene {i}",
                organized=True,
                analyzed=True,
                video_analyzed=True,
                stash_created_at=base_time,
                last_synced=base_time,
            )
            scenes.append(scene)
            test_async_session.add(scene)

        # Create unanalyzed scenes
        for i in range(5):
            scene = Scene(
                id=f"unanalyzed-{i}",
                title=f"Unanalyzed Scene {i}",
                organized=False,
                analyzed=False,
                video_analyzed=False,
                stash_created_at=base_time,
                last_synced=base_time,
            )
            scenes.append(scene)
            test_async_session.add(scene)

        # Create partially analyzed scenes
        for i in range(2):
            scene = Scene(
                id=f"partial-{i}",
                title=f"Partial Scene {i}",
                organized=True,
                analyzed=True,
                video_analyzed=False,  # Only text analyzed, not video
                stash_created_at=base_time,
                last_synced=base_time,
            )
            scenes.append(scene)
            test_async_session.add(scene)

        await test_async_session.commit()
        return scenes

    @pytest.mark.asyncio
    async def test_get_unanalyzed_scenes_current_implementation(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test the current implementation of get_unanalyzed_scenes (returns empty list)."""
        result = await scene_repository.get_unanalyzed_scenes(test_async_session)

        # Current implementation returns empty list
        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_unanalyzed_scenes_with_no_scenes(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test get_unanalyzed_scenes when database has no scenes."""
        result = await scene_repository.get_unanalyzed_scenes(test_async_session)

        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_repository_instance(self) -> None:
        """Test that the repository is properly instantiated."""
        from app.repositories.scene_repository import SceneRepository, scene_repository

        assert scene_repository is not None
        assert isinstance(scene_repository, SceneRepository)

    # The following tests demonstrate how the repository could be extended
    # They are marked with pytest.mark.skip as the functionality doesn't exist yet

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_get_scene_by_id(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test getting a scene by ID."""
        # This would be a useful method to add
        scene = await scene_repository.get_scene_by_id(test_async_session, "analyzed-0")
        assert scene is not None
        assert scene.id == "analyzed-0"
        assert scene.title == "Analyzed Scene 0"

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_get_scenes_by_organized_status(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test getting scenes by organized status."""
        # Get organized scenes
        organized = await scene_repository.get_scenes_by_organized_status(
            test_async_session, organized=True
        )
        assert len(organized) == 5  # 3 analyzed + 2 partial

        # Get unorganized scenes
        unorganized = await scene_repository.get_scenes_by_organized_status(
            test_async_session, organized=False
        )
        assert len(unorganized) == 5  # 5 unanalyzed

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_bulk_update_scenes(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test bulk updating scenes."""
        scene_ids = ["unanalyzed-0", "unanalyzed-1"]

        updated_count = await scene_repository.bulk_update_scenes(
            test_async_session,
            scene_ids=scene_ids,
            update_data={"organized": True, "analyzed": True},
        )

        assert updated_count == 2

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_search_scenes(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test searching scenes by title."""
        results = await scene_repository.search_scenes(
            test_async_session, search_term="Analyzed"
        )
        assert len(results) == 3

        results = await scene_repository.search_scenes(
            test_async_session, search_term="Partial"
        )
        assert len(results) == 2

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_get_scenes_with_filters(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test getting scenes with multiple filters."""
        # Test with organized filter
        results = await scene_repository.get_scenes(
            test_async_session, organized=True, limit=10, offset=0
        )
        assert len(results) == 5

        # Test with analyzed filter
        results = await scene_repository.get_scenes(
            test_async_session, analyzed=True, video_analyzed=False, limit=10, offset=0
        )
        assert len(results) == 2  # Only partial scenes

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_count_scenes(
        self, test_async_session: AsyncSession, sample_scenes: list[Scene]
    ) -> None:
        """Test counting scenes with filters."""
        # Total count
        total = await scene_repository.count_scenes(test_async_session)
        assert total == 10

        # Count analyzed
        analyzed_count = await scene_repository.count_scenes(
            test_async_session, analyzed=True
        )
        assert analyzed_count == 5

        # Count video analyzed
        video_analyzed_count = await scene_repository.count_scenes(
            test_async_session, video_analyzed=True
        )
        assert video_analyzed_count == 3

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_get_scenes_by_studio(self, test_async_session: AsyncSession) -> None:
        """Test getting scenes by studio ID."""
        from app.models.studio import Studio

        # Create a studio
        studio = Studio(
            id="studio-1", name="Test Studio", last_synced=datetime.utcnow()
        )
        test_async_session.add(studio)

        # Create scenes with studio
        for i in range(3):
            scene = Scene(
                id=f"studio-scene-{i}",
                title=f"Studio Scene {i}",
                studio_id=studio.id,
                stash_created_at=datetime.utcnow(),
                last_synced=datetime.utcnow(),
            )
            test_async_session.add(scene)

        await test_async_session.commit()

        # Get scenes by studio
        results = await scene_repository.get_scenes_by_studio(
            test_async_session, studio_id=studio.id
        )
        assert len(results) == 3

    @pytest.mark.skip(reason="Method not yet implemented")
    @pytest.mark.asyncio
    async def test_get_scenes_needing_sync(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test getting scenes that need synchronization."""
        from datetime import timedelta

        now = datetime.utcnow()

        # Create old scene (needs sync)
        old_scene = Scene(
            id="old-scene",
            title="Old Scene",
            stash_created_at=now - timedelta(days=10),
            last_synced=now - timedelta(days=7),  # Synced 7 days ago
        )
        test_async_session.add(old_scene)

        # Create recent scene (doesn't need sync)
        recent_scene = Scene(
            id="recent-scene",
            title="Recent Scene",
            stash_created_at=now - timedelta(days=1),
            last_synced=now - timedelta(hours=1),  # Synced 1 hour ago
        )
        test_async_session.add(recent_scene)

        await test_async_session.commit()

        # Get scenes needing sync (older than 24 hours)
        results = await scene_repository.get_scenes_needing_sync(
            test_async_session, older_than_hours=24
        )
        assert len(results) == 1
        assert results[0].id == "old-scene"

    @pytest.mark.asyncio
    async def test_repository_with_empty_database(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test repository methods with empty database."""
        # Ensure database is empty
        from sqlalchemy import select

        result = await test_async_session.execute(select(Scene))
        assert len(result.scalars().all()) == 0

        # Test current implementation
        unanalyzed = await scene_repository.get_unanalyzed_scenes(test_async_session)
        assert unanalyzed == []

    @pytest.mark.asyncio
    async def test_repository_transaction_handling(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test that repository handles transactions correctly."""
        # Create a scene
        scene = Scene(
            id="transaction-test",
            title="Transaction Test",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Call repository method
        result = await scene_repository.get_unanalyzed_scenes(test_async_session)

        # Should return empty list per current implementation
        assert result == []

        # Verify scene still exists (transaction wasn't corrupted)
        from sqlalchemy import select

        result = await test_async_session.execute(
            select(Scene).where(Scene.id == "transaction-test")
        )
        assert result.scalar() is not None

    @pytest.mark.asyncio
    async def test_large_dataset_performance(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test repository performance with larger dataset."""
        # Create 100 scenes
        scenes = []
        base_time = datetime.utcnow()

        for i in range(100):
            scene = Scene(
                id=f"perf-test-{i}",
                title=f"Performance Test Scene {i}",
                organized=i % 2 == 0,
                analyzed=i % 3 == 0,
                video_analyzed=i % 5 == 0,
                stash_created_at=base_time,
                last_synced=base_time,
            )
            scenes.append(scene)
            test_async_session.add(scene)

        await test_async_session.commit()

        # Test repository method
        import time

        start_time = time.time()
        result = await scene_repository.get_unanalyzed_scenes(test_async_session)
        end_time = time.time()

        # Should complete quickly even with many scenes
        assert (end_time - start_time) < 1.0  # Less than 1 second
        assert result == []  # Current implementation
