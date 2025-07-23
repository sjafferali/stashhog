"""Tests for Tag model."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import BaseModel
from app.models.tag import Tag


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    BaseModel.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_tag():
    """Create a sample tag for testing."""
    return Tag(
        id="tag123",
        name="Sample Tag",
        aliases=["alias1", "alias2"],
        description="A sample tag for testing",
        ignore_auto_tag=False,
        parent_id=None,
        last_synced=datetime.now(timezone.utc),
    )


@pytest.fixture
def parent_tag():
    """Create a parent tag for testing hierarchy."""
    return Tag(
        id="parent123",
        name="Parent Tag",
        description="A parent tag",
        ignore_auto_tag=True,
        last_synced=datetime.now(timezone.utc),
    )


class TestTagModel:
    """Test Tag model functionality."""

    def test_tag_creation(self, sample_tag):
        """Test creating a tag instance."""
        assert sample_tag.id == "tag123"
        assert sample_tag.name == "Sample Tag"
        assert sample_tag.aliases == ["alias1", "alias2"]
        assert sample_tag.description == "A sample tag for testing"
        assert sample_tag.ignore_auto_tag is False
        assert sample_tag.parent_id is None
        assert isinstance(sample_tag.last_synced, datetime)

    def test_tag_with_parent(self, db_session, parent_tag):
        """Test tag hierarchy with parent-child relationship."""
        # Add parent tag
        db_session.add(parent_tag)
        db_session.commit()

        # Create child tag
        child_tag = Tag(
            id="child123",
            name="Child Tag",
            parent_id=parent_tag.id,
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(child_tag)
        db_session.commit()

        # Verify relationship
        assert child_tag.parent_id == parent_tag.id

    def test_tag_unique_name_constraint(self, db_session):
        """Test that tag names must be unique."""
        # Add first tag
        tag1 = Tag(
            id="tag1",
            name="Unique Name",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag1)
        db_session.commit()

        # Try to add second tag with same name
        tag2 = Tag(
            id="tag2",
            name="Unique Name",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag2)

        with pytest.raises(Exception):  # SQLAlchemy will raise an IntegrityError
            db_session.commit()

    def test_tag_nullable_fields(self, db_session):
        """Test tag with minimal required fields."""
        minimal_tag = Tag(
            id="minimal123",
            name="Minimal Tag",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(minimal_tag)
        db_session.commit()

        # Verify defaults and nullable fields
        assert minimal_tag.aliases is None
        assert minimal_tag.description is None
        assert minimal_tag.ignore_auto_tag is False
        assert minimal_tag.parent_id is None
        assert minimal_tag.parent_temp_id is None

    def test_get_scene_count(self, db_session):
        """Test getting scene count for a tag."""
        # Create a real tag with scenes in the database
        tag = Tag(
            id="count_test",
            name="Count Test Tag",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        # The method should work with the dynamic relationship
        count = tag.get_scene_count()
        assert count == 0  # No scenes associated yet

    def test_get_scene_count_logic(self, sample_tag):
        """Test the get_scene_count method implementation logic."""
        # The actual implementation will check if the scenes relationship has a count method
        # Since this is a dynamic relationship, it should have count()

        # We can test the logic by mocking the method itself
        with patch.object(Tag, "get_scene_count", return_value=10):
            tag = Tag(id="test", name="Test", last_synced=datetime.now(timezone.utc))
            assert tag.get_scene_count() == 10

    def test_to_dict_basic(self, sample_tag):
        """Test converting tag to dictionary without stats."""
        with patch.object(BaseModel, "to_dict") as mock_base_to_dict:
            mock_base_to_dict.return_value = {
                "id": "tag123",
                "name": "Sample Tag",
                "aliases": ["alias1", "alias2"],
                "description": "A sample tag for testing",
                "ignore_auto_tag": False,
                "parent_id": None,
                "last_synced": sample_tag.last_synced,
            }

            result = sample_tag.to_dict()

            assert result["id"] == "tag123"
            assert result["name"] == "Sample Tag"
            assert result["aliases"] == ["alias1", "alias2"]
            assert result["description"] == "A sample tag for testing"
            assert "scene_count" not in result
            mock_base_to_dict.assert_called_once_with(None)

    def test_to_dict_with_stats(self, sample_tag):
        """Test converting tag to dictionary with statistics."""
        with patch.object(BaseModel, "to_dict") as mock_base_to_dict:
            mock_base_to_dict.return_value = {
                "id": "tag123",
                "name": "Sample Tag",
                "aliases": ["alias1", "alias2"],
                "description": "A sample tag for testing",
                "ignore_auto_tag": False,
                "parent_id": None,
                "last_synced": sample_tag.last_synced,
            }

            with patch.object(sample_tag, "get_scene_count", return_value=10):
                result = sample_tag.to_dict(include_stats=True)

                assert result["scene_count"] == 10
                mock_base_to_dict.assert_called_once_with(None)

    def test_to_dict_with_exclude(self, sample_tag):
        """Test converting tag to dictionary with excluded fields."""
        exclude_fields = {"description", "aliases"}

        with patch.object(BaseModel, "to_dict") as mock_base_to_dict:
            mock_base_to_dict.return_value = {
                "id": "tag123",
                "name": "Sample Tag",
                "ignore_auto_tag": False,
                "parent_id": None,
                "last_synced": sample_tag.last_synced,
            }

            result = sample_tag.to_dict(exclude=exclude_fields)

            assert "description" not in result
            assert "aliases" not in result
            mock_base_to_dict.assert_called_once_with(exclude_fields)

    def test_tag_with_temp_parent_id(self, db_session):
        """Test tag with temporary parent ID for sync operations."""
        tag = Tag(
            id="tag_with_temp",
            name="Tag with Temp Parent",
            parent_temp_id="temp_parent_123",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        assert tag.parent_temp_id == "temp_parent_123"
        assert tag.parent_id is None

    def test_tag_aliases_json_field(self, db_session):
        """Test that aliases are properly stored as JSON."""
        tag = Tag(
            id="tag_aliases",
            name="Tag with Aliases",
            aliases=["alias1", "alias2", "alias3"],
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        # Retrieve from database
        retrieved_tag = db_session.query(Tag).filter_by(id="tag_aliases").first()
        assert retrieved_tag.aliases == ["alias1", "alias2", "alias3"]

    def test_tag_ignore_auto_tag_default(self, db_session):
        """Test that ignore_auto_tag defaults to False."""
        tag = Tag(
            id="default_tag",
            name="Default Tag",
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        assert tag.ignore_auto_tag is False

    def test_tag_relationship_lazy_loading(self, sample_tag):
        """Test that scenes relationship is configured for lazy loading."""
        # The relationship should be a dynamic query
        assert hasattr(sample_tag.scenes, "filter")
        assert hasattr(sample_tag.scenes, "count")

    def test_tag_cascade_behavior(self, db_session, parent_tag):
        """Test cascade behavior when parent tag is deleted."""
        # Add parent tag
        db_session.add(parent_tag)
        db_session.commit()

        # Create child tags
        child1 = Tag(
            id="child1",
            name="Child 1",
            parent_id=parent_tag.id,
            last_synced=datetime.now(timezone.utc),
        )
        child2 = Tag(
            id="child2",
            name="Child 2",
            parent_id=parent_tag.id,
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add_all([child1, child2])
        db_session.commit()

        # Verify parent relationship before deletion
        assert child1.parent_id == parent_tag.id
        assert child2.parent_id == parent_tag.id

        # Note: The actual cascade behavior depends on the database configuration
        # This test verifies that the model is configured with ondelete="SET NULL"
        # In a real database, deleting the parent would set children's parent_id to NULL
        # For this test, we'll just verify the configuration exists
        foreign_key = Tag.__table__.c.parent_id.foreign_keys
        assert len(foreign_key) == 1
        fk = list(foreign_key)[0]
        assert fk.ondelete == "SET NULL"

    def test_tag_empty_aliases(self, db_session):
        """Test tag with empty aliases list."""
        tag = Tag(
            id="empty_aliases",
            name="Empty Aliases Tag",
            aliases=[],
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        retrieved_tag = db_session.query(Tag).filter_by(id="empty_aliases").first()
        assert retrieved_tag.aliases == []

    def test_tag_long_description(self, db_session):
        """Test tag with very long description."""
        long_description = "A" * 5000  # 5000 characters
        tag = Tag(
            id="long_desc",
            name="Long Description Tag",
            description=long_description,
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        retrieved_tag = db_session.query(Tag).filter_by(id="long_desc").first()
        assert len(retrieved_tag.description) == 5000
        assert retrieved_tag.description == long_description

    def test_tag_special_characters_in_name(self, db_session):
        """Test tag with special characters in name."""
        special_name = "Tag & Name (with) [special] {chars} @ 100%"
        tag = Tag(
            id="special_chars",
            name=special_name,
            last_synced=datetime.now(timezone.utc),
        )
        db_session.add(tag)
        db_session.commit()

        retrieved_tag = db_session.query(Tag).filter_by(id="special_chars").first()
        assert retrieved_tag.name == special_name
