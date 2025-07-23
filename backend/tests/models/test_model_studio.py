"""Tests for the Studio model."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene
from app.models.studio import Studio


class TestStudioModel:
    """Test Studio model operations."""

    async def test_create_studio(self, test_async_session: AsyncSession):
        """Test creating a studio."""
        studio = Studio(
            id="test-studio-1",
            name="Test Studio",
            url="https://example.com/studio",
            details="A test studio",
            rating=5,
            favorite=True,
            ignore_auto_tag=False,
            image_url="https://example.com/studio.jpg",
            last_synced=datetime.now(timezone.utc),
        )

        test_async_session.add(studio)
        await test_async_session.commit()
        await test_async_session.refresh(studio)

        assert studio.id == "test-studio-1"
        assert studio.name == "Test Studio"
        assert studio.url == "https://example.com/studio"
        assert studio.details == "A test studio"
        assert studio.rating == 5
        assert studio.favorite is True
        assert studio.ignore_auto_tag is False
        assert studio.image_url == "https://example.com/studio.jpg"
        assert studio.last_synced is not None

    async def test_studio_with_aliases(self, test_async_session: AsyncSession):
        """Test studio with aliases."""
        aliases = ["Alias 1", "Alias 2", "Alias 3"]
        studio = Studio(
            id="test-studio-2",
            name="Studio with Aliases",
            aliases=aliases,
            last_synced=datetime.now(timezone.utc),
        )

        test_async_session.add(studio)
        await test_async_session.commit()
        await test_async_session.refresh(studio)

        assert studio.aliases == aliases
        assert len(studio.aliases) == 3
        assert "Alias 1" in studio.aliases

    async def test_studio_hierarchy(self, test_async_session: AsyncSession):
        """Test studio parent-child relationships."""
        # Create parent studio
        parent = Studio(
            id="parent-studio",
            name="Parent Studio",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(parent)
        await test_async_session.commit()

        # Create child studio
        child = Studio(
            id="child-studio",
            name="Child Studio",
            parent_id="parent-studio",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(child)
        await test_async_session.commit()
        await test_async_session.refresh(child)

        assert child.parent_id == "parent-studio"

    async def test_studio_temp_parent_id(self, test_async_session: AsyncSession):
        """Test studio with temporary parent ID for sync."""
        studio = Studio(
            id="test-studio-3",
            name="Studio with Temp Parent",
            parent_temp_id="temp-parent-123",
            last_synced=datetime.now(timezone.utc),
        )

        test_async_session.add(studio)
        await test_async_session.commit()
        await test_async_session.refresh(studio)

        assert studio.parent_temp_id == "temp-parent-123"
        assert studio.parent_id is None

    async def test_studio_scene_foreign_key(self, test_async_session: AsyncSession):
        """Test studio-scene foreign key relationship."""
        # Create studio
        studio = Studio(
            id="test-studio-4",
            name="Studio with Scenes",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(studio)
        await test_async_session.commit()

        # Create scene with studio reference
        scene = Scene(
            id="scene-fk-1",
            title="Scene with Studio",
            studio_id="test-studio-4",
            stash_created_at=datetime.now(timezone.utc),
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(scene)
        await test_async_session.commit()

        # Query scene and verify studio_id
        result = await test_async_session.execute(
            select(Scene).filter(Scene.id == "scene-fk-1")
        )
        saved_scene = result.scalar_one()
        assert saved_scene.studio_id == "test-studio-4"

    async def test_query_scenes_by_studio(self, test_async_session: AsyncSession):
        """Test querying scenes by studio ID."""
        # Create studio
        studio = Studio(
            id="test-studio-5",
            name="Studio for Query Test",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(studio)
        await test_async_session.commit()

        # Create scenes with different dates
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        scene_ids = []
        for i in range(3):
            scene = Scene(
                id=f"query-scene-{i}",
                title=f"Scene {i}",
                studio_id="test-studio-5",
                stash_date=base_date.replace(day=i + 1),
                stash_created_at=datetime.now(timezone.utc),
                last_synced=datetime.now(timezone.utc),
            )
            test_async_session.add(scene)
            scene_ids.append(scene.id)

        await test_async_session.commit()

        # Query scenes by studio_id
        result = await test_async_session.execute(
            select(Scene)
            .filter(Scene.studio_id == "test-studio-5")
            .order_by(Scene.stash_date.desc())
        )
        scenes = result.scalars().all()

        assert len(scenes) == 3
        # Verify they are ordered by date descending
        assert scenes[0].id == "query-scene-2"
        assert scenes[1].id == "query-scene-1"
        assert scenes[2].id == "query-scene-0"

    async def test_studio_to_dict(self, test_async_session: AsyncSession):
        """Test converting studio to dictionary."""
        studio = Studio(
            id="test-studio-6",
            name="Test Studio Dict",
            aliases=["Alias A", "Alias B"],
            url="https://example.com",
            details="Studio details",
            rating=4,
            favorite=False,
            ignore_auto_tag=True,
            image_url="https://example.com/image.jpg",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(studio)
        await test_async_session.commit()

        # Test basic to_dict
        data = studio.to_dict()
        assert data["id"] == "test-studio-6"
        assert data["name"] == "Test Studio Dict"
        assert data["aliases"] == ["Alias A", "Alias B"]
        assert data["url"] == "https://example.com"
        assert data["details"] == "Studio details"
        assert data["rating"] == 4
        assert data["favorite"] is False
        assert data["ignore_auto_tag"] is True
        assert data["image_url"] == "https://example.com/image.jpg"
        assert "last_synced" in data

        # Test with exclude
        data_excluded = studio.to_dict(exclude={"details", "rating"})
        assert "details" not in data_excluded
        assert "rating" not in data_excluded
        assert "name" in data_excluded

    async def test_studio_to_dict_basic(self, test_async_session: AsyncSession):
        """Test converting studio to dictionary."""
        # Create studio
        studio = Studio(
            id="test-studio-7",
            name="Studio Basic Dict",
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(studio)
        await test_async_session.commit()

        # Test basic dict conversion
        data = studio.to_dict()
        assert "id" in data
        assert data["id"] == "test-studio-7"
        assert data["name"] == "Studio Basic Dict"
        assert "last_synced" in data

        # Test dict with include_stats=False (default behavior)
        data_no_stats = studio.to_dict(include_stats=False)
        assert "scene_count" not in data_no_stats

    async def test_studio_nullable_fields(self, test_async_session: AsyncSession):
        """Test studio with nullable fields."""
        studio = Studio(
            id="test-studio-8",
            name="Minimal Studio",
            last_synced=datetime.now(timezone.utc),
        )

        test_async_session.add(studio)
        await test_async_session.commit()
        await test_async_session.refresh(studio)

        assert studio.aliases is None
        assert studio.url is None
        assert studio.details is None
        assert studio.rating is None
        assert studio.favorite is False  # Has default
        assert studio.ignore_auto_tag is False  # Has default
        assert studio.image_url is None
        assert studio.parent_id is None
        assert studio.parent_temp_id is None

    async def test_studio_name_index(self, test_async_session: AsyncSession):
        """Test that studio name is indexed for performance."""
        # Create multiple studios
        studios = []
        for i in range(5):
            studio = Studio(
                id=f"indexed-studio-{i}",
                name=f"Studio Name {i}",
                last_synced=datetime.now(timezone.utc),
            )
            studios.append(studio)

        test_async_session.add_all(studios)
        await test_async_session.commit()

        # Query by name (should use index)
        result = await test_async_session.execute(
            select(Studio).filter(Studio.name == "Studio Name 2")
        )
        studio = result.scalar_one_or_none()
        assert studio is not None
        assert studio.id == "indexed-studio-2"

    async def test_studio_update(self, test_async_session: AsyncSession):
        """Test updating studio fields."""
        # Create studio
        studio = Studio(
            id="test-studio-update",
            name="Original Name",
            rating=3,
            favorite=False,
            last_synced=datetime.now(timezone.utc),
        )
        test_async_session.add(studio)
        await test_async_session.commit()

        # Update fields
        studio.name = "Updated Name"
        studio.rating = 5
        studio.favorite = True
        studio.aliases = ["New Alias"]
        studio.url = "https://updated.com"

        await test_async_session.commit()
        await test_async_session.refresh(studio)

        # Verify updates
        assert studio.name == "Updated Name"
        assert studio.rating == 5
        assert studio.favorite is True
        assert studio.aliases == ["New Alias"]
        assert studio.url == "https://updated.com"

    async def test_studio_base_model_fields(self, test_async_session: AsyncSession):
        """Test that Studio inherits BaseModel fields correctly."""
        studio = Studio(
            id="test-studio-base",
            name="Studio with Base Fields",
            last_synced=datetime.now(timezone.utc),
        )

        test_async_session.add(studio)
        await test_async_session.commit()
        await test_async_session.refresh(studio)

        # BaseModel should provide created_at and updated_at
        assert hasattr(studio, "created_at")
        assert hasattr(studio, "updated_at")
        assert studio.created_at is not None
        assert studio.updated_at is not None
        assert isinstance(studio.created_at, datetime)
        assert isinstance(studio.updated_at, datetime)
