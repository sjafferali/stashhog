"""
Tests for details/description generation module.

This module tests the scene description generation functionality including
HTML cleaning, description formatting, and metadata-based description creation.
"""

import pytest

from app.services.analysis.details_generator import DetailsGenerator, HTMLStripper
from app.services.analysis.models import DetectionResult


class TestHTMLStripper:
    """Test cases for HTML stripping functionality."""

    def test_strip_basic_html(self):
        """Test stripping basic HTML tags."""
        stripper = HTMLStripper()
        stripper.feed("<p>Hello <b>world</b>!</p>")

        result = stripper.get_data()

        assert result == "Hello world!"

    def test_strip_nested_html(self):
        """Test stripping nested HTML tags."""
        stripper = HTMLStripper()
        stripper.feed("<div><p>Nested <span><b>content</b></span> here</p></div>")

        result = stripper.get_data()

        assert result == "Nested content here"

    def test_strip_with_attributes(self):
        """Test stripping HTML with attributes."""
        stripper = HTMLStripper()
        stripper.feed('<a href="https://example.com" class="link">Click here</a>')

        result = stripper.get_data()

        assert result == "Click here"

    def test_strip_empty_tags(self):
        """Test handling of empty HTML tags."""
        stripper = HTMLStripper()
        stripper.feed("<br/><hr/>Text<img src='test.jpg'/>")

        result = stripper.get_data()

        assert result == "Text"


class TestDetailsGeneratorInit:
    """Test cases for DetailsGenerator initialization."""

    def test_init_empty_cache(self):
        """Test that cache is initialized empty."""
        generator = DetailsGenerator()

        assert generator._description_cache == {}

    def test_constants_defined(self):
        """Test that class constants are properly defined."""
        assert DetailsGenerator.MAX_DESCRIPTION_LENGTH == 500
        assert DetailsGenerator.MIN_SUBSTANTIAL_LENGTH == 50


class TestHTMLCleaning:
    """Test cases for HTML cleaning functionality."""

    def test_clean_html_basic(self):
        """Test basic HTML cleaning."""
        generator = DetailsGenerator()

        html = "<p>This is <strong>bold</strong> text.</p>"
        result = generator.clean_html(html)

        assert result == "This is bold text."

    def test_clean_html_entities(self):
        """Test cleaning HTML entities."""
        generator = DetailsGenerator()

        html = "This &amp; that &lt;tag&gt; &quot;quoted&quot; &#39;text&#39;"
        result = generator.clean_html(html)

        assert result == "This & that <tag> \"quoted\" 'text'"

    def test_clean_html_whitespace(self):
        """Test cleaning excessive whitespace."""
        generator = DetailsGenerator()

        html = "<p>Too    much     whitespace\n\n\nhere</p>"
        result = generator.clean_html(html)

        assert result == "Too much whitespace here"

    def test_clean_html_empty(self):
        """Test cleaning empty/None input."""
        generator = DetailsGenerator()

        assert generator.clean_html("") == ""
        assert generator.clean_html(None) == ""

    def test_clean_html_nbsp(self):
        """Test cleaning non-breaking spaces."""
        generator = DetailsGenerator()

        html = "Text&nbsp;with&nbsp;non-breaking&nbsp;spaces"
        result = generator.clean_html(html)

        assert result == "Text with non-breaking spaces"


