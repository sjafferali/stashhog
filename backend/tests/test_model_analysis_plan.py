"""Tests for the AnalysisPlan model."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from sqlalchemy.orm import Query

from app.models.analysis_plan import AnalysisPlan, PlanStatus


@pytest.fixture
def analysis_plan():
    """Create a test analysis plan."""
    plan = AnalysisPlan(
        name="Test Plan",
        description="Test description",
        plan_metadata={"test_key": "test_value"},
        status=PlanStatus.DRAFT,
    )
    plan.id = 1
    return plan


@pytest.fixture
def mock_changes_query():
    """Create a mock query for changes relationship."""
    mock_query = MagicMock(spec=Query)
    mock_query.count.return_value = 0
    mock_query.filter_by.return_value = mock_query
    mock_query.all.return_value = []
    return mock_query


class TestAnalysisPlan:
    """Test AnalysisPlan model functionality."""

    def test_initialization(self):
        """Test AnalysisPlan initialization."""
        plan = AnalysisPlan(
            name="New Plan",
            description="A new analysis plan",
            plan_metadata={"key": "value"},
            status=PlanStatus.DRAFT,  # Explicitly set status
        )
        assert plan.name == "New Plan"
        assert plan.description == "A new analysis plan"
        assert plan.plan_metadata == {"key": "value"}
        assert plan.status == PlanStatus.DRAFT
        assert plan.applied_at is None

    def test_plan_status_enum(self):
        """Test PlanStatus enum values."""
        assert PlanStatus.DRAFT == "DRAFT"
        assert PlanStatus.REVIEWING == "REVIEWING"
        assert PlanStatus.APPLIED == "APPLIED"
        assert PlanStatus.CANCELLED == "CANCELLED"

    def test_get_change_count_with_query(self, analysis_plan, mock_changes_query):
        """Test get_change_count with query interface."""
        mock_changes_query.count.return_value = 5

        # Mock the get_change_count method implementation
        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes:
            mock_changes.return_value = mock_changes_query
            count = analysis_plan.get_change_count()
            assert count == 5
            mock_changes_query.count.assert_called_once()

    def test_get_change_count_with_list(self, analysis_plan):
        """Test get_change_count with list interface."""
        # When changes doesn't have count method
        changes_list = [MagicMock() for _ in range(3)]
        analysis_plan.changes = changes_list

        count = analysis_plan.get_change_count()
        assert count == 3

    def test_get_applied_change_count(self, analysis_plan, mock_changes_query):
        """Test get_applied_change_count."""
        mock_changes_query.filter_by.return_value.count.return_value = 2

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes:
            mock_changes.return_value = mock_changes_query
            count = analysis_plan.get_applied_change_count()
            assert count == 2
            from app.models.plan_change import ChangeStatus

            mock_changes_query.filter_by.assert_called_with(status=ChangeStatus.APPLIED)

    def test_get_accepted_change_count(self, analysis_plan, mock_changes_query):
        """Test get_accepted_change_count."""
        mock_changes_query.filter_by.return_value.count.return_value = 3

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes:
            mock_changes.return_value = mock_changes_query
            count = analysis_plan.get_accepted_change_count()
            assert count == 3
            from app.models.plan_change import ChangeStatus

            mock_changes_query.filter_by.assert_called_with(
                status=ChangeStatus.APPROVED
            )

    def test_get_pending_change_count(self, analysis_plan, mock_changes_query):
        """Test get_pending_change_count."""
        mock_changes_query.filter_by.return_value.count.return_value = 4

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes:
            mock_changes.return_value = mock_changes_query
            count = analysis_plan.get_pending_change_count()
            assert count == 4
            from app.models.plan_change import ChangeStatus

            mock_changes_query.filter_by.assert_called_with(status=ChangeStatus.PENDING)

    def test_get_rejected_change_count(self, analysis_plan, mock_changes_query):
        """Test get_rejected_change_count."""
        mock_changes_query.filter_by.return_value.count.return_value = 1

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes:
            mock_changes.return_value = mock_changes_query
            count = analysis_plan.get_rejected_change_count()
            assert count == 1
            from app.models.plan_change import ChangeStatus

            mock_changes_query.filter_by.assert_called_with(
                status=ChangeStatus.REJECTED
            )

    def test_get_changes_by_field(self, analysis_plan, mock_changes_query):
        """Test get_changes_by_field."""
        mock_changes = [MagicMock(field="title"), MagicMock(field="title")]
        mock_changes_query.filter_by.return_value.all.return_value = mock_changes

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes_prop:
            mock_changes_prop.return_value = mock_changes_query
            changes = analysis_plan.get_changes_by_field("title")
            assert len(changes) == 2
            mock_changes_query.filter_by.assert_called_with(field="title")

    def test_get_changes_by_scene(self, analysis_plan, mock_changes_query):
        """Test get_changes_by_scene."""
        mock_changes = [MagicMock(scene_id="scene1")]
        mock_changes_query.filter_by.return_value.all.return_value = mock_changes

        with patch.object(
            type(analysis_plan), "changes", new_callable=PropertyMock
        ) as mock_changes_prop:
            mock_changes_prop.return_value = mock_changes_query
            changes = analysis_plan.get_changes_by_scene("scene1")
            assert len(changes) == 1
            mock_changes_query.filter_by.assert_called_with(scene_id="scene1")

    def test_add_metadata(self, analysis_plan):
        """Test add_metadata."""
        # Add to existing metadata
        analysis_plan.add_metadata("new_key", "new_value")
        assert analysis_plan.plan_metadata["new_key"] == "new_value"
        assert analysis_plan.plan_metadata["test_key"] == "test_value"

        # Add when metadata is None
        analysis_plan.plan_metadata = None
        analysis_plan.add_metadata("key", "value")
        assert analysis_plan.plan_metadata == {"key": "value"}

    def test_get_metadata(self, analysis_plan):
        """Test get_metadata."""
        # Get existing key
        value = analysis_plan.get_metadata("test_key")
        assert value == "test_value"

        # Get non-existent key with default
        value = analysis_plan.get_metadata("missing_key", "default")
        assert value == "default"

        # Get when metadata is None
        analysis_plan.plan_metadata = None
        value = analysis_plan.get_metadata("key", "default")
        assert value == "default"

    def test_update_status_based_on_changes_no_changes(self, analysis_plan):
        """Test update_status_based_on_changes with no changes."""
        with patch.object(analysis_plan, "get_change_count", return_value=0):
            original_status = analysis_plan.status
            analysis_plan.update_status_based_on_changes()
            assert analysis_plan.status == original_status

    def test_update_status_draft_to_reviewing(self, analysis_plan):
        """Test status update from DRAFT to REVIEWING."""
        analysis_plan.status = PlanStatus.DRAFT

        with (
            patch.object(analysis_plan, "get_change_count", return_value=5),
            patch.object(analysis_plan, "get_accepted_change_count", return_value=2),
            patch.object(analysis_plan, "get_rejected_change_count", return_value=1),
            patch.object(analysis_plan, "get_applied_change_count", return_value=0),
            patch.object(analysis_plan, "get_pending_change_count", return_value=2),
        ):

            analysis_plan.update_status_based_on_changes()
            assert analysis_plan.status == PlanStatus.REVIEWING

    def test_update_status_to_applied(self, analysis_plan):
        """Test status update to APPLIED."""
        analysis_plan.status = PlanStatus.REVIEWING
        analysis_plan.applied_at = None

        with (
            patch.object(analysis_plan, "get_change_count", return_value=5),
            patch.object(analysis_plan, "get_accepted_change_count", return_value=3),
            patch.object(analysis_plan, "get_rejected_change_count", return_value=2),
            patch.object(analysis_plan, "get_applied_change_count", return_value=3),
            patch.object(analysis_plan, "get_pending_change_count", return_value=0),
        ):

            analysis_plan.update_status_based_on_changes()
            assert analysis_plan.status == PlanStatus.APPLIED
            assert analysis_plan.applied_at is not None

    def test_update_status_not_all_accepted_applied(self, analysis_plan):
        """Test status doesn't change to APPLIED if not all accepted changes are applied."""
        analysis_plan.status = PlanStatus.REVIEWING

        with (
            patch.object(analysis_plan, "get_change_count", return_value=5),
            patch.object(analysis_plan, "get_accepted_change_count", return_value=3),
            patch.object(analysis_plan, "get_rejected_change_count", return_value=2),
            patch.object(analysis_plan, "get_applied_change_count", return_value=2),
            patch.object(analysis_plan, "get_pending_change_count", return_value=0),
        ):

            analysis_plan.update_status_based_on_changes()
            assert analysis_plan.status == PlanStatus.REVIEWING

    def test_can_be_applied(self, analysis_plan):
        """Test can_be_applied for different statuses."""
        analysis_plan.status = PlanStatus.DRAFT
        assert analysis_plan.can_be_applied() is True

        analysis_plan.status = PlanStatus.REVIEWING
        assert analysis_plan.can_be_applied() is True

        analysis_plan.status = PlanStatus.APPLIED
        assert analysis_plan.can_be_applied() is False

        analysis_plan.status = PlanStatus.CANCELLED
        assert analysis_plan.can_be_applied() is False

    def test_can_be_modified(self, analysis_plan):
        """Test can_be_modified for different statuses."""
        analysis_plan.status = PlanStatus.DRAFT
        assert analysis_plan.can_be_modified() is True

        analysis_plan.status = PlanStatus.REVIEWING
        assert analysis_plan.can_be_modified() is False

        analysis_plan.status = PlanStatus.APPLIED
        assert analysis_plan.can_be_modified() is False

        analysis_plan.status = PlanStatus.CANCELLED
        assert analysis_plan.can_be_modified() is False

    def test_to_dict_with_stats(self, analysis_plan):
        """Test to_dict with statistics included."""
        with (
            patch.object(analysis_plan, "get_change_count", return_value=10),
            patch.object(analysis_plan, "get_applied_change_count", return_value=5),
            patch.object(analysis_plan, "get_pending_change_count", return_value=3),
        ):

            result = analysis_plan.to_dict(include_stats=True)

            assert result["name"] == "Test Plan"
            assert result["description"] == "Test description"
            assert result["status"] == PlanStatus.DRAFT
            assert result["total_changes"] == 10
            assert result["applied_changes"] == 5
            assert result["pending_changes"] == 3

    def test_to_dict_without_stats(self, analysis_plan):
        """Test to_dict without statistics."""
        result = analysis_plan.to_dict(include_stats=False)

        assert result["name"] == "Test Plan"
        assert result["description"] == "Test description"
        assert result["status"] == PlanStatus.DRAFT
        assert "total_changes" not in result
        assert "applied_changes" not in result
        assert "pending_changes" not in result

    def test_to_dict_with_exclude(self, analysis_plan):
        """Test to_dict with exclude parameter."""
        # Don't include stats to avoid lazy loading issues
        result = analysis_plan.to_dict(
            exclude={"description", "plan_metadata"}, include_stats=False
        )

        assert result["name"] == "Test Plan"
        assert "description" not in result
        assert "plan_metadata" not in result

    def test_relationships(self):
        """Test relationship configuration."""
        # This tests that the relationship is properly configured
        plan = AnalysisPlan(name="Test")
        assert hasattr(plan, "changes")
        # The actual relationship behavior is tested via mocks above

    def test_table_indexes(self):
        """Test that proper indexes are defined."""
        # Check that the table args define the expected indexes
        table_args = AnalysisPlan.__table_args__
        assert len(table_args) == 2

        # Check index names
        index_names = [idx.name for idx in table_args]
        assert "idx_plan_status_created" in index_names
        assert "idx_plan_status_applied" in index_names


