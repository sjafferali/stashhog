"""
Tests for studio detection module.

This module tests studio detection from paths, patterns, and AI analysis.
"""

import re
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.analysis.studio_detector import StudioDetector


class TestStudioDetectorInit:
    """Test cases for StudioDetector initialization."""

    def test_init_loads_patterns(self):
        """Test that initialization loads default patterns."""
        detector = StudioDetector()

        assert len(detector.patterns) > 0
        assert "Sean Cody" in detector.patterns
        assert "Men.com" in detector.patterns
        assert "OnlyFans" in detector.patterns
        assert isinstance(detector.patterns["Sean Cody"], re.Pattern)

    def test_init_empty_cache(self):
        """Test that cache is initialized empty."""
        detector = StudioDetector()

        assert detector._studio_cache == {}


class TestPatternDetection:
    """Test cases for pattern-based studio detection."""

    @pytest.mark.asyncio
    async def test_detect_from_path_filename_match(self):
        """Test detection from filename pattern match."""
        detector = StudioDetector()
        known_studios = ["Sean Cody", "Men.com"]

        # Test with Sean Cody pattern in filename
        result = await detector.detect_from_path(
            "/videos/SeanCody - Hot Scene.mp4", known_studios
        )

        assert result is not None
        assert result.value == "Sean Cody"
        assert result.confidence == 0.9  # High confidence for known studio
        assert result.source == "pattern"
        assert "pattern" in result.metadata

    @pytest.mark.asyncio
    async def test_detect_from_path_directory_match(self):
        """Test detection from directory pattern match."""
        detector = StudioDetector()
        known_studios = ["Men.com"]

        # Test with Men.com pattern in directory
        result = await detector.detect_from_path(
            "/videos/Men.com/scene123.mp4", known_studios
        )

        assert result is not None
        assert result.value == "Men.com"
        assert result.confidence == 0.85  # Slightly lower for directory match
        assert result.metadata["matched_in"] == "directory"

    @pytest.mark.asyncio
    async def test_detect_from_path_unknown_studio(self):
        """Test detection for studio not in known list."""
        detector = StudioDetector()
        known_studios = []  # Empty known studios

        result = await detector.detect_from_path(
            "/videos/BelAmi - Scene.mp4", known_studios
        )

        assert result is not None
        assert result.value == "Bel Ami"
        assert result.confidence == 0.8  # Lower confidence for unknown studio

    @pytest.mark.asyncio
    async def test_detect_from_path_exact_match(self):
        """Test detection from exact studio name in path."""
        detector = StudioDetector()
        known_studios = ["Exact Studio Name", "Hot House"]

        # Test exact match in directory - use a studio name that doesn't have a pattern
        result = await detector.detect_from_path(
            "/videos/Exact Studio Name/new_scene.mp4", known_studios
        )

        assert result is not None
        assert result.value == "Exact Studio Name"
        assert result.confidence == 0.95  # Highest confidence for exact directory
        assert result.source == "path"
        assert result.metadata["match_type"] == "exact"

    @pytest.mark.asyncio
    async def test_detect_from_path_no_match(self):
        """Test detection when no patterns match."""
        detector = StudioDetector()
        known_studios = ["Some Studio"]

        result = await detector.detect_from_path(
            "/videos/random/unknown_scene.mp4", known_studios
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_from_path_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        detector = StudioDetector()
        known_studios = ["Sean Cody"]

        # Test various case combinations
        test_paths = [
            "/videos/SEANCODY_scene.mp4",
            "/videos/sean_cody_scene.mp4",
            "/videos/Sean-Cody-Scene.mp4",
            "/videos/SeAnCoDy.mp4",
        ]

        for path in test_paths:
            result = await detector.detect_from_path(path, known_studios)
            assert result is not None
            assert result.value == "Sean Cody"

    @pytest.mark.asyncio
    async def test_detect_from_path_abbreviation_patterns(self):
        """Test detection of studio abbreviations."""
        detector = StudioDetector()
        known_studios = ["Corbin Fisher", "Raging Stallion"]

        # Test CF pattern for Corbin Fisher
        result = await detector.detect_from_path("/videos/CF1234.mp4", known_studios)
        assert result is not None
        assert result.value == "Corbin Fisher"

        # Test RS pattern for Raging Stallion
        result = await detector.detect_from_path("/videos/RS_999.mp4", known_studios)
        assert result is not None
        assert result.value == "Raging Stallion"

    @pytest.mark.asyncio
    async def test_detect_from_path_fansite_patterns(self):
        """Test detection of fan site patterns."""
        detector = StudioDetector()
        known_studios = ["OnlyFans", "JustForFans"]

        # Test OnlyFans variations
        result = await detector.detect_from_path(
            "/videos/OnlyFans/creator/video.mp4", known_studios
        )
        assert result is not None
        assert result.value == "OnlyFans"

        # Test JustForFans abbreviation
        result = await detector.detect_from_path(
            "/videos/JFF_content.mp4", known_studios
        )
        assert result is not None
        assert result.value == "JustForFans"


class TestAIDetection:
    """Test cases for AI-based studio detection."""

    @pytest.mark.asyncio
    async def test_detect_with_ai_success(self):
        """Test successful AI detection."""
        detector = StudioDetector()
        known_studios = ["Studio A", "Studio B"]

        # Mock AI client
        ai_client = Mock()
        ai_client.model = "gpt-4"
        ai_client.analyze_scene = AsyncMock(
            return_value={"studio": "Studio A", "confidence": 0.95}
        )

        scene_data = {
            "file_path": "/videos/scene.mp4",
            "title": "Hot Scene at Studio A",
        }

        result = await detector.detect_with_ai(scene_data, ai_client, known_studios)

        assert result is not None
        assert result.value == "Studio A"
        assert result.confidence == 0.95
        assert result.source == "ai"
        assert result.metadata["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_detect_with_ai_unknown_studio(self):
        """Test AI detection returning unknown."""
        detector = StudioDetector()
        known_studios = ["Studio A"]

        ai_client = Mock()
        ai_client.analyze_scene = AsyncMock(
            return_value={"studio": "Unknown", "confidence": 0.3}
        )

        scene_data = {"file_path": "/videos/scene.mp4"}

        result = await detector.detect_with_ai(scene_data, ai_client, known_studios)

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_with_ai_error_handling(self):
        """Test AI detection error handling."""
        detector = StudioDetector()
        known_studios = ["Studio A"]

        ai_client = Mock()
        ai_client.analyze_scene = AsyncMock(side_effect=Exception("API Error"))

        scene_data = {"file_path": "/videos/scene.mp4"}

        result = await detector.detect_with_ai(scene_data, ai_client, known_studios)

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_with_ai_tracked(self):
        """Test AI detection with cost tracking."""
        detector = StudioDetector()
        known_studios = ["Studio X"]

        ai_client = Mock()
        ai_client.model = "gpt-4"
        ai_client.analyze_scene_with_cost = AsyncMock(
            return_value=(
                {"studio": "Studio X", "confidence": 0.85},
                {"input_tokens": 100, "output_tokens": 20, "cost": 0.002},
            )
        )

        scene_data = {"file_path": "/videos/scene.mp4"}

        result, cost_info = await detector.detect_with_ai_tracked(
            scene_data, ai_client, known_studios
        )

        assert result is not None
        assert result.value == "Studio X"
        assert result.confidence == 0.85
        assert cost_info["cost"] == 0.002

    @pytest.mark.asyncio
    async def test_detect_with_ai_tracked_no_result(self):
        """Test AI detection with cost tracking returning no result."""
        detector = StudioDetector()
        known_studios = []

        ai_client = Mock()
        ai_client.analyze_scene_with_cost = AsyncMock(
            return_value=({"studio": "", "confidence": 0}, {"cost": 0.001})
        )

        scene_data = {"file_path": "/videos/scene.mp4"}

        result, cost_info = await detector.detect_with_ai_tracked(
            scene_data, ai_client, known_studios
        )

        assert result is None
        assert cost_info is None


class TestCombinedDetection:
    """Test cases for combined detection methods."""

    @pytest.mark.asyncio
    async def test_detect_pattern_high_confidence(self):
        """Test that high confidence pattern match is used without AI."""
        detector = StudioDetector()
        known_studios = ["Sean Cody"]

        ai_client = Mock()
        ai_client.analyze_scene = AsyncMock()  # Should not be called

        scene_data = {"file_path": "/videos/SeanCody_Hot.mp4"}

        result = await detector.detect(
            scene_data, known_studios, ai_client, use_ai=True
        )

        assert result is not None
        assert result.value == "Sean Cody"
        assert result.source == "pattern"
        # AI should not be called for high confidence pattern match
        ai_client.analyze_scene.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_pattern_low_confidence_uses_ai(self):
        """Test that low confidence pattern triggers AI detection."""
        detector = StudioDetector()
        known_studios = []  # Unknown studio gives low confidence

        ai_client = Mock()
        ai_client.model = "gpt-4"
        ai_client.analyze_scene = AsyncMock(
            return_value={"studio": "Sean Cody", "confidence": 0.95}
        )

        scene_data = {"file_path": "/videos/sc1234.mp4"}  # Matches pattern

        result = await detector.detect(
            scene_data, known_studios, ai_client, use_ai=True
        )

        assert result is not None
        assert result.value == "Sean Cody"
        assert result.source == "ai"  # AI result used due to higher confidence
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_detect_no_ai_client(self):
        """Test detection without AI client."""
        detector = StudioDetector()
        known_studios = ["Men.com"]

        scene_data = {"file_path": "/videos/Men - Scene.mp4"}

        result = await detector.detect(scene_data, known_studios, ai_client=None)

        assert result is not None
        assert result.source == "pattern"

    @pytest.mark.asyncio
    async def test_detect_ai_disabled(self):
        """Test detection with AI disabled."""
        detector = StudioDetector()
        known_studios = []

        ai_client = Mock()
        ai_client.analyze_scene = AsyncMock()

        scene_data = {"file_path": "/videos/unknown.mp4"}

        result = await detector.detect(
            scene_data, known_studios, ai_client, use_ai=False
        )

        # Should return None as no pattern matches and AI is disabled
        assert result is None
        ai_client.analyze_scene.assert_not_called()


class TestCustomPatterns:
    """Test cases for custom pattern management."""

    def test_add_custom_pattern_valid(self):
        """Test adding a valid custom pattern."""
        detector = StudioDetector()

        detector.add_custom_pattern("Custom Studio", r"custom[\s_-]?studio")

        assert "Custom Studio" in detector.patterns
        assert isinstance(detector.patterns["Custom Studio"], re.Pattern)

    def test_add_custom_pattern_invalid_regex(self):
        """Test adding an invalid regex pattern."""
        detector = StudioDetector()

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            detector.add_custom_pattern("Bad Studio", r"[invalid(regex")

    @pytest.mark.asyncio
    async def test_custom_pattern_detection(self):
        """Test detection using custom pattern."""
        detector = StudioDetector()
        detector.add_custom_pattern("My Studio", r"mystudio|ms\d+")

        known_studios = ["My Studio"]

        result = await detector.detect_from_path(
            "/videos/MyStudio_scene.mp4", known_studios
        )

        assert result is not None
        assert result.value == "My Studio"

    def test_add_custom_pattern_overrides_existing(self):
        """Test that custom pattern overrides existing pattern."""
        detector = StudioDetector()
        original_pattern = detector.patterns.get("Sean Cody")

        # Add custom pattern for existing studio
        detector.add_custom_pattern("Sean Cody", r"new_pattern")

        assert detector.patterns["Sean Cody"] != original_pattern
        assert detector.patterns["Sean Cody"].pattern == "new_pattern"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_detect_empty_path(self):
        """Test detection with empty path."""
        detector = StudioDetector()
        known_studios = ["Studio A"]

        result = await detector.detect_from_path("", known_studios)

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_path_no_extension(self):
        """Test detection with path without extension."""
        detector = StudioDetector()
        known_studios = ["Sean Cody"]

        result = await detector.detect_from_path(
            "/videos/SeanCody_scene", known_studios
        )

        assert result is not None
        assert result.value == "Sean Cody"

    @pytest.mark.asyncio
    async def test_detect_special_characters_in_path(self):
        """Test detection with special characters in path."""
        detector = StudioDetector()
        known_studios = ["Men.com"]

        result = await detector.detect_from_path(
            "/videos/Men.com - Special (2023) [HD].mp4", known_studios
        )

        assert result is not None
        assert result.value == "Men.com"

    @pytest.mark.asyncio
    async def test_detect_multiple_pattern_matches(self):
        """Test when multiple patterns could match."""
        detector = StudioDetector()
        known_studios = ["Amateur", "OnlyFans"]

        # Path that could match both Amateur and OnlyFans
        result = await detector.detect_from_path(
            "/videos/Amateur OnlyFans Content.mp4", known_studios
        )

        # Should return first match found
        assert result is not None
        assert result.value in ["Amateur", "OnlyFans"]

    @pytest.mark.asyncio
    async def test_detect_unicode_in_path(self):
        """Test detection with unicode characters in path."""
        detector = StudioDetector()
        known_studios = ["Citebeur"]

        result = await detector.detect_from_path(
            "/vidéos/Citebeur - Scène.mp4", known_studios
        )

        assert result is not None
        assert result.value == "Citebeur"