class TestDescriptionCleaning:
    """Test cases for description cleaning and validation."""

    def test_clean_description_basic(self):
        """Test basic description cleaning."""
        generator = DetailsGenerator()

        desc = "This is a basic description"
        result = generator._clean_description(desc)

        assert result == "This is a basic description."

    def test_clean_description_html_removal(self):
        """Test HTML removal from descriptions."""
        generator = DetailsGenerator()

        desc = "<p>Description with <b>HTML</b> tags</p>"
        result = generator._clean_description(desc)

        assert result == "Description with HTML tags."

    def test_clean_description_url_preservation(self):
        """Test that URLs are preserved in descriptions."""
        generator = DetailsGenerator()

        desc = "Visit https://example.com or http://test.org for more"
        result = generator._clean_description(desc)

        # URLs are now preserved
        assert result == "Visit https://example.com or http://test.org for more."

    def test_clean_description_email_preservation(self):
        """Test that email addresses are preserved in descriptions."""
        generator = DetailsGenerator()

        desc = "Contact us at test@example.com for info"
        result = generator._clean_description(desc)

        # Email addresses are now preserved
        assert result == "Contact us at test@example.com for info."

    def test_clean_description_sentence_ending(self):
        """Test proper sentence ending addition."""
        generator = DetailsGenerator()

        # Already has ending
        assert generator._clean_description("Already ends.") == "Already ends."
        assert generator._clean_description("Question?") == "Question?"
        assert generator._clean_description("Exclamation!") == "Exclamation!"

        # Needs ending
        assert generator._clean_description("No ending") == "No ending."

    def test_clean_description_truncation(self):
        """Test description truncation at sentence boundaries."""
        generator = DetailsGenerator()

        # Create a long description
        long_desc = "First sentence. " * 50  # Much longer than 500 chars
        result = generator._clean_description(long_desc)

        assert len(result) <= generator.MAX_DESCRIPTION_LENGTH
        assert result.endswith(".")
        assert "First sentence" in result

    def test_clean_description_truncation_boundary(self):
        """Test truncation preserves sentence boundaries."""
        generator = DetailsGenerator()

        desc = "This is the first sentence. This is the second one. " * 20
        result = generator._clean_description(desc)

        # Should truncate at sentence boundary
        assert len(result) <= generator.MAX_DESCRIPTION_LENGTH
        assert result.endswith(".")
        assert not result.endswith(". .")  # No double periods


class TestBasicDescriptionCreation:
    """Test cases for basic description creation from metadata."""

    def test_create_basic_empty_scene(self):
        """Test description creation with empty scene data."""
        generator = DetailsGenerator()

        result = generator.create_basic_description({})

        assert isinstance(result, DetectionResult)
        assert result.value == ""
        assert result.confidence == 0.0
        assert result.source == "metadata"
        assert result.metadata["type"] == "empty"

    def test_create_basic_with_studio(self):
        """Test description with studio information."""
        generator = DetailsGenerator()

        scene_data = {"studio": {"name": "Test Studio"}}

        result = generator.create_basic_description(scene_data)

        assert result.value == "A Test Studio production."
        assert result.confidence == 0.5
        assert result.metadata["type"] == "basic"

    def test_create_basic_with_single_performer(self):
        """Test description with single performer."""
        generator = DetailsGenerator()

        scene_data = {"performers": [{"name": "John Doe"}]}

        result = generator.create_basic_description(scene_data)

        assert result.value == "featuring John Doe."
        assert result.confidence == 0.5

    def test_create_basic_with_two_performers(self):
        """Test description with two performers."""
        generator = DetailsGenerator()

        scene_data = {"performers": [{"name": "John Doe"}, {"name": "Jane Smith"}]}

        result = generator.create_basic_description(scene_data)

        assert result.value == "featuring John Doe and Jane Smith."

    def test_create_basic_with_multiple_performers(self):
        """Test description with multiple performers."""
        generator = DetailsGenerator()

        scene_data = {
            "performers": [
                {"name": "Actor One"},
                {"name": "Actor Two"},
                {"name": "Actor Three"},
            ]
        }

        result = generator.create_basic_description(scene_data)

        assert result.value == "featuring Actor One, Actor Two, and Actor Three."

    def test_create_basic_with_duration(self):
        """Test description with duration."""
        generator = DetailsGenerator()

        scene_data = {"duration": 1800}  # 30 minutes

        result = generator.create_basic_description(scene_data)

        assert result.value == "(30 minutes)."

    def test_create_basic_full_metadata(self):
        """Test description with all metadata."""
        generator = DetailsGenerator()

        scene_data = {
            "studio": {"name": "Great Studio"},
            "performers": [{"name": "Star One"}, {"name": "Star Two"}],
            "duration": 2400,  # 40 minutes
        }

        result = generator.create_basic_description(scene_data)

        expected = (
            "A Great Studio production featuring Star One and Star Two (40 minutes)."
        )
        assert result.value == expected
        assert result.confidence == 0.5

    def test_create_basic_performer_string_format(self):
        """Test description with performers as strings."""
        generator = DetailsGenerator()

        scene_data = {"performers": ["John Doe", "Jane Smith"]}

        result = generator.create_basic_description(scene_data)

        assert result.value == "featuring John Doe and Jane Smith."

    def test_create_basic_mixed_performer_format(self):
        """Test description with mixed performer formats."""
        generator = DetailsGenerator()

        scene_data = {
            "performers": [
                {"name": "John Doe"},
                "Jane Smith",
                {"name": "Bob Johnson", "id": "123"},
            ]
        }

        result = generator.create_basic_description(scene_data)

        assert result.value == "featuring John Doe, Jane Smith, and Bob Johnson."

    def test_create_basic_zero_duration(self):
        """Test that zero duration is not included."""
        generator = DetailsGenerator()

        scene_data = {"studio": {"name": "Test Studio"}, "duration": 0}

        result = generator.create_basic_description(scene_data)

        assert result.value == "A Test Studio production."
        assert "(0 minutes)" not in result.value

    def test_create_basic_short_duration(self):
        """Test description with duration less than a minute."""
        generator = DetailsGenerator()

        scene_data = {"duration": 45}  # 45 seconds

        result = generator.create_basic_description(scene_data)

        # Should not include duration if less than 1 minute
        assert result.value == ""
        assert result.metadata["type"] == "empty"


