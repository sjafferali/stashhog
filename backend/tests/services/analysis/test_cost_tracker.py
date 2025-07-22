"""Tests for the analysis cost tracker."""

from unittest.mock import patch

from app.services.analysis.cost_tracker import AnalysisCostTracker


class TestAnalysisCostTracker:
    """Test the AnalysisCostTracker class."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = AnalysisCostTracker()

        # Check initial values
        assert tracker.scenes_analyzed == 0
        assert tracker.model_used is None
        assert tracker.get_total_cost() == 0.0

        # Check operation costs are initialized
        assert "studio_detection" in tracker.operation_costs
        assert "performer_detection" in tracker.operation_costs
        assert "tag_detection" in tracker.operation_costs
        assert "details_generation" in tracker.operation_costs

        # Check all costs are zero
        for cost in tracker.operation_costs.values():
            assert cost == 0.0

        # Check token usage is initialized
        for operation in tracker.token_usage:
            assert tracker.token_usage[operation]["prompt"] == 0
            assert tracker.token_usage[operation]["completion"] == 0
            assert tracker.token_usage[operation]["total"] == 0

    def test_track_operation(self):
        """Test tracking a single operation."""
        tracker = AnalysisCostTracker()

        # Track an operation
        tracker.track_operation(
            operation="studio_detection",
            cost=0.0025,
            prompt_tokens=150,
            completion_tokens=50,
            model="gpt-4",
        )

        # Verify cost tracking
        assert tracker.operation_costs["studio_detection"] == 0.0025
        assert tracker.get_total_cost() == 0.0025

        # Verify token tracking
        assert tracker.token_usage["studio_detection"]["prompt"] == 150
        assert tracker.token_usage["studio_detection"]["completion"] == 50
        assert tracker.token_usage["studio_detection"]["total"] == 200

        # Verify model tracking
        assert tracker.model_used == "gpt-4"

    def test_track_multiple_operations(self):
        """Test tracking multiple operations."""
        tracker = AnalysisCostTracker()

        # Track multiple operations
        tracker.track_operation("studio_detection", 0.0025, 150, 50, "gpt-4")
        tracker.track_operation("performer_detection", 0.0030, 200, 60, "gpt-4")
        tracker.track_operation("tag_detection", 0.0040, 250, 80, "gpt-4")
        tracker.track_operation("details_generation", 0.0050, 300, 100, "gpt-4")

        # Verify individual costs
        assert tracker.operation_costs["studio_detection"] == 0.0025
        assert tracker.operation_costs["performer_detection"] == 0.0030
        assert tracker.operation_costs["tag_detection"] == 0.0040
        assert tracker.operation_costs["details_generation"] == 0.0050

        # Verify total cost (using approx for floating point comparison)
        assert abs(tracker.get_total_cost() - 0.0145) < 1e-10

    def test_track_same_operation_multiple_times(self):
        """Test tracking the same operation multiple times."""
        tracker = AnalysisCostTracker()

        # Track same operation multiple times
        tracker.track_operation("studio_detection", 0.0025, 150, 50)
        tracker.track_operation("studio_detection", 0.0030, 200, 60)
        tracker.track_operation("studio_detection", 0.0020, 100, 40)

        # Verify costs are accumulated
        assert tracker.operation_costs["studio_detection"] == 0.0075

        # Verify tokens are accumulated
        assert tracker.token_usage["studio_detection"]["prompt"] == 450
        assert tracker.token_usage["studio_detection"]["completion"] == 150
        assert tracker.token_usage["studio_detection"]["total"] == 600

    @patch("app.services.analysis.cost_tracker.logger")
    def test_track_unknown_operation(self, mock_logger):
        """Test tracking an unknown operation type."""
        tracker = AnalysisCostTracker()

        # Track unknown operation
        tracker.track_operation("unknown_operation", 0.001, 50, 20)

        # Should log warning
        mock_logger.warning.assert_called_once_with(
            "Unknown operation type: unknown_operation"
        )

        # Should not affect total cost
        assert tracker.get_total_cost() == 0.0

    def test_increment_scenes(self):
        """Test incrementing scene count."""
        tracker = AnalysisCostTracker()

        assert tracker.scenes_analyzed == 0

        tracker.increment_scenes()
        assert tracker.scenes_analyzed == 1

        tracker.increment_scenes()
        tracker.increment_scenes()
        assert tracker.scenes_analyzed == 3

    def test_get_total_tokens(self):
        """Test getting total token usage."""
        tracker = AnalysisCostTracker()

        # Track operations
        tracker.track_operation("studio_detection", 0.001, 150, 50)
        tracker.track_operation("performer_detection", 0.001, 200, 60)
        tracker.track_operation("tag_detection", 0.001, 250, 80)

        # Get total tokens
        total_tokens = tracker.get_total_tokens()

        assert total_tokens["prompt"] == 600
        assert total_tokens["completion"] == 190
        assert total_tokens["total"] == 790

    def test_get_average_cost_per_scene(self):
        """Test calculating average cost per scene."""
        tracker = AnalysisCostTracker()

        # No scenes analyzed
        assert tracker.get_average_cost_per_scene() == 0.0

        # Track operations and scenes
        tracker.track_operation("studio_detection", 0.0025, 150, 50)
        tracker.track_operation("performer_detection", 0.0030, 200, 60)
        tracker.track_operation("tag_detection", 0.0040, 250, 80)

        tracker.increment_scenes()
        tracker.increment_scenes()

        # Average should be total cost / scenes
        expected_average = 0.0095 / 2
        assert abs(tracker.get_average_cost_per_scene() - expected_average) < 1e-10

    def test_get_summary(self):
        """Test getting complete summary."""
        tracker = AnalysisCostTracker()

        # Track some operations
        tracker.track_operation("studio_detection", 0.0025, 150, 50, "gpt-4")
        tracker.track_operation("performer_detection", 0.0030, 200, 60)
        tracker.track_operation("tag_detection", 0.0040, 250, 80)

        tracker.increment_scenes()
        tracker.increment_scenes()

        # Get summary
        summary = tracker.get_summary()

        # Verify summary contents
        assert abs(summary["total_cost"] - 0.0095) < 1e-10
        assert summary["total_tokens"] == 790
        assert summary["prompt_tokens"] == 600
        assert summary["completion_tokens"] == 190
        assert summary["scenes_analyzed"] == 2
        assert abs(summary["average_cost_per_scene"] - 0.0095 / 2) < 1e-10
        assert summary["model"] == "gpt-4"

        # Verify cost breakdown
        assert summary["cost_breakdown"]["studio_detection"] == 0.0025
        assert summary["cost_breakdown"]["performer_detection"] == 0.0030
        assert summary["cost_breakdown"]["tag_detection"] == 0.0040
        assert summary["cost_breakdown"]["details_generation"] == 0.0

        # Verify token breakdown exists
        assert "token_breakdown" in summary

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = AnalysisCostTracker()

        # Add some data
        tracker.track_operation("studio_detection", 0.0025, 150, 50, "gpt-4")
        tracker.track_operation("performer_detection", 0.0030, 200, 60)
        tracker.increment_scenes()
        tracker.increment_scenes()

        # Verify data exists
        assert tracker.get_total_cost() > 0
        assert tracker.scenes_analyzed == 2
        assert tracker.model_used == "gpt-4"

        # Reset
        tracker.reset()

        # Verify everything is reset
        assert tracker.get_total_cost() == 0.0
        assert tracker.scenes_analyzed == 0
        assert tracker.model_used is None

        # Verify all operation costs are reset
        for cost in tracker.operation_costs.values():
            assert cost == 0.0

        # Verify all token usage is reset
        for operation in tracker.token_usage:
            assert tracker.token_usage[operation]["prompt"] == 0
            assert tracker.token_usage[operation]["completion"] == 0
            assert tracker.token_usage[operation]["total"] == 0

    def test_repr(self):
        """Test string representation."""
        tracker = AnalysisCostTracker()

        # Initial state
        repr_str = repr(tracker)
        assert "AnalysisCostTracker" in repr_str
        assert "total_cost=$0.0000" in repr_str
        assert "scenes=0" in repr_str
        assert "model=None" in repr_str

        # Add some data
        tracker.track_operation("studio_detection", 0.0025, 150, 50, "gpt-4")
        tracker.increment_scenes()

        # Updated state
        repr_str = repr(tracker)
        assert "total_cost=$0.0025" in repr_str
        assert "scenes=1" in repr_str
        assert "model=gpt-4" in repr_str

    def test_model_tracking(self):
        """Test model tracking behavior."""
        tracker = AnalysisCostTracker()

        # Track with model
        tracker.track_operation("studio_detection", 0.001, 50, 20, "gpt-4")
        assert tracker.model_used == "gpt-4"

        # Track without model - should keep existing
        tracker.track_operation("performer_detection", 0.001, 50, 20)
        assert tracker.model_used == "gpt-4"

        # Track with different model - should not overwrite
        tracker.track_operation("tag_detection", 0.001, 50, 20, "gpt-3.5-turbo")
        assert tracker.model_used == "gpt-4"  # First model is kept

    def test_empty_token_breakdown(self):
        """Test token breakdown when no operations tracked."""
        tracker = AnalysisCostTracker()

        total_tokens = tracker.get_total_tokens()
        assert total_tokens["prompt"] == 0
        assert total_tokens["completion"] == 0
        assert total_tokens["total"] == 0

    def test_cost_precision(self):
        """Test cost calculation precision."""
        tracker = AnalysisCostTracker()

        # Track operations with small costs
        tracker.track_operation("studio_detection", 0.00012345, 10, 5)
        tracker.track_operation("performer_detection", 0.00067890, 20, 10)

        # Verify precision is maintained
        total_cost = tracker.get_total_cost()
        assert abs(total_cost - 0.00080235) < 0.0000001
