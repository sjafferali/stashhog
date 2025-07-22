"""Tests for stash transformers module."""

from unittest.mock import patch

import pytest

from app.services.stash.transformers import (
    _extract_paths_list,
    prepare_scene_update,
    transform_file_info,
    transform_performer,
    transform_scene,
    transform_studio,
    transform_tag,
)


class TestExtractPathsList:
    """Test _extract_paths_list function."""

    def test_extract_paths_empty(self):
        """Test with empty or None input."""
        assert _extract_paths_list(None) == []
        assert _extract_paths_list([]) == []
        assert _extract_paths_list({}) == []

    def test_extract_paths_dict_format(self):
        """Test with dictionary format (new Stash API format)."""
        paths_dict = {
            "stream": "http://example.com/stream",
            "screenshot": "http://example.com/screenshot.jpg",
            "preview": "http://example.com/preview.mp4",
        }
        result = _extract_paths_list(paths_dict)
        assert len(result) == 3
        assert "http://example.com/stream" in result
        assert "http://example.com/screenshot.jpg" in result
        assert "http://example.com/preview.mp4" in result

    def test_extract_paths_dict_with_empty_values(self):
        """Test dictionary format with some empty values."""
        paths_dict = {
            "stream": "http://example.com/stream",
            "screenshot": "",
            "preview": None,
        }
        result = _extract_paths_list(paths_dict)
        assert result == ["http://example.com/stream"]

    def test_extract_paths_list_format(self):
        """Test with list format (legacy format)."""
        paths_list = [
            {"path": "/path/to/file1.mp4"},
            {"path": "/path/to/file2.mp4"},
        ]
        result = _extract_paths_list(paths_list)
        assert result == ["/path/to/file1.mp4", "/path/to/file2.mp4"]

    def test_extract_paths_list_with_invalid_items(self):
        """Test list format with invalid items."""
        paths_list = [
            {"path": "/valid/path.mp4"},
            "invalid_string",
            {"no_path_key": "value"},
            None,
            {"path": "/another/valid.mp4"},
        ]
        result = _extract_paths_list(paths_list)
        assert result == ["/valid/path.mp4", "", "/another/valid.mp4"]

    def test_extract_paths_invalid_type(self):
        """Test with invalid input type."""
        assert _extract_paths_list("string") == []
        assert _extract_paths_list(123) == []


