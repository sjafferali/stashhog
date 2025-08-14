"""Tests for the PlanChange model."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.plan_change import ChangeAction, ChangeStatus, PlanChange


@pytest.fixture
def plan_change():
    """Create a test plan change."""
    change = PlanChange(
        plan_id=1,
        scene_id="scene123",
        field="title",
        action=ChangeAction.UPDATE,
        current_value="Old Title",
        proposed_value="New Title",
        confidence=0.95,
        status=ChangeStatus.PENDING,
    )
    change.id = 1
    return change


@pytest.fixture
def mock_plan():
    """Create a mock analysis plan."""
    plan = MagicMock()
    plan.id = 1
    plan.can_be_applied.return_value = True
    return plan


@pytest.fixture
def mock_scene():
    """Create a mock scene."""
    scene = MagicMock()
    scene.id = "scene123"
    scene.title = "Test Scene"
    return scene


class TestPlanChange:
    """Test PlanChange model functionality."""

    def test_initialization(self):
        """Test PlanChange initialization."""
        change = PlanChange(
            plan_id=1,
            scene_id="scene456",
            field="details",
            action=ChangeAction.SET,
            current_value=None,
            proposed_value="New details",
            confidence=0.85,
            status=ChangeStatus.PENDING,
        )
        assert change.plan_id == 1
        assert change.scene_id == "scene456"
        assert change.field == "details"
        assert change.action == ChangeAction.SET
        assert change.current_value is None
        assert change.proposed_value == "New details"
        assert change.confidence == 0.85
        assert change.status == ChangeStatus.PENDING
        # Legacy fields are not set in __init__, they get defaults after DB commit
        # We won't test them here since they're not part of initialization

    def test_change_action_enum(self):
        """Test ChangeAction enum values."""
        assert ChangeAction.ADD == "add"
        assert ChangeAction.REMOVE == "remove"
        assert ChangeAction.UPDATE == "update"
        assert ChangeAction.SET == "set"

    def test_change_status_enum(self):
        """Test ChangeStatus enum values."""
        assert ChangeStatus.PENDING == "pending"
        assert ChangeStatus.APPROVED == "approved"
        assert ChangeStatus.REJECTED == "rejected"
        assert ChangeStatus.APPLIED == "applied"

    def test_get_display_value_none(self, plan_change):
        """Test get_display_value with None."""
        result = plan_change.get_display_value(None)
        assert result == "None"

    def test_get_display_value_list(self, plan_change):
        """Test get_display_value with list."""
        result = plan_change.get_display_value(["tag1", "tag2", "tag3"])
        assert result == "tag1, tag2, tag3"

    def test_get_display_value_dict_with_name(self, plan_change):
        """Test get_display_value with dict containing name."""
        result = plan_change.get_display_value({"name": "Studio Name"})
        assert result == "Studio Name"

    def test_get_display_value_dict_with_id_and_name(self, plan_change):
        """Test get_display_value with dict containing id and name."""
        # Due to the order of checks in get_display_value, if "name" exists,
        # it returns just the name, not "name (id)"
        result = plan_change.get_display_value({"id": "123", "name": "Studio Name"})
        assert result == "Studio Name"

    def test_get_display_value_string(self, plan_change):
        """Test get_display_value with string."""
        result = plan_change.get_display_value("Simple String")
        assert result == "Simple String"

    def test_get_display_value_other_types(self, plan_change):
        """Test get_display_value with other types."""
        # Integer
        result = plan_change.get_display_value(42)
        assert result == "42"

        # Float
        result = plan_change.get_display_value(3.14)
        assert result == "3.14"

        # Boolean
        result = plan_change.get_display_value(True)
        assert result == "True"

    def test_get_change_description_add(self, plan_change):
        """Test get_change_description for ADD action."""
        plan_change.action = ChangeAction.ADD
        plan_change.field = "tags"
        plan_change.proposed_value = {"name": "NewTag"}

        description = plan_change.get_change_description()
        assert description == "Add NewTag to tags"

    def test_get_change_description_remove(self, plan_change):
        """Test get_change_description for REMOVE action."""
        plan_change.action = ChangeAction.REMOVE
        plan_change.field = "performers"
        plan_change.proposed_value = {"name": "Performer Name"}

        description = plan_change.get_change_description()
        assert description == "Remove Performer Name from performers"

    def test_get_change_description_update(self, plan_change):
        """Test get_change_description for UPDATE action."""
        plan_change.action = ChangeAction.UPDATE
        plan_change.field = "title"
        plan_change.current_value = "Old Title"
        plan_change.proposed_value = "New Title"

        description = plan_change.get_change_description()
        assert description == "Update title from 'Old Title' to 'New Title'"

    def test_get_change_description_set(self, plan_change):
        """Test get_change_description for SET action."""
        plan_change.action = ChangeAction.SET
        plan_change.field = "studio"
        plan_change.proposed_value = {"name": "Studio X"}

        description = plan_change.get_change_description()
        assert description == "Set studio to 'Studio X'"

    def test_is_high_confidence_default_threshold(self, plan_change):
        """Test is_high_confidence with default threshold."""
        plan_change.confidence = 0.95
        assert plan_change.is_high_confidence() is True

        plan_change.confidence = 0.75
        assert plan_change.is_high_confidence() is False

        plan_change.confidence = 0.8
        assert plan_change.is_high_confidence() is True

    def test_is_high_confidence_custom_threshold(self, plan_change):
        """Test is_high_confidence with custom threshold."""
        plan_change.confidence = 0.85
        assert plan_change.is_high_confidence(0.9) is False
        assert plan_change.is_high_confidence(0.8) is True
        assert plan_change.is_high_confidence(0.85) is True

    def test_is_high_confidence_none_confidence(self, plan_change):
        """Test is_high_confidence when confidence is None."""
        plan_change.confidence = None
        assert plan_change.is_high_confidence() is False

    def test_can_be_applied_success(self, plan_change, mock_plan):
        """Test can_be_applied when change can be applied."""
        plan_change.plan = mock_plan
        plan_change.status = ChangeStatus.PENDING

        assert plan_change.can_be_applied() is True

    def test_can_be_applied_already_applied(self, plan_change, mock_plan):
        """Test can_be_applied when already applied."""
        plan_change.plan = mock_plan
        plan_change.status = ChangeStatus.APPLIED

        assert plan_change.can_be_applied() is False

    def test_can_be_applied_rejected(self, plan_change, mock_plan):
        """Test can_be_applied when rejected."""
        plan_change.plan = mock_plan
        plan_change.status = ChangeStatus.REJECTED

        assert plan_change.can_be_applied() is False

    def test_can_be_applied_plan_cannot_be_applied(self, plan_change, mock_plan):
        """Test can_be_applied when plan cannot be applied."""
        plan_change.plan = mock_plan
        plan_change.status = ChangeStatus.PENDING
        mock_plan.can_be_applied.return_value = False

        assert plan_change.can_be_applied() is False

    def test_to_dict_basic(self, plan_change):
        """Test to_dict basic functionality."""
        with patch.object(plan_change, "can_be_applied", return_value=True):
            result = plan_change.to_dict()

            assert result["id"] == 1
            assert result["plan_id"] == 1
            assert result["scene_id"] == "scene123"
            assert result["field"] == "title"
            assert result["action"] == ChangeAction.UPDATE
            assert result["current_value"] == "Old Title"
            assert result["proposed_value"] == "New Title"
            assert result["confidence"] == 0.95
            assert result["status"] == ChangeStatus.PENDING
            assert (
                result["change_description"]
                == "Update title from 'Old Title' to 'New Title'"
            )
            assert result["can_apply"] is True

    def test_to_dict_with_scene(self, plan_change, mock_scene):
        """Test to_dict with scene loaded."""
        plan_change.scene = mock_scene

        with patch.object(plan_change, "can_be_applied", return_value=True):
            result = plan_change.to_dict()

            assert result["scene_title"] == "Test Scene"

    def test_to_dict_with_exclude(self, plan_change):
        """Test to_dict with exclude parameter."""
        with patch.object(plan_change, "can_be_applied", return_value=True):
            result = plan_change.to_dict(exclude={"confidence", "current_value"})

            assert "confidence" not in result
            assert "current_value" not in result
            assert "proposed_value" in result
            assert "change_description" in result

    def test_relationships(self):
        """Test relationship configuration."""
        change = PlanChange(
            plan_id=1,
            scene_id="test",
            field="title",
            action=ChangeAction.SET,
            proposed_value="Test",
        )
        assert hasattr(change, "plan")
        assert hasattr(change, "scene")

    def test_table_indexes(self):
        """Test that proper indexes are defined."""
        # Check that the table args define the expected indexes
        table_args = PlanChange.__table_args__
        assert len(table_args) == 4  # Updated after removing idx_change_applied_plan

        # Check index names
        index_names = [idx.name for idx in table_args]
        assert "idx_change_plan_field" in index_names
        assert "idx_change_scene_field" in index_names
        assert "idx_change_status_plan" in index_names
        assert "idx_change_confidence" in index_names


class TestPlanChangeEdgeCases:
    """Test edge cases and error scenarios."""

    def test_complex_proposed_values(self, plan_change):
        """Test handling of complex proposed values."""
        # List of dicts
        plan_change.proposed_value = [
            {"id": "1", "name": "Tag 1"},
            {"id": "2", "name": "Tag 2"},
        ]
        plan_change.action = ChangeAction.ADD
        plan_change.field = "tags"

        display = plan_change.get_display_value(plan_change.proposed_value)
        assert "Tag 1" in display
        assert "Tag 2" in display

    def test_empty_list_values(self, plan_change):
        """Test handling of empty lists."""
        plan_change.proposed_value = []
        display = plan_change.get_display_value(plan_change.proposed_value)
        assert display == ""

    def test_dict_without_name_or_id(self, plan_change):
        """Test dict display without name or id fields."""
        value = {"type": "special", "value": 42}
        display = plan_change.get_display_value(value)
        assert display == str(value)

    def test_unicode_in_values(self, plan_change):
        """Test handling of unicode characters."""
        plan_change.current_value = "Café"
        plan_change.proposed_value = "Café ☕"
        plan_change.action = ChangeAction.UPDATE

        description = plan_change.get_change_description()
        assert "Café" in description
        assert "☕" in description

    def test_very_long_values(self, plan_change):
        """Test handling of very long values."""
        long_text = "A" * 1000
        plan_change.proposed_value = long_text

        display = plan_change.get_display_value(plan_change.proposed_value)
        assert len(display) == 1000
        assert display == long_text

    def test_status_field_behavior(self):
        """Test status field behavior."""
        change = PlanChange(
            plan_id=1,
            scene_id="test",
            field="title",
            action=ChangeAction.SET,
            proposed_value="Test",
            status=ChangeStatus.APPLIED,
            applied_at=datetime.now(timezone.utc),
        )

        assert change.status == ChangeStatus.APPLIED
        assert change.applied_at is not None

    def test_status_transitions(self, plan_change):
        """Test different status transitions."""
        # PENDING -> APPROVED
        plan_change.status = ChangeStatus.PENDING
        plan_change.status = ChangeStatus.APPROVED
        assert plan_change.status == ChangeStatus.APPROVED

        # APPROVED -> APPLIED
        plan_change.status = ChangeStatus.APPLIED
        assert plan_change.status == ChangeStatus.APPLIED

        # PENDING -> REJECTED
        change2 = PlanChange(
            plan_id=1,
            scene_id="test",
            field="title",
            action=ChangeAction.SET,
            proposed_value="Test",
            status=ChangeStatus.PENDING,
        )
        change2.status = ChangeStatus.REJECTED
        assert change2.status == ChangeStatus.REJECTED

    def test_json_field_handling(self):
        """Test JSON field serialization/deserialization."""
        complex_value = {
            "nested": {"array": [1, 2, 3], "string": "test", "bool": True, "null": None}
        }

        change = PlanChange(
            plan_id=1,
            scene_id="test",
            field="metadata",
            action=ChangeAction.SET,
            current_value=None,
            proposed_value=complex_value,
        )

        assert change.proposed_value == complex_value
        assert change.proposed_value["nested"]["array"] == [1, 2, 3]