class TestAnalysisPlanEdgeCases:
    """Test edge cases and error scenarios."""

    def test_update_status_with_zero_applied(self, analysis_plan):
        """Test status update when no changes are applied."""
        analysis_plan.status = PlanStatus.REVIEWING

        with (
            patch.object(analysis_plan, "get_change_count", return_value=5),
            patch.object(analysis_plan, "get_accepted_change_count", return_value=0),
            patch.object(analysis_plan, "get_rejected_change_count", return_value=5),
            patch.object(analysis_plan, "get_applied_change_count", return_value=0),
            patch.object(analysis_plan, "get_pending_change_count", return_value=0),
        ):

            analysis_plan.update_status_based_on_changes()
            # Should not change to APPLIED since no changes were applied
            assert analysis_plan.status == PlanStatus.REVIEWING

    def test_applied_at_not_updated_if_already_set(self, analysis_plan):
        """Test applied_at is not updated if already set."""
        original_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        analysis_plan.status = PlanStatus.REVIEWING
        analysis_plan.applied_at = original_time

        with (
            patch.object(analysis_plan, "get_change_count", return_value=5),
            patch.object(analysis_plan, "get_accepted_change_count", return_value=3),
            patch.object(analysis_plan, "get_rejected_change_count", return_value=2),
            patch.object(analysis_plan, "get_applied_change_count", return_value=3),
            patch.object(analysis_plan, "get_pending_change_count", return_value=0),
        ):

            analysis_plan.update_status_based_on_changes()
            assert analysis_plan.status == PlanStatus.APPLIED
            assert analysis_plan.applied_at == original_time

    def test_metadata_operations_with_complex_values(self, analysis_plan):
        """Test metadata operations with complex data types."""
        # Add nested dict
        analysis_plan.add_metadata("nested", {"level1": {"level2": "value"}})
        assert analysis_plan.get_metadata("nested")["level1"]["level2"] == "value"

        # Add list
        analysis_plan.add_metadata("list", [1, 2, 3])
        assert analysis_plan.get_metadata("list") == [1, 2, 3]

        # Update existing key
        analysis_plan.add_metadata("test_key", "updated_value")
        assert analysis_plan.get_metadata("test_key") == "updated_value"