class TestTransformScene:
    """Test transform_scene function."""

    def test_transform_empty_scene(self):
        """Test with empty or None scene."""
        assert transform_scene(None) == {}
        assert transform_scene({}) == {}

    def test_transform_minimal_scene(self):
        """Test with minimal scene data."""
        scene = {
            "id": "123",
            "title": "Test Scene",
        }
        result = transform_scene(scene)
        assert result["id"] == "123"
        assert result["title"] == "Test Scene"
        assert result["path"] == ""
        assert result["paths"] == []
        assert result["file_path"] is None

    def test_transform_scene_with_files(self):
        """Test scene with files."""
        scene = {
            "id": "123",
            "title": "Test Scene",
            "files": [
                {
                    "id": "file1",
                    "path": "/path/to/video.mp4",
                    "size": 1000000,
                }
            ],
        }
        result = transform_scene(scene)
        assert result["file_path"] == "/path/to/video.mp4"
        assert result["path"] == "/path/to/video.mp4"
        assert len(result["files"]) == 1

    def test_transform_scene_with_paths(self):
        """Test scene with paths."""
        scene = {
            "id": "123",
            "title": "Test Scene",
            "paths": {
                "stream": "http://example.com/stream",
                "screenshot": "http://example.com/screenshot.jpg",
            },
        }
        result = transform_scene(scene)
        assert len(result["paths"]) == 2
        assert "http://example.com/stream" in result["paths"]

    def test_transform_complete_scene(self):
        """Test with complete scene data."""
        scene = {
            "id": "123",
            "title": "Complete Scene",
            "details": "Scene details",
            "date": "2024-01-01",
            "rating100": 80,
            "organized": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "studio": {"id": "studio1", "name": "Test Studio"},
            "performers": [{"id": "perf1", "name": "Performer 1"}],
            "tags": [{"id": "tag1", "name": "Tag 1"}],
            "scene_markers": [{"id": "marker1"}],
            "files": [{"id": "file1", "path": "/path/to/file.mp4"}],
            "galleries": [{"id": "gallery1"}],
            "movies": [{"id": "movie1"}],
            "paths": {"stream": "http://example.com/stream"},
        }

        result = transform_scene(scene)

        assert result["id"] == "123"
        assert result["title"] == "Complete Scene"
        assert result["details"] == "Scene details"
        assert result["date"] == "2024-01-01"
        assert result["rating"] == 80
        assert result["rating100"] == 80
        assert result["organized"] is True
        assert result["created_at"] == "2024-01-01T00:00:00Z"
        assert result["updated_at"] == "2024-01-02T00:00:00Z"
        assert result["studio"]["name"] == "Test Studio"
        assert len(result["performers"]) == 1
        assert len(result["tags"]) == 1
        assert len(result["scene_markers"]) == 1
        assert len(result["files"]) == 1
        assert len(result["galleries"]) == 1
        assert len(result["movies"]) == 1

    def test_transform_scene_with_null_studio(self):
        """Test scene with null studio."""
        scene = {
            "id": "123",
            "title": "Test Scene",
            "studio": None,
        }
        result = transform_scene(scene)
        assert result["studio"] is None

    @patch("app.services.stash.transformers.logger")
    def test_transform_scene_with_error(self, mock_logger):
        """Test scene transformation with error."""
        # Create a scene that will cause an error in transform_studio
        scene = {
            "id": "123",
            "studio": "invalid_studio_type",  # Should be dict, not string
        }

        with pytest.raises(AttributeError):
            transform_scene(scene)

        # Verify error logging
        mock_logger.error.assert_called()


class TestTransformPerformer:
    """Test transform_performer function."""

    def test_transform_empty_performer(self):
        """Test with empty or None performer."""
        assert transform_performer(None) == {}
        assert transform_performer({}) == {}

    def test_transform_minimal_performer(self):
        """Test with minimal performer data."""
        performer = {
            "id": "perf1",
            "name": "Test Performer",
        }
        result = transform_performer(performer)
        assert result["id"] == "perf1"
        assert result["name"] == "Test Performer"
        assert result["favorite"] is False
        assert result["ignore_auto_tag"] is False

    def test_transform_complete_performer(self):
        """Test with complete performer data."""
        performer = {
            "id": "perf1",
            "name": "Complete Performer",
            "gender": "FEMALE",
            "url": "http://example.com/performer",
            "birthdate": "1990-01-01",
            "ethnicity": "Caucasian",
            "country": "USA",
            "eye_color": "Blue",
            "height_cm": 170,
            "measurements": "34-24-34",
            "fake_tits": False,
            "career_length": "2010-2020",
            "tattoos": "Butterfly on ankle",
            "piercings": "Ears",
            "alias_list": ["Alias 1", "Alias 2"],
            "favorite": True,
            "rating100": 90,
            "details": "Performer details",
            "death_date": None,
            "hair_color": "Blonde",
            "weight": 55,
            "twitter": "@performer",
            "instagram": "@performer",
            "ignore_auto_tag": True,
        }

        result = transform_performer(performer)

        assert result["id"] == "perf1"
        assert result["name"] == "Complete Performer"
        assert result["gender"] == "FEMALE"
        assert result["url"] == "http://example.com/performer"
        assert result["birthdate"] == "1990-01-01"
        assert result["ethnicity"] == "Caucasian"
        assert result["country"] == "USA"
        assert result["eye_color"] == "Blue"
        assert result["height_cm"] == 170
        assert result["measurements"] == "34-24-34"
        assert result["fake_tits"] is False
        assert result["career_length"] == "2010-2020"
        assert result["tattoos"] == "Butterfly on ankle"
        assert result["piercings"] == "Ears"
        assert result["aliases"] == ["Alias 1", "Alias 2"]
        assert result["favorite"] is True
        assert result["rating"] == 90
        assert result["details"] == "Performer details"
        assert result["death_date"] is None
        assert result["hair_color"] == "Blonde"
        assert result["weight"] == 55
        assert result["twitter"] == "@performer"
        assert result["instagram"] == "@performer"
        assert result["ignore_auto_tag"] is True

    @patch("app.services.stash.transformers.logger")
    def test_transform_performer_missing_id(self, mock_logger):
        """Test performer without id field."""
        performer = {"name": "No ID Performer"}
        result = transform_performer(performer)
        assert result["id"] is None
        assert result["name"] == "No ID Performer"
        mock_logger.error.assert_called_once()


