"""
Tests for tag detection module.

This module tests the tag detection functionality including AI-based detection,
technical tag detection, redundancy filtering, and related tag suggestions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.analysis.ai_client import AIClient
from app.services.analysis.models import (
    DetectionResult,
    TagSuggestion,
    TagSuggestionsResponse,
)
from app.services.analysis.tag_detector import TagDetector


class TestTagDetectorInit:
    """Test cases for TagDetector initialization."""

    def test_init_empty_cache(self):
        """Test that cache is initialized empty."""
        detector = TagDetector()

        assert detector._tag_cache == {}

    def test_reverse_hierarchy_built(self):
        """Test that reverse hierarchy is built correctly."""
        detector = TagDetector()

        # Check some reverse mappings
        assert detector.parent_tags.get("raw") == "bareback"
        assert detector.parent_tags.get("3way") == "threesome"
        assert detector.parent_tags.get("muscular") == "muscle"
        assert detector.parent_tags.get("breeding") == "creampie"

    def test_constants_defined(self):
        """Test that class constants are properly defined."""
        assert hasattr(TagDetector, "TAG_HIERARCHY")
        assert hasattr(TagDetector, "RESOLUTION_TAGS")
        assert hasattr(TagDetector, "DURATION_TAGS")

        # Check structure
        assert isinstance(TagDetector.TAG_HIERARCHY, dict)
        assert isinstance(TagDetector.RESOLUTION_TAGS, dict)
        assert isinstance(TagDetector.DURATION_TAGS, dict)


class TestTechnicalTagDetection:
    """Test cases for technical tag detection based on video properties."""

    def test_detect_resolution_tags_4k(self):
        """Test detection of 4K resolution tags."""
        detector = TagDetector()

        scene_data = {
            "width": 3840,
            "height": 2160,
        }
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        assert len(results) > 0
        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["4K", "UHD", "2160p"])
        assert all(
            r.confidence == 0.95 for r in results if r.metadata["type"] == "resolution"
        )
        assert all(r.source == "technical" for r in results)

    def test_detect_resolution_tags_1080p(self):
        """Test detection of 1080p resolution tags."""
        detector = TagDetector()

        scene_data = {
            "width": 1920,
            "height": 1080,
        }
        existing_tags = ["amateur"]

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["1080p", "Full HD", "FHD"])

    def test_detect_resolution_tags_existing(self):
        """Test that existing resolution tags are not re-suggested."""
        detector = TagDetector()

        scene_data = {
            "width": 3840,
            "height": 2160,
        }
        existing_tags = ["4K", "amateur"]

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        assert "4K" not in tag_values
        # Other resolution tags for 4K might still be suggested
        assert any(tag in tag_values for tag in ["UHD", "2160p"])

    def test_detect_duration_tags_short(self):
        """Test detection of short duration tags."""
        detector = TagDetector()

        scene_data = {
            "duration": 180,  # 3 minutes
        }
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["short", "quickie"])
        duration_results = [r for r in results if r.metadata.get("type") == "duration"]
        assert all(r.confidence == 0.9 for r in duration_results)

    def test_detect_duration_tags_long(self):
        """Test detection of long duration tags."""
        detector = TagDetector()

        scene_data = {
            "duration": 2700,  # 45 minutes
        }
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["long", "full scene"])

    def test_detect_framerate_tags(self):
        """Test detection of framerate tags."""
        detector = TagDetector()

        scene_data = {
            "frame_rate": 60,
        }
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        assert "60fps" in tag_values
        fps_result = next(r for r in results if r.value == "60fps")
        assert fps_result.confidence == 0.95
        assert fps_result.metadata["type"] == "framerate"
        assert fps_result.metadata["fps"] == 60

    def test_detect_no_technical_tags(self):
        """Test scene with no technical properties."""
        detector = TagDetector()

        scene_data = {"title": "Test"}  # No technical data
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        # When no duration is provided, it defaults to 0 which matches "short" duration
        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["short", "quickie"])

    def test_detect_combined_technical_tags(self):
        """Test detection of multiple technical tags."""
        detector = TagDetector()

        scene_data = {
            "width": 1920,
            "height": 1080,
            "duration": 1200,  # 20 minutes
            "frame_rate": 60,
        }
        existing_tags = []

        results = detector.detect_technical_tags(scene_data, existing_tags)

        tag_values = [r.value for r in results]
        # Should have resolution, duration, and framerate tags
        assert any(tag in tag_values for tag in ["1080p", "Full HD", "FHD"])
        assert "standard length" in tag_values
        assert "60fps" in tag_values
        assert len(results) >= 3


class TestRedundancyFiltering:
    """Test cases for redundant tag filtering."""

    def test_filter_redundant_basic(self):
        """Test basic redundancy filtering."""
        detector = TagDetector()

        proposed = ["raw", "amateur"]  # raw is child of bareback
        existing = ["bareback"]  # parent already exists

        filtered = detector.filter_redundant_tags(proposed, existing)

        # "raw" is child of "bareback", so should be filtered
        assert "raw" not in filtered
        assert "amateur" in filtered

    def test_filter_already_existing(self):
        """Test filtering of already existing tags."""
        detector = TagDetector()

        proposed = ["bareback", "Amateur", "muscle"]  # Note case difference
        existing = ["amateur", "muscle"]

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert "bareback" in filtered
        assert "Amateur" not in filtered  # Case-insensitive match
        assert "muscle" not in filtered

    def test_filter_parent_when_child_exists(self):
        """Test that parent tags are filtered when child exists."""
        detector = TagDetector()

        proposed = ["group", "threesome"]
        existing = ["orgy"]  # Child of "group"

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert "group" not in filtered  # Parent filtered because child exists
        assert "threesome" in filtered

    def test_filter_child_when_parent_exists(self):
        """Test that child tags are filtered when parent exists."""
        detector = TagDetector()

        proposed = ["raw", "no condom", "amateur"]
        existing = ["bareback"]  # Parent of "raw" and "no condom"

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert "raw" not in filtered
        assert "no condom" not in filtered
        assert "amateur" in filtered

    def test_filter_complex_hierarchy(self):
        """Test filtering with complex tag hierarchies."""
        detector = TagDetector()

        proposed = ["hung", "large cock", "dad"]
        existing = ["big dick", "daddy"]  # Parents exist

        filtered = detector.filter_redundant_tags(proposed, existing)

        # Children of existing parents should be filtered
        assert "hung" not in filtered  # Child of "big dick"
        assert "large cock" not in filtered  # Child of "big dick"
        assert "dad" not in filtered  # Child of "daddy"

    def test_filter_redundant_results(self):
        """Test filtering of DetectionResult objects."""
        detector = TagDetector()

        results = [
            DetectionResult(value="raw", confidence=0.8, source="ai"),
            DetectionResult(value="amateur", confidence=0.7, source="ai"),
        ]
        existing = ["bareback"]  # Parent of "raw"

        filtered_results = detector._filter_redundant_results(results, existing)

        values = [r.value for r in filtered_results]
        assert "raw" not in values  # Filtered because parent exists
        assert "amateur" in values
        assert len(filtered_results) == 1


class TestAITagDetection:
    """Test cases for AI-based tag detection."""

    @pytest.mark.asyncio
    async def test_detect_with_ai_success(self):
        """Test successful AI tag detection."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        # Mock AI response
        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="bareback", confidence=0.9),
                TagSuggestion(name="muscle", confidence=0.8),
                TagSuggestion(name="amateur", confidence=0.7),
            ]
        )
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        scene_data = {"title": "Test Scene"}
        existing_tags = ["daddy"]
        available_tags = ["bareback", "muscle", "amateur", "twink"]

        results = await detector.detect_with_ai(
            scene_data, ai_client, existing_tags, available_tags
        )

        assert len(results) == 3
        assert all(isinstance(r, DetectionResult) for r in results)
        assert results[0].value == "bareback"
        assert results[0].confidence == 0.9
        assert results[0].source == "ai"
        assert results[0].metadata["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_detect_with_ai_filters_existing(self):
        """Test that AI detection filters out existing tags."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="bareback", confidence=0.9),
                TagSuggestion(name="Muscle", confidence=0.8),  # Different case
            ]
        )
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        scene_data = {"title": "Test Scene"}
        existing_tags = ["muscle", "daddy"]  # muscle already exists
        available_tags = ["bareback", "muscle"]

        results = await detector.detect_with_ai(
            scene_data, ai_client, existing_tags, available_tags
        )

        values = [r.value for r in results]
        assert "bareback" in values
        assert "Muscle" not in values  # Filtered due to case-insensitive match

    @pytest.mark.asyncio
    async def test_detect_with_ai_error_handling(self):
        """Test AI detection error handling."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.analyze_scene = AsyncMock(side_effect=Exception("API Error"))

        scene_data = {"title": "Test Scene"}
        existing_tags = []
        available_tags = []

        results = await detector.detect_with_ai(
            scene_data, ai_client, existing_tags, available_tags
        )

        assert results == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_detect_with_ai_tracked(self):
        """Test AI detection with cost tracking."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="bareback", confidence=0.9),
            ]
        )
        cost_info = {"total_cost": 0.05, "input_tokens": 100, "output_tokens": 50}
        ai_client.analyze_scene_with_cost = AsyncMock(
            return_value=(mock_response, cost_info)
        )

        scene_data = {"title": "Test Scene"}
        existing_tags = []
        available_tags = ["bareback"]

        results, returned_cost = await detector.detect_with_ai_tracked(
            scene_data, ai_client, existing_tags, available_tags
        )

        assert len(results) == 1
        assert results[0].value == "bareback"
        assert returned_cost == cost_info

    @pytest.mark.asyncio
    async def test_detect_with_ai_unexpected_response(self):
        """Test handling of unexpected response types."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)

        # Return wrong type
        ai_client.analyze_scene = AsyncMock(return_value={"wrong": "type"})

        scene_data = {"title": "Test Scene"}
        existing_tags = []
        available_tags = []

        results = await detector.detect_with_ai(
            scene_data, ai_client, existing_tags, available_tags
        )

        assert results == []


class TestRelatedTagSuggestions:
    """Test cases for related tag suggestions."""

    def test_suggest_related_basic(self):
        """Test basic related tag suggestions."""
        detector = TagDetector()

        current_tags = ["bareback"]
        all_available = ["creampie", "breeding", "raw", "amateur", "muscle"]

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        values = [s.value for s in suggestions]
        assert "creampie" in values
        assert "breeding" in values
        assert "raw" in values
        assert all(s.confidence == 0.6 for s in suggestions)
        assert all(s.source == "related" for s in suggestions)

    def test_suggest_related_no_duplicates(self):
        """Test that existing tags aren't suggested as related."""
        detector = TagDetector()

        current_tags = ["bareback", "creampie"]
        all_available = ["creampie", "breeding", "raw"]

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        values = [s.value for s in suggestions]
        assert "creampie" not in values  # Already in current tags
        assert "breeding" in values
        assert "raw" in values

    def test_suggest_related_multiple_base_tags(self):
        """Test suggestions based on multiple tags."""
        detector = TagDetector()

        current_tags = ["daddy", "muscle"]
        all_available = ["mature", "older younger", "gym", "jock", "athletic"]

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        values = [s.value for s in suggestions]
        # Should get suggestions for both daddy and muscle
        assert any(tag in values for tag in ["mature", "older younger"])
        assert any(tag in values for tag in ["gym", "jock", "athletic"])

    def test_suggest_related_unavailable_tags(self):
        """Test that unavailable tags aren't suggested."""
        detector = TagDetector()

        current_tags = ["outdoor"]
        all_available = ["public"]  # "nature" and "cruising" not available

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        values = [s.value for s in suggestions]
        assert "public" in values
        assert "nature" not in values  # Not in available tags
        assert "cruising" not in values  # Not in available tags

    def test_suggest_related_metadata(self):
        """Test that metadata includes base tag information."""
        detector = TagDetector()

        current_tags = ["fetish"]
        all_available = ["leather", "rubber", "gear"]

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        for suggestion in suggestions:
            assert suggestion.metadata["based_on"] == "fetish"

    def test_suggest_related_case_insensitive(self):
        """Test case-insensitive matching for related tags."""
        detector = TagDetector()

        current_tags = ["Amateur"]  # Capitalized
        all_available = ["homemade", "real", "authentic"]

        suggestions = detector.suggest_related_tags(current_tags, all_available)

        assert len(suggestions) > 0
        values = [s.value for s in suggestions]
        assert "homemade" in values


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_scene_data(self):
        """Test handling of empty scene data."""
        detector = TagDetector()

        results = detector.detect_technical_tags({}, [])

        # Empty dict means duration=0 which matches short duration
        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["short", "quickie"])

    def test_none_values_in_scene_data(self):
        """Test handling of None values."""
        detector = TagDetector()

        scene_data = {
            "width": None,
            "height": None,
            "duration": None,
            "frame_rate": None,
        }

        results = detector.detect_technical_tags(scene_data, [])

        # None values get converted to 0 with the `or 0` pattern
        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["short", "quickie"])

    def test_negative_values(self):
        """Test handling of negative values."""
        detector = TagDetector()

        scene_data = {
            "width": -1920,
            "height": -1080,
            "duration": -100,
            "frame_rate": -30,
        }

        results = detector.detect_technical_tags(scene_data, [])

        # Should not match any technical criteria
        assert len(results) == 0

    def test_extremely_high_resolution(self):
        """Test handling of resolutions higher than defined."""
        detector = TagDetector()

        scene_data = {
            "width": 7680,  # 8K
            "height": 4320,
        }

        results = detector.detect_technical_tags(scene_data, [])

        # Should match highest defined resolution (4K)
        tag_values = [r.value for r in results]
        assert any(tag in tag_values for tag in ["4K", "UHD", "2160p"])

    def test_whitespace_in_tags(self):
        """Test handling of tags with extra whitespace."""
        detector = TagDetector()

        proposed = ["  bareback  ", "amateur\n", "\tmuscle"]
        existing = []

        # The filter_redundant_tags method doesn't strip whitespace
        # so these would be treated as different tags
        filtered = detector.filter_redundant_tags(proposed, existing)

        assert len(filtered) == 3  # All kept because of whitespace differences

    @pytest.mark.asyncio
    async def test_detect_with_ai_empty_tags(self):
        """Test AI detection with empty tag list in response."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)

        mock_response = TagSuggestionsResponse(tags=[])
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        results = await detector.detect_with_ai({}, ai_client, [], [])

        assert results == []

    def test_unicode_tags(self):
        """Test handling of unicode in tags."""
        detector = TagDetector()

        proposed = ["日本人", "café", "naïve"]
        existing = []

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert len(filtered) == 3
        assert all(tag in filtered for tag in proposed)


class TestConfidenceScoring:
    """Test cases for tag confidence scoring and thresholds."""

    def test_technical_tag_confidence_scores(self):
        """Test that technical tags have appropriate confidence scores."""
        detector = TagDetector()

        scene_data = {
            "width": 3840,
            "height": 2160,
            "duration": 600,
            "frame_rate": 60,
        }

        results = detector.detect_technical_tags(scene_data, [])

        # Check confidence scores by type
        for result in results:
            if result.metadata["type"] == "resolution":
                assert result.confidence == 0.95  # High confidence for resolution
            elif result.metadata["type"] == "duration":
                assert result.confidence == 0.9  # Slightly lower for duration
            elif result.metadata["type"] == "framerate":
                assert result.confidence == 0.95  # High confidence for framerate

    @pytest.mark.asyncio
    async def test_ai_tag_confidence_variation(self):
        """Test that AI-suggested tags can have varying confidence scores."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="bareback", confidence=0.95),  # High confidence
                TagSuggestion(name="amateur", confidence=0.7),  # Medium confidence
                TagSuggestion(name="outdoor", confidence=0.4),  # Low confidence
            ]
        )
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        results = await detector.detect_with_ai(
            {"title": "Test"}, ai_client, [], ["bareback", "amateur", "outdoor"]
        )

        # Check that confidence scores are preserved
        assert len(results) == 3
        assert results[0].confidence == 0.95
        assert results[1].confidence == 0.7
        assert results[2].confidence == 0.4

    def test_related_tag_confidence_score(self):
        """Test that related tags have consistent confidence scores."""
        detector = TagDetector()

        current_tags = ["bareback", "daddy"]
        available = ["creampie", "breeding", "mature", "older younger"]

        suggestions = detector.suggest_related_tags(current_tags, available)

        # All related tags should have 0.6 confidence
        assert all(s.confidence == 0.6 for s in suggestions)
        assert len(suggestions) > 0

    def test_confidence_metadata_preservation(self):
        """Test that confidence scores are preserved with metadata."""
        detector = TagDetector()

        scene_data = {
            "width": 1920,
            "height": 1080,
            "duration": 1200,
        }

        results = detector.detect_technical_tags(scene_data, [])

        # Check each result has both confidence and metadata
        for result in results:
            assert hasattr(result, "confidence")
            assert hasattr(result, "metadata")
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_based_filtering(self):
        """Test filtering tags based on confidence threshold."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="high_conf", confidence=0.9),
                TagSuggestion(name="medium_conf", confidence=0.6),
                TagSuggestion(name="low_conf", confidence=0.3),
            ]
        )
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        results = await detector.detect_with_ai(
            {}, ai_client, [], ["high_conf", "medium_conf", "low_conf"]
        )

        # All results should be returned (no built-in filtering by confidence)
        assert len(results) == 3

        # But caller can filter by confidence
        high_confidence = [r for r in results if r.confidence >= 0.7]
        assert len(high_confidence) == 1
        assert high_confidence[0].value == "high_conf"


class TestAdvancedFiltering:
    """Test cases for advanced filtering scenarios."""

    def test_filter_multiple_hierarchy_levels(self):
        """Test filtering with multiple levels of tag hierarchy."""
        detector = TagDetector()

        # If we have "group", we shouldn't add "orgy" or "gangbang"
        proposed = ["orgy", "gangbang", "threesome"]
        existing = ["group"]

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert "orgy" not in filtered  # Child of "group"
        assert "gangbang" not in filtered  # Child of "group"
        assert "threesome" in filtered  # Not a child of "group"

    def test_filter_preserves_order(self):
        """Test that filtering preserves the original order of tags."""
        detector = TagDetector()

        proposed = ["amateur", "bareback", "daddy", "muscle"]
        existing = []

        filtered = detector.filter_redundant_tags(proposed, existing)

        # All should be kept and in original order
        assert filtered == proposed

    def test_case_insensitive_filtering(self):
        """Test case-insensitive filtering of redundant tags."""
        detector = TagDetector()

        proposed = ["RAW", "No Condom", "BREEDING"]
        existing = ["Bareback", "creampie"]  # Mixed case

        filtered = detector.filter_redundant_tags(proposed, existing)

        # RAW and "No Condom" are children of bareback
        assert "RAW" not in filtered
        assert "No Condom" not in filtered
        # BREEDING is child of creampie
        assert "BREEDING" not in filtered

    def test_filter_with_partial_matches(self):
        """Test that partial string matches don't cause false filtering."""
        detector = TagDetector()

        proposed = ["outdoor", "door", "out"]
        existing = []

        filtered = detector.filter_redundant_tags(proposed, existing)

        # All should be kept - no hierarchical relationship
        assert len(filtered) == 3
        assert all(tag in filtered for tag in proposed)

    def test_combined_source_filtering(self):
        """Test filtering when tags come from multiple sources."""
        detector = TagDetector()

        # Technical tags
        tech_results = detector.detect_technical_tags(
            {"width": 1920, "height": 1080, "duration": 600}, []
        )

        # Mock AI tags
        ai_results = [
            DetectionResult(value="1080p", confidence=0.8, source="ai"),  # Duplicate
            DetectionResult(value="amateur", confidence=0.7, source="ai"),
        ]

        # Filter combined results
        all_tags = [r.value for r in tech_results + ai_results]
        existing = []
        filtered_tags = detector.filter_redundant_tags(all_tags, existing)

        # filter_redundant_tags doesn't remove exact duplicates, it only filters hierarchical relationships
        # So we need to check that all unique tags are preserved
        assert (
            "1080p" in filtered_tags
            or "Full HD" in filtered_tags
            or "FHD" in filtered_tags
        )
        assert "amateur" in filtered_tags

    def test_filter_empty_lists(self):
        """Test filtering with empty lists."""
        detector = TagDetector()

        # Empty proposed
        assert detector.filter_redundant_tags([], ["existing"]) == []

        # Empty existing
        proposed = ["tag1", "tag2"]
        assert detector.filter_redundant_tags(proposed, []) == proposed

        # Both empty
        assert detector.filter_redundant_tags([], []) == []

    def test_filter_with_whitespace_preservation(self):
        """Test that tags with different whitespace are treated as different."""
        detector = TagDetector()

        proposed = ["big dick", "big  dick", "big\tdick"]
        existing = []

        filtered = detector.filter_redundant_tags(proposed, existing)

        # Different whitespace means different tags
        assert len(filtered) == 3

    def test_hierarchy_with_multiple_parents(self):
        """Test tags that could belong to multiple hierarchies."""
        detector = TagDetector()

        # "raw" is child of "bareback"
        # Let's test a scenario with clear parent-child relationships
        proposed = ["breeding"]  # Child of "creampie"
        existing = ["creampie", "bareback"]

        filtered = detector.filter_redundant_tags(proposed, existing)

        assert "breeding" not in filtered  # Filtered because parent exists


