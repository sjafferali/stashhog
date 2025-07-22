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

    def test_deduplicate_markers(self, detector):
        """Test deduplication of markers."""
        markers = [
            {"time": 10.0, "title": "action_AI", "confidence": 0.7},
            {
                "time": 10.5,
                "title": "action_AI",
                "confidence": 0.8,
            },  # Duplicate, higher confidence
            {"time": 20.0, "title": "other_AI", "confidence": 0.9},
            {"time": 30.0, "end_time": 35.0, "title": "span_AI", "confidence": 0.7},
            {
                "time": 32.0,
                "end_time": 37.0,
                "title": "span_AI",
                "confidence": 0.8,
            },  # Overlapping
        ]

        deduplicated = detector._deduplicate_markers(markers)

        # Expected: 3 markers (keeping higher confidence ones)
        assert len(deduplicated) == 3

        # Should keep the higher confidence "action_AI" at 10.5
        action_markers = [m for m in deduplicated if m["title"] == "action_AI"]
        assert len(action_markers) == 1
        assert action_markers[0]["time"] == 10.5
        assert action_markers[0]["confidence"] == 0.8

        # Should keep "other_AI"
        other_markers = [m for m in deduplicated if m["title"] == "other_AI"]
        assert len(other_markers) == 1

        # Should keep the higher confidence overlapping span
        span_markers = [m for m in deduplicated if m["title"] == "span_AI"]
        assert len(span_markers) == 1
        assert span_markers[0]["confidence"] == 0.8

    def test_convert_timespans_to_tags(self, detector):
        """Test conversion of timespans to tags with aggregation."""
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

        # Should have 2 unique tags (action1_AI with highest confidence, action2_AI)
        assert len(tags) == 2

        # Find tags by name
        tag_dict = {tag["name"]: tag for tag in tags}

        # action1_AI should have confidence 0.9 (from category2)
        assert "action1_AI" in tag_dict
        assert tag_dict["action1_AI"]["confidence"] == 0.9
        assert tag_dict["action1_AI"]["category"] == "category2"

        # action2_AI should have confidence 0.6
        assert "action2_AI" in tag_dict
        assert tag_dict["action2_AI"]["confidence"] == 0.6

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
        """Test extraction of tags from result with deduplication."""
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

        # Should only add tag2_AI since tag1_AI already exists
        assert len(changes) == 1
        assert changes[0].field == "tags"
        assert changes[0].action == "add"
        assert changes[0].proposed_value == "tag2_AI"
        assert changes[0].confidence == 0.6

    @pytest.mark.asyncio
    async def test_extract_markers_from_result_with_deduplication(self, detector):
        """Test extraction of markers with deduplication."""
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
                        },  # Overlaps, higher confidence
                    ]
                }
            }
        }

        existing_markers = [
            {"seconds": 10.5, "title": "existing_marker"}  # Exists at similar time
        ]

        changes = detector._extract_markers_from_result(result, existing_markers)

        # The merged marker at 10-12 will be skipped because there's an existing marker at 10.5
        # Only the higher confidence marker at 20.5-21.5 will be added
        assert len(changes) == 1

        # Should only have the higher confidence overlapping marker
        marker_value = changes[0].proposed_value
        assert marker_value["seconds"] == 20.5
        assert marker_value["end_seconds"] == 21.5
        assert marker_value["title"] == "action1_AI"
        assert changes[0].confidence == 0.85