class TestTransformTag:
    """Test transform_tag function."""

    def test_transform_empty_tag(self):
        """Test with empty or None tag."""
        assert transform_tag(None) == {}
        assert transform_tag({}) == {}

    def test_transform_minimal_tag(self):
        """Test with minimal tag data."""
        tag = {
            "id": "tag1",
            "name": "Test Tag",
        }
        result = transform_tag(tag)
        assert result["id"] == "tag1"
        assert result["name"] == "Test Tag"
        assert result["scene_count"] == 0
        assert result["ignore_auto_tag"] is False

    def test_transform_complete_tag(self):
        """Test with complete tag data."""
        tag = {
            "id": "tag1",
            "name": "Complete Tag",
            "description": "Tag description",
            "aliases": ["Alias 1", "Alias 2"],
            "scene_count": 100,
            "performer_count": 50,
            "studio_count": 10,
            "movie_count": 5,
            "gallery_count": 20,
            "image_count": 200,
            "ignore_auto_tag": True,
        }

        result = transform_tag(tag)

        assert result["id"] == "tag1"
        assert result["name"] == "Complete Tag"
        assert result["description"] == "Tag description"
        assert result["aliases"] == ["Alias 1", "Alias 2"]
        assert result["scene_count"] == 100
        assert result["performer_count"] == 50
        assert result["studio_count"] == 10
        assert result["movie_count"] == 5
        assert result["gallery_count"] == 20
        assert result["image_count"] == 200
        assert result["ignore_auto_tag"] is True

    @patch("app.services.stash.transformers.logger")
    def test_transform_tag_missing_id(self, mock_logger):
        """Test tag without id field."""
        tag = {"name": "No ID Tag"}
        result = transform_tag(tag)
        assert result["id"] is None
        assert result["name"] == "No ID Tag"
        mock_logger.error.assert_called_once()


class TestTransformStudio:
    """Test transform_studio function."""

    def test_transform_empty_studio(self):
        """Test with empty or None studio."""
        assert transform_studio(None) == {}
        assert transform_studio({}) == {}

    def test_transform_minimal_studio(self):
        """Test with minimal studio data."""
        studio = {
            "id": "studio1",
            "name": "Test Studio",
        }
        result = transform_studio(studio)
        assert result["id"] == "studio1"
        assert result["name"] == "Test Studio"
        assert result["scene_count"] == 0
        assert result["ignore_auto_tag"] is False

    def test_transform_complete_studio(self):
        """Test with complete studio data."""
        studio = {
            "id": "studio1",
            "name": "Complete Studio",
            "url": "http://example.com/studio",
            "details": "Studio details",
            "rating100": 85,
            "scene_count": 500,
            "aliases": ["Alias 1", "Alias 2"],
            "ignore_auto_tag": True,
        }

        result = transform_studio(studio)

        assert result["id"] == "studio1"
        assert result["name"] == "Complete Studio"
        assert result["url"] == "http://example.com/studio"
        assert result["details"] == "Studio details"
        assert result["rating"] == 85
        assert result["scene_count"] == 500
        assert result["aliases"] == ["Alias 1", "Alias 2"]
        assert result["ignore_auto_tag"] is True

    @patch("app.services.stash.transformers.logger")
    def test_transform_studio_missing_id(self, mock_logger):
        """Test studio without id field."""
        studio = {"name": "No ID Studio"}
        result = transform_studio(studio)
        assert result["id"] is None
        assert result["name"] == "No ID Studio"
        mock_logger.error.assert_called_once()

    @patch("app.services.stash.transformers.logger")
    def test_transform_studio_with_error(self, mock_logger):
        """Test studio transformation with error."""

        # Create a mock object that will raise an exception when accessed
        class ErrorDict(dict):
            def get(self, key, default=None):
                if key == "name":
                    raise Exception("Test error")
                return super().get(key, default)

        studio = ErrorDict({"id": "studio1"})

        with pytest.raises(Exception):
            transform_studio(studio)

        mock_logger.error.assert_called()