class TestScenarioBasedFiltering:
    """Test real-world scenarios for tag detection and filtering."""

    @pytest.mark.asyncio
    async def test_complete_scene_analysis_workflow(self):
        """Test a complete workflow of detecting and filtering tags."""
        detector = TagDetector()
        ai_client = MagicMock(spec=AIClient)
        ai_client.model = "gpt-4"

        # Scene with technical properties
        scene_data = {
            "title": "Amateur Scene",
            "width": 1920,
            "height": 1080,
            "duration": 1200,
            "frame_rate": 30,
        }

        # Existing tags
        existing_tags = ["amateur", "bareback"]
        available_tags = ["muscle", "daddy", "twink", "outdoor", "1080p"]

        # Get technical tags first
        tech_results = detector.detect_technical_tags(scene_data, existing_tags)

        # Mock AI suggestions
        mock_response = TagSuggestionsResponse(
            tags=[
                TagSuggestion(name="muscle", confidence=0.8),
                TagSuggestion(
                    name="raw", confidence=0.7
                ),  # Should be filtered (child of bareback)
                TagSuggestion(name="outdoor", confidence=0.6),
            ]
        )
        ai_client.analyze_scene = AsyncMock(return_value=mock_response)

        ai_results = await detector.detect_with_ai(
            scene_data, ai_client, existing_tags, available_tags
        )

        # Combine all results
        all_results = tech_results + ai_results

        # Check that redundant tags are filtered
        tag_values = [r.value for r in all_results]
        assert "1080p" in tag_values or "Full HD" in tag_values or "FHD" in tag_values
        assert "standard length" in tag_values
        assert "muscle" in tag_values
        assert "outdoor" in tag_values
        assert "raw" not in tag_values  # Filtered because bareback exists

    def test_performance_with_large_tag_sets(self):
        """Test performance with large numbers of tags."""
        detector = TagDetector()

        # Create large tag sets
        proposed = [f"tag_{i}" for i in range(100)]
        proposed.extend(["bareback", "raw", "muscle", "muscular"])

        existing = [f"existing_{i}" for i in range(50)]
        existing.extend(
            ["daddy", "bareback", "muscle"]
        )  # Add parents to test child filtering

        # Should handle large sets efficiently
        filtered = detector.filter_redundant_tags(proposed, existing)

        # Check specific filtering
        assert "bareback" not in filtered  # Already exists
        assert "raw" not in filtered  # Child of bareback which exists
        assert "muscle" not in filtered  # Already exists
        assert "muscular" not in filtered  # Child of muscle which exists

        # Check that all unique generated tags are kept
        unique_generated = set(f"tag_{i}" for i in range(100))
        filtered_generated = set(tag for tag in filtered if tag.startswith("tag_"))
        assert filtered_generated == unique_generated