class TestHelperMethods:
    """Test cases for helper methods."""

    def test_extract_performer_names_dicts(self):
        """Test extracting names from dict performers."""
        generator = DetailsGenerator()

        performers = [
            {"name": "John Doe", "id": "1"},
            {"name": "Jane Smith"},
            {"id": "3"},  # No name
        ]

        names = generator._extract_performer_names(performers)

        assert names == ["John Doe", "Jane Smith"]

    def test_extract_performer_names_strings(self):
        """Test extracting names from string performers."""
        generator = DetailsGenerator()

        performers = ["John Doe", "Jane Smith", ""]

        names = generator._extract_performer_names(performers)

        assert names == ["John Doe", "Jane Smith", ""]

    def test_format_performer_list_variations(self):
        """Test formatting performer lists of various sizes."""
        generator = DetailsGenerator()

        # Single
        assert generator._format_performer_list(["John"]) == "featuring John"

        # Two
        assert (
            generator._format_performer_list(["John", "Jane"])
            == "featuring John and Jane"
        )

        # Three
        assert (
            generator._format_performer_list(["A", "B", "C"]) == "featuring A, B, and C"
        )

        # Four or more
        assert (
            generator._format_performer_list(["A", "B", "C", "D"])
            == "featuring A, B, C, and D"
        )

    def test_add_studio_to_parts_variations(self):
        """Test adding studio with various data formats."""
        generator = DetailsGenerator()

        # Valid studio dict
        parts = []
        generator._add_studio_to_parts({"studio": {"name": "Test"}}, parts)
        assert parts == ["A Test production"]

        # Empty studio name
        parts = []
        generator._add_studio_to_parts({"studio": {"name": ""}}, parts)
        assert parts == []

        # Studio as string (invalid format)
        parts = []
        generator._add_studio_to_parts({"studio": "Test Studio"}, parts)
        assert parts == []

        # No studio
        parts = []
        generator._add_studio_to_parts({}, parts)
        assert parts == []


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_description_invalid_types(self):
        """Test handling of invalid data types."""
        generator = DetailsGenerator()

        # Performers as non-list - will iterate through string as characters
        scene_data = {"performers": "John Doe"}
        result = generator.create_basic_description(scene_data)
        # Will treat each character as a performer name
        assert "featuring" in result.value
        assert result.value == "featuring J, o, h, n,  , D, o, and e."

        # Duration as string - will cause TypeError
        scene_data = {"duration": "thirty minutes"}
        with pytest.raises(TypeError):
            result = generator.create_basic_description(scene_data)

    def test_clean_description_unicode(self):
        """Test handling of unicode characters."""
        generator = DetailsGenerator()

        desc = "Unicode test: café, naïve, 日本語"
        result = generator._clean_description(desc)

        assert result == "Unicode test: café, naïve, 日本語."

    def test_clean_html_malformed(self):
        """Test handling of malformed HTML."""
        generator = DetailsGenerator()

        # Unclosed tags
        html = "<p>Unclosed paragraph <b>bold text"
        result = generator.clean_html(html)

        assert "Unclosed paragraph" in result
        assert "bold text" in result

    def test_empty_performer_list(self):
        """Test handling of empty performer list."""
        generator = DetailsGenerator()

        scene_data = {"performers": []}
        result = generator.create_basic_description(scene_data)

        assert result.value == ""
        assert result.metadata["type"] == "empty"