class TestTransformFileInfo:
    """Test transform_file_info function."""

    def test_transform_empty_file_info(self):
        """Test with empty or None file info."""
        assert transform_file_info(None) == {}
        assert transform_file_info({}) == {}

    def test_transform_minimal_file_info(self):
        """Test with minimal file info."""
        file_info = {
            "id": 123,
            "path": "/path/to/file.mp4",
        }
        result = transform_file_info(file_info)
        assert result["id"] == "123"
        assert result["path"] == "/path/to/file.mp4"
        assert result["size"] == 0
        assert result["duration"] == 0

    def test_transform_complete_file_info(self):
        """Test with complete file info."""
        file_info = {
            "id": 123,
            "path": "/path/to/video.mp4",
            "basename": "video.mp4",
            "parent_folder_id": 456,
            "zip_file_id": None,
            "mod_time": "2024-01-01T00:00:00Z",
            "size": 1000000000,
            "format": "mp4",
            "duration": 3600.5,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": 1920,
            "height": 1080,
            "frame_rate": 30.0,
            "bit_rate": 5000000,
            "fingerprints": [
                {"type": "oshash", "value": "abc123"},
                {"type": "phash", "value": "def456"},
                {"type": "md5", "value": "ghi789"},
            ],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }

        result = transform_file_info(file_info)

        assert result["id"] == "123"
        assert result["path"] == "/path/to/video.mp4"
        assert result["basename"] == "video.mp4"
        assert result["parent_folder_id"] == 456
        assert result["zip_file_id"] is None
        assert result["mod_time"] == "2024-01-01T00:00:00Z"
        assert result["size"] == 1000000000
        assert result["format"] == "mp4"
        assert result["duration"] == 3600.5
        assert result["video_codec"] == "h264"
        assert result["audio_codec"] == "aac"
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["frame_rate"] == 30.0
        assert result["bit_rate"] == 5000000
        assert result["oshash"] == "abc123"
        assert result["phash"] == "def456"
        assert len(result["fingerprints"]) == 3

    def test_transform_file_info_with_no_fingerprints(self):
        """Test file info without fingerprints."""
        file_info = {
            "id": 123,
            "path": "/path/to/file.mp4",
            "fingerprints": [],
        }
        result = transform_file_info(file_info)
        assert result["oshash"] is None
        assert result["phash"] is None
        assert result["fingerprints"] == []

    def test_transform_file_info_with_invalid_fingerprints(self):
        """Test file info with invalid fingerprint data."""
        file_info = {
            "id": 123,
            "path": "/path/to/file.mp4",
            "fingerprints": [
                {"type": "oshash", "value": "abc123"},
                "invalid_fingerprint",
                {"no_type": "value"},
                None,
            ],
        }
        result = transform_file_info(file_info)
        assert result["oshash"] == "abc123"
        assert result["phash"] is None

    def test_transform_file_info_with_none_id(self):
        """Test file info with None id."""
        file_info = {
            "id": None,
            "path": "/path/to/file.mp4",
        }
        result = transform_file_info(file_info)
        assert result["id"] is None


