"""Tests for Scene model."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.performer import Performer
from app.models.scene import Scene
from app.models.scene_file import SceneFile
from app.models.studio import Studio
from app.models.tag import Tag


class TestSceneModel:
    """Test cases for Scene model."""

    @pytest.fixture
    async def sample_studio(self, test_async_session: AsyncSession) -> Studio:
        """Create a sample studio for testing."""
        studio = Studio(
            id="studio-123", name="Test Studio", last_synced=datetime.utcnow()
        )
        test_async_session.add(studio)
        await test_async_session.commit()
        return studio

    @pytest.fixture
    async def sample_performers(
        self, test_async_session: AsyncSession
    ) -> list[Performer]:
        """Create sample performers for testing."""
        performers = [
            Performer(id="perf-1", name="Performer One", last_synced=datetime.utcnow()),
            Performer(id="perf-2", name="Performer Two", last_synced=datetime.utcnow()),
        ]
        test_async_session.add_all(performers)
        await test_async_session.commit()
        return performers

    @pytest.fixture
    async def sample_tags(self, test_async_session: AsyncSession) -> list[Tag]:
        """Create sample tags for testing."""
        tags = [
            Tag(id="tag-1", name="Action", last_synced=datetime.utcnow()),
            Tag(id="tag-2", name="Drama", last_synced=datetime.utcnow()),
        ]
        test_async_session.add_all(tags)
        await test_async_session.commit()
        return tags

    @pytest.mark.asyncio
    async def test_create_scene_basic(self, test_async_session: AsyncSession) -> None:
        """Test creating a basic scene."""
        scene = Scene(
            id="scene-123",
            title="Test Scene",
            organized=True,
            analyzed=False,
            video_analyzed=False,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )

        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert scene.id == "scene-123"
        assert scene.title == "Test Scene"
        assert scene.organized is True
        assert scene.analyzed is False
        assert scene.video_analyzed is False
        assert scene.details is None
        assert scene.url is None
        assert scene.rating is None
        assert scene.studio_id is None
        assert scene.stash_updated_at is None
        assert scene.stash_date is None
        assert scene.content_checksum is None

    @pytest.mark.asyncio
    async def test_scene_with_all_fields(
        self, test_async_session: AsyncSession, sample_studio: Studio
    ) -> None:
        """Test creating a scene with all fields populated."""
        now = datetime.utcnow()
        scene = Scene(
            id="scene-456",
            title="Complete Scene",
            organized=True,
            analyzed=True,
            video_analyzed=True,
            details="This is a detailed description",
            url="https://example.com/scene",
            rating=85,
            stash_created_at=now - timedelta(days=30),
            stash_updated_at=now - timedelta(days=1),
            stash_date=now - timedelta(days=15),
            studio_id=sample_studio.id,
            last_synced=now,
            content_checksum="abc123def456",
        )

        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert scene.title == "Complete Scene"
        assert scene.details == "This is a detailed description"
        assert scene.url == "https://example.com/scene"
        assert scene.rating == 85
        assert scene.studio_id == sample_studio.id
        assert scene.studio.name == "Test Studio"
        assert scene.content_checksum == "abc123def456"

    @pytest.mark.asyncio
    async def test_scene_performer_relationships(
        self,
        test_async_session: AsyncSession,
        sample_performers: list[Performer],
    ) -> None:
        """Test scene-performer relationships."""
        scene = Scene(
            id="scene-789",
            title="Scene with Performers",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )

        # Add performers
        scene.add_performer(sample_performers[0])
        scene.add_performer(sample_performers[1])

        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert len(scene.performers) == 2
        assert sample_performers[0] in scene.performers
        assert sample_performers[1] in scene.performers

        # Test adding duplicate performer (should not add)
        scene.add_performer(sample_performers[0])
        await test_async_session.commit()
        await test_async_session.refresh(scene)
        assert len(scene.performers) == 2

        # Test removing performer
        scene.remove_performer(sample_performers[1])
        await test_async_session.commit()
        await test_async_session.refresh(scene)
        assert len(scene.performers) == 1
        assert sample_performers[0] in scene.performers
        assert sample_performers[1] not in scene.performers

        # Test removing non-existent performer (should not error)
        scene.remove_performer(sample_performers[1])
        await test_async_session.commit()
        assert len(scene.performers) == 1

    @pytest.mark.asyncio
    async def test_scene_tag_relationships(
        self,
        test_async_session: AsyncSession,
        sample_tags: list[Tag],
    ) -> None:
        """Test scene-tag relationships."""
        scene = Scene(
            id="scene-tag-test",
            title="Scene with Tags",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )

        # Add tags
        scene.add_tag(sample_tags[0])
        scene.add_tag(sample_tags[1])

        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert len(scene.tags) == 2
        assert sample_tags[0] in scene.tags
        assert sample_tags[1] in scene.tags

        # Test adding duplicate tag (should not add)
        scene.add_tag(sample_tags[0])
        await test_async_session.commit()
        await test_async_session.refresh(scene)
        assert len(scene.tags) == 2

        # Test removing tag
        scene.remove_tag(sample_tags[1])
        await test_async_session.commit()
        await test_async_session.refresh(scene)
        assert len(scene.tags) == 1
        assert sample_tags[0] in scene.tags
        assert sample_tags[1] not in scene.tags

    @pytest.mark.asyncio
    async def test_scene_file_relationships(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test scene-file relationships."""
        scene = Scene(
            id="scene-file-test",
            title="Scene with Files",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )

        test_async_session.add(scene)
        await test_async_session.commit()

        # Add primary file
        primary_file = SceneFile(
            id="file-1",
            scene_id=scene.id,
            path="/videos/primary.mp4",
            is_primary=True,
            width=1920,
            height=1080,
            duration=3600.5,
            video_codec="h264",
            audio_codec="aac",
            frame_rate=30.0,
            bit_rate=5000000,
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(primary_file)

        # Add secondary file
        secondary_file = SceneFile(
            id="file-2",
            scene_id=scene.id,
            path="/videos/secondary.mp4",
            is_primary=False,
            width=1280,
            height=720,
            duration=3600.5,
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(secondary_file)

        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert len(scene.files) == 2
        assert scene.get_primary_file() == primary_file
        assert scene.get_primary_path() == "/videos/primary.mp4"

    @pytest.mark.asyncio
    async def test_get_primary_file_methods(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test get_primary_file and get_primary_path methods."""
        # Scene with no files
        scene_no_files = Scene(
            id="scene-no-files",
            title="No Files",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_no_files)
        await test_async_session.commit()
        await test_async_session.refresh(scene_no_files)

        assert scene_no_files.get_primary_file() is None
        assert scene_no_files.get_primary_path() is None

        # Scene with only non-primary files
        scene_no_primary = Scene(
            id="scene-no-primary",
            title="No Primary File",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_no_primary)
        await test_async_session.commit()

        non_primary_file = SceneFile(
            id="file-3",
            scene_id=scene_no_primary.id,
            path="/videos/file.mp4",
            is_primary=False,
            width=1920,
            height=1080,
            duration=1800.0,
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(non_primary_file)
        await test_async_session.commit()
        await test_async_session.refresh(scene_no_primary)

        # Should return first file if no primary
        assert scene_no_primary.get_primary_file() == non_primary_file
        assert scene_no_primary.get_primary_path() == "/videos/file.mp4"

    @pytest.mark.asyncio
    async def test_to_dict_method(
        self,
        test_async_session: AsyncSession,
    ) -> None:
        """Test to_dict method with relationships."""
        # Create all entities in the same transaction
        studio = Studio(
            id="studio-dict-test", name="Test Studio", last_synced=datetime.utcnow()
        )
        test_async_session.add(studio)

        performers = [
            Performer(
                id="perf-dict-1", name="Performer One", last_synced=datetime.utcnow()
            ),
        ]
        test_async_session.add_all(performers)

        tags = [
            Tag(id="tag-dict-1", name="Action", last_synced=datetime.utcnow()),
        ]
        test_async_session.add_all(tags)

        scene = Scene(
            id="scene-dict-test",
            title="Dictionary Test Scene",
            organized=True,
            analyzed=True,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
            studio_id=studio.id,
        )

        scene.add_performer(performers[0])
        scene.add_tag(tags[0])

        test_async_session.add(scene)
        await test_async_session.commit()

        # Query with explicit join to load studio relationship
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = (
            select(Scene)
            .where(Scene.id == "scene-dict-test")
            .options(
                joinedload(Scene.studio),
                joinedload(Scene.performers),
                joinedload(Scene.tags),
            )
        )
        result = await test_async_session.execute(stmt)
        scene = result.unique().scalar_one()

        scene_dict = scene.to_dict()

        assert scene_dict["id"] == "scene-dict-test"
        assert scene_dict["title"] == "Dictionary Test Scene"
        assert scene_dict["organized"] is True
        assert scene_dict["analyzed"] is True
        assert scene_dict["studio"] == {
            "id": studio.id,
            "name": studio.name,
        }
        assert scene_dict["performers"] == [
            {"id": performers[0].id, "name": performers[0].name}
        ]
        assert scene_dict["tags"] == [{"id": tags[0].id, "name": tags[0].name}]

        # Test exclude parameter
        scene_dict_excluded = scene.to_dict(exclude={"studio", "performers", "tags"})
        assert "studio" not in scene_dict_excluded
        assert "performers" not in scene_dict_excluded
        assert "tags" not in scene_dict_excluded

    @pytest.mark.asyncio
    async def test_scene_indexes(self, test_async_session: AsyncSession) -> None:
        """Test that scene indexes work correctly."""
        # Create scenes with different attributes for index testing
        scenes = []
        base_time = datetime.utcnow()

        for i in range(5):
            scene = Scene(
                id=f"scene-idx-{i}",
                title=f"Scene {i}",
                organized=i % 2 == 0,
                analyzed=i % 3 == 0,
                stash_created_at=base_time,
                stash_date=base_time - timedelta(days=i),
                last_synced=base_time - timedelta(hours=i),
            )
            scenes.append(scene)

        test_async_session.add_all(scenes)
        await test_async_session.commit()

        # Query using indexed fields
        from sqlalchemy import and_, select

        # Test organized + date index
        result = await test_async_session.execute(
            select(Scene).where(
                and_(
                    Scene.organized.is_(True),
                    Scene.stash_date >= base_time - timedelta(days=2),
                )
            )
        )
        organized_scenes = result.scalars().all()
        assert len(organized_scenes) == 2  # scenes 0 and 2

        # Test analyzed index
        result = await test_async_session.execute(
            select(Scene).where(Scene.analyzed.is_(True))
        )
        analyzed_scenes = result.scalars().all()
        assert len(analyzed_scenes) == 2  # scenes 0 and 3

    @pytest.mark.asyncio
    async def test_scene_cascade_delete(self, test_async_session: AsyncSession) -> None:
        """Test cascade delete for scene relationships."""
        scene = Scene(
            id="scene-cascade",
            title="Cascade Test",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Add a file
        scene_file = SceneFile(
            id="file-cascade",
            scene_id=scene.id,
            path="/test/cascade.mp4",
            is_primary=True,
            width=1920,
            height=1080,
            duration=100.0,
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_file)
        await test_async_session.commit()

        # Delete scene
        await test_async_session.delete(scene)
        await test_async_session.commit()

        # Check file is deleted
        from sqlalchemy import select

        result = await test_async_session.execute(
            select(SceneFile).where(SceneFile.id == "file-cascade")
        )
        assert result.scalar() is None

    @pytest.mark.asyncio
    async def test_scene_repr(self, test_async_session: AsyncSession) -> None:
        """Test string representation of scene."""
        scene = Scene(
            id="scene-repr",
            title="Repr Test",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        assert repr(scene) == "<Scene(id='scene-repr')>"

    @pytest.mark.asyncio
    async def test_scene_update_from_dict(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test updating scene from dictionary."""
        scene = Scene(
            id="scene-update",
            title="Original Title",
            organized=False,
            analyzed=False,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Update from dict
        update_data = {
            "title": "Updated Title",
            "organized": True,
            "analyzed": True,
            "details": "New details",
            "rating": 90,
        }
        scene.update_from_dict(update_data)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert scene.title == "Updated Title"
        assert scene.organized is True
        assert scene.analyzed is True
        assert scene.details == "New details"
        assert scene.rating == 90
        assert scene.id == "scene-update"  # ID should not change

    @pytest.mark.asyncio
    async def test_scene_nullable_fields(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test that nullable fields work correctly."""
        scene = Scene(
            id="scene-nullable",
            title="Nullable Test",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
            details=None,
            url=None,
            rating=None,
            studio_id=None,
            stash_updated_at=None,
            stash_date=None,
            content_checksum=None,
        )
        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert scene.details is None
        assert scene.url is None
        assert scene.rating is None
        assert scene.studio_id is None
        assert scene.stash_updated_at is None
        assert scene.stash_date is None
        assert scene.content_checksum is None

    @pytest.mark.asyncio
    async def test_scene_defaults(self, test_async_session: AsyncSession) -> None:
        """Test default values for scene fields."""
        scene = Scene(
            id="scene-defaults",
            title="Default Test",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()
        await test_async_session.refresh(scene)

        assert scene.organized is False
        assert scene.analyzed is False
        assert scene.video_analyzed is False
        assert scene.created_at is not None
        assert scene.updated_at is not None

    @pytest.mark.asyncio
    async def test_scene_edge_cases(self, test_async_session: AsyncSession) -> None:
        """Test edge cases for scene model."""
        # Test empty title
        scene_empty_title = Scene(
            id="scene-empty",
            title="",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_empty_title)
        await test_async_session.commit()
        assert scene_empty_title.title == ""

        # Test very long title
        long_title = "A" * 1000
        scene_long_title = Scene(
            id="scene-long",
            title=long_title,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_long_title)
        await test_async_session.commit()
        assert scene_long_title.title == long_title

        # Test rating boundaries
        scene_min_rating = Scene(
            id="scene-min-rating",
            title="Min Rating",
            rating=0,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_min_rating)
        await test_async_session.commit()
        assert scene_min_rating.rating == 0

        scene_max_rating = Scene(
            id="scene-max-rating",
            title="Max Rating",
            rating=100,
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene_max_rating)
        await test_async_session.commit()
        assert scene_max_rating.rating == 100

    @pytest.mark.asyncio
    async def test_scene_without_relationships_to_dict(
        self, test_async_session: AsyncSession
    ) -> None:
        """Test to_dict when relationships are not loaded."""
        scene = Scene(
            id="scene-no-rel",
            title="No Relationships",
            stash_created_at=datetime.utcnow(),
            last_synced=datetime.utcnow(),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Create a new session to ensure relationships aren't loaded
        from sqlalchemy import select

        result = await test_async_session.execute(
            select(Scene).where(Scene.id == "scene-no-rel")
        )
        scene_unloaded = result.scalar_one()

        # Should handle missing relationships gracefully
        scene_dict = scene_unloaded.to_dict()
        assert "studio" not in scene_dict or scene_dict["studio"] is None
        assert scene_dict.get("performers", []) == []
        assert scene_dict.get("tags", []) == []
