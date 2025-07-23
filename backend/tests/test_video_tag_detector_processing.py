"""Test the video tag detector processing logic."""

from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.services.analysis.video_tag_detector import VideoTagDetector


class TestVideoTagDetectorProcessing:
    """Test the processing logic for video tag detection."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = Mock(spec=Settings)
        settings.analysis = Mock()
        settings.analysis.ai_video_server_url = "http://localhost:8080"
        settings.analysis.frame_interval = 1.0
        settings.analysis.ai_video_threshold = 0.3
        settings.analysis.server_timeout = 30
        settings.analysis.create_markers = True
        return settings

    @pytest.fixture
    def detector(self, settings):
        """Create video tag detector instance."""
        return VideoTagDetector(settings)

    def test_merge_consecutive_occurrences(self, detector):
        """Test merging of consecutive occurrences."""
        # Test data: frame-by-frame detections that should be merged
        occurrences = [
            {"start": 1.0, "end": 2.0, "confidence": 0.8},
            {"start": 2.0, "end": 3.0, "confidence": 0.8},  # Should merge
            {"start": 3.0, "end": 4.0, "confidence": 0.8},  # Should merge
            {
                "start": 5.0,
                "end": 6.0,
                "confidence": 0.8,
            },  # Gap of 1s, within frame_interval
            {"start": 6.0, "end": 7.0, "confidence": 0.9},  # Different confidence
            {"start": 7.0, "end": 8.0, "confidence": 0.9},  # Should merge with previous
        ]

        merged = detector._merge_consecutive_occurrences(occurrences)

        # The merging is based on frame_interval (1.0s) with 10% tolerance
        # So occurrences with gaps <= 1.1s and same confidence get merged
        assert len(merged) == 2

        # First span: frames 1-6 (all with 0.8 confidence)
        assert merged[0]["start"] == 1.0
        assert merged[0]["end"] == 6.0
        assert merged[0]["confidence"] == 0.8

        # Second span: frames 6-8 (0.9 confidence)
        assert merged[1]["start"] == 6.0
        assert merged[1]["end"] == 8.0
        assert merged[1]["confidence"] == 0.9

    def test_convert_timespans_to_tags(self, detector):
        """Test conversion of timespans to tags."""
        timespans = {
            "category1": {
                "action1": [
                    {"start": 1, "end": 2, "confidence": 0.7},
                    {"start": 2, "end": 3, "confidence": 0.7},  # Should merge
                    {"start": 10, "end": 11, "confidence": 0.8},
                ],
                "action2": [
                    {"start": 5, "end": 6, "confidence": 0.6},
                ],
            },
            "category2": {
                "action1": [  # Same action name, different category
                    {"start": 15, "end": 16, "confidence": 0.9},
                ]
            },
        }

        tags = detector._convert_timespans_to_tags(timespans)

        # Should have 3 tags (action1_AI from both categories, action2_AI)
        assert len(tags) == 3

        # Check tag names
        tag_names = [tag["name"] for tag in tags]
        assert tag_names.count("action1_AI") == 2
        assert tag_names.count("action2_AI") == 1

        # Get action1_AI tags
        action1_tags = [tag for tag in tags if tag["name"] == "action1_AI"]
        action1_confidences = sorted([tag["confidence"] for tag in action1_tags])
        # Should have average confidence from merged occurrences in category1 (0.75) and category2 (0.9)
        assert len(action1_confidences) == 2
        assert abs(action1_confidences[0] - 0.75) < 0.0001  # Average of 0.7, 0.7, 0.8
        assert action1_confidences[1] == 0.9

    def test_convert_timespans_to_markers_with_merging(self, detector):
        """Test conversion of timespans to markers with merging."""
        timespans = {
            "category1": {
                "action1": [
                    {"start": 1, "end": 2, "confidence": 0.8},
                    {"start": 2, "end": 3, "confidence": 0.8},  # Should merge
                    {"start": 3, "end": 4, "confidence": 0.8},  # Should merge
                    {"start": 10, "end": 11, "confidence": 0.75},
                ]
            }
        }

        markers = detector._convert_timespans_to_markers(timespans)

        # Should have 2 markers after merging (1-4 merged, 10-11 separate)
        assert len(markers) == 2

        # First marker should be the merged span
        assert markers[0]["time"] == 1
        assert markers[0]["end_time"] == 4
        assert markers[0]["title"] == "action1_AI"
        assert markers[0]["confidence"] == 0.8

        # Second marker
        assert markers[1]["time"] == 10
        assert markers[1]["end_time"] == 11
        assert markers[1]["confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_extract_tags_from_result(self, detector):
        """Test extraction of tags from result."""
        result = {
            "timespans": {
                "category1": {
                    "tag1": [
                        {"start": 1, "end": 2, "confidence": 0.8},
                        {"start": 2, "end": 3, "confidence": 0.8},
                    ],
                    "tag2": [
                        {"start": 5, "end": 6, "confidence": 0.6},
                    ],
                }
            }
        }

        existing_tags = ["existing_tag", "tag1_AI"]  # tag1_AI already exists

        changes = detector._extract_tags_from_result(result, existing_tags)

        # Should add both tags regardless of existing tags
        assert len(changes) == 2
        assert all(c.field == "tags" for c in changes)
        assert all(c.action == "add" for c in changes)
        proposed_values = [c.proposed_value for c in changes]
        assert "tag1_AI" in proposed_values
        assert "tag2_AI" in proposed_values

    @pytest.mark.asyncio
    async def test_extract_markers_from_result(self, detector):
        """Test extraction of markers."""
        result = {
            "timespans": {
                "category1": {
                    "action1": [
                        {"start": 10, "end": 11, "confidence": 0.8},
                        {"start": 11, "end": 12, "confidence": 0.8},  # Should merge
                        {"start": 20, "end": 21, "confidence": 0.75},
                        {
                            "start": 20.5,
                            "end": 21.5,
                            "confidence": 0.85,
                        },  # Overlaps
                    ]
                }
            }
        }

        existing_markers = [
            {"seconds": 10.5, "title": "existing_marker"}  # Exists at similar time
        ]

        changes = detector._extract_markers_from_result(result, existing_markers)

        # Should remove existing marker and add new ones
        # After merging consecutive occurrences: 10-12 (merged), 20-21, 20.5-21.5
        # Total: 1 remove + 3 add = 4 changes
        assert len(changes) == 4

        # Check that all changes are for markers
        assert all(c.field == "markers" for c in changes)

        # Check that we have 1 remove and 3 add operations
        remove_changes = [c for c in changes if c.action == "remove"]
        add_changes = [c for c in changes if c.action == "add"]
        assert len(remove_changes) == 1
        assert len(add_changes) == 3

        # Check that the remove operation is for the existing marker
        assert remove_changes[0].current_value == existing_markers[0]