class TestPrepareSceneUpdate:
    """Test prepare_scene_update function."""

    def test_prepare_empty_updates(self):
        """Test with empty updates."""
        assert prepare_scene_update({}) == {}

    def test_prepare_basic_updates(self):
        """Test basic field updates."""
        updates = {
            "id": "123",
            "rating": 80,
            "o_counter": 5,
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "rating100": 80,
            "o_counter": 5,
        }

    def test_prepare_updates_with_none_values(self):
        """Test updates with None values are skipped."""
        updates = {
            "id": "123",
            "rating": None,
            "o_counter": 5,
            "studio_id": None,
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "o_counter": 5,
        }

    def test_prepare_updates_with_performers(self):
        """Test updates with performer objects."""
        updates = {
            "id": "123",
            "performers": [
                {"id": "perf1", "name": "Performer 1"},
                {"id": "perf2", "name": "Performer 2"},
            ],
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "performer_ids": ["perf1", "perf2"],
        }

    def test_prepare_updates_with_performer_ids(self):
        """Test updates with performer IDs."""
        updates = {
            "id": "123",
            "performers": ["perf1", "perf2"],
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "performer_ids": ["perf1", "perf2"],
        }

    def test_prepare_updates_with_tags(self):
        """Test updates with tag objects."""
        updates = {
            "id": "123",
            "tags": [
                {"id": "tag1", "name": "Tag 1"},
                {"id": "tag2", "name": "Tag 2"},
            ],
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "tag_ids": ["tag1", "tag2"],
        }

    def test_prepare_updates_with_tag_ids(self):
        """Test updates with tag IDs."""
        updates = {
            "id": "123",
            "tags": ["tag1", "tag2"],
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "tag_ids": ["tag1", "tag2"],
        }

    def test_prepare_updates_with_studio(self):
        """Test updates with studio object."""
        updates = {
            "id": "123",
            "studio": {"id": "studio1", "name": "Studio 1"},
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "studio_id": "studio1",
        }

    def test_prepare_updates_with_empty_studio(self):
        """Test updates with empty studio."""
        updates = {
            "id": "123",
            "studio": {},
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "studio_id": None,
        }

    def test_prepare_updates_with_studio_id(self):
        """Test updates with studio_id field."""
        updates = {
            "id": "123",
            "studio_id": "studio1",
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "studio_id": "studio1",
        }

    def test_prepare_complete_updates(self):
        """Test complete scene updates."""
        updates = {
            "id": "123",
            "rating": 90,
            "o_counter": 10,
            "studio": {"id": "studio1", "name": "Studio 1"},
            "performers": [{"id": "perf1"}, {"id": "perf2"}],
            "tags": [{"id": "tag1"}, {"id": "tag2"}],
            "movie_ids": ["movie1", "movie2"],
            "gallery_ids": ["gallery1"],
            "unknown_field": "ignored",
        }

        result = prepare_scene_update(updates)

        assert result == {
            "id": "123",
            "rating100": 90,
            "o_counter": 10,
            "studio_id": "studio1",
            "performer_ids": ["perf1", "perf2"],
            "tag_ids": ["tag1", "tag2"],
            "movie_ids": ["movie1", "movie2"],
            "gallery_ids": ["gallery1"],
            "unknown_field": "ignored",
        }

    def test_prepare_updates_with_mixed_types(self):
        """Test updates with mixed performer/tag types."""
        updates = {
            "id": "123",
            "performers": [{"id": "perf1"}, "perf2"],
            "tags": ["tag1", {"id": "tag2"}],
        }
        result = prepare_scene_update(updates)
        assert result == {
            "id": "123",
            "performer_ids": ["perf1", "perf2"],
            "tag_ids": ["tag1", "tag2"],
        }
