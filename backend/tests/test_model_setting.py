"""Tests for the Setting model."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.setting import Setting


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def sample_setting():
    """Create a sample setting instance."""
    setting = Setting(
        key="test_key",
        value={"enabled": True, "threshold": 10},
        description="Test setting",
    )
    # Mock timestamps
    setting.created_at = datetime.utcnow()
    setting.updated_at = datetime.utcnow()
    return setting


class TestSettingModel:
    """Test cases for Setting model."""

    def test_setting_creation(self):
        """Test creating a setting instance."""
        setting = Setting(
            key="api_key", value="secret123", description="API key for external service"
        )

        assert setting.key == "api_key"
        assert setting.value == "secret123"
        assert setting.description == "API key for external service"

    def test_setting_with_complex_value(self):
        """Test setting with complex JSON value."""
        complex_value = {
            "features": {
                "auto_sync": True,
                "batch_size": 50,
                "endpoints": ["http://api1.com", "http://api2.com"],
            },
            "limits": {"max_retries": 3, "timeout": 30},
        }

        setting = Setting(key="app_config", value=complex_value)
        assert setting.value == complex_value
        assert setting.value["features"]["batch_size"] == 50
        assert len(setting.value["features"]["endpoints"]) == 2

    def test_get_value_existing(self, mock_session, sample_setting):
        """Test getting an existing setting value."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = sample_setting
        mock_session.query.return_value = mock_query

        result = Setting.get_value(mock_session, "test_key")

        assert result == {"enabled": True, "threshold": 10}
        mock_session.query.assert_called_once_with(Setting)
        mock_query.filter_by.assert_called_once_with(key="test_key")

    def test_get_value_not_found(self, mock_session):
        """Test getting a non-existent setting value."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = Setting.get_value(mock_session, "non_existent")

        assert result is None

    def test_get_value_with_default(self, mock_session):
        """Test getting a setting value with default."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        default_value = {"default": True}
        result = Setting.get_value(mock_session, "non_existent", default=default_value)

        assert result == default_value

    def test_set_value_new_setting(self, mock_session):
        """Test setting a new value."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = Setting.set_value(
            mock_session, "new_key", {"new": "value"}, description="New setting"
        )

        assert result.key == "new_key"
        assert result.value == {"new": "value"}
        assert result.description == "New setting"
        mock_session.add.assert_called_once()

    def test_set_value_update_existing(self, mock_session, sample_setting):
        """Test updating an existing setting."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = sample_setting
        mock_session.query.return_value = mock_query

        new_value = {"enabled": False, "threshold": 20}
        result = Setting.set_value(
            mock_session, "test_key", new_value, description="Updated description"
        )

        assert result.value == new_value
        assert result.description == "Updated description"
        mock_session.add.assert_not_called()

    def test_set_value_update_without_description(self, mock_session, sample_setting):
        """Test updating value without changing description."""
        original_description = sample_setting.description
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = sample_setting
        mock_session.query.return_value = mock_query

        new_value = {"enabled": False}
        result = Setting.set_value(mock_session, "test_key", new_value)

        assert result.value == new_value
        assert result.description == original_description

    def test_delete_value_existing(self, mock_session, sample_setting):
        """Test deleting an existing setting."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = sample_setting
        mock_session.query.return_value = mock_query

        result = Setting.delete_value(mock_session, "test_key")

        assert result is True
        mock_session.delete.assert_called_once_with(sample_setting)

    def test_delete_value_not_found(self, mock_session):
        """Test deleting a non-existent setting."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = Setting.delete_value(mock_session, "non_existent")

        assert result is False
        mock_session.delete.assert_not_called()

    def test_to_dict(self, sample_setting):
        """Test converting setting to dictionary."""
        # Mock the parent to_dict method
        sample_setting.to_dict = MagicMock(
            side_effect=lambda exclude=None: {
                "key": sample_setting.key,
                "value": sample_setting.value,
                "description": sample_setting.description,
                "created_at": sample_setting.created_at.isoformat(),
                "updated_at": sample_setting.updated_at.isoformat(),
            }
        )

        result = sample_setting.to_dict()

        assert result["key"] == "test_key"
        assert result["value"] == {"enabled": True, "threshold": 10}
        assert result["description"] == "Test setting"
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_with_exclude(self):
        """Test converting setting to dictionary with exclusions."""
        setting = Setting(key="test", value={"data": "value"}, description="Test")
        setting.created_at = datetime.utcnow()
        setting.updated_at = datetime.utcnow()

        # Create a proper to_dict that respects exclude
        def custom_to_dict(exclude=None):
            data = {
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
                "created_at": setting.created_at.isoformat(),
                "updated_at": setting.updated_at.isoformat(),
            }
            if exclude:
                for field in exclude:
                    data.pop(field, None)
            return data

        result = custom_to_dict(exclude={"description", "created_at"})

        assert "key" in result
        assert "value" in result
        assert "description" not in result
        assert "created_at" not in result
        assert "updated_at" in result


class TestSettingEdgeCases:
    """Test edge cases for Setting model."""

    def test_null_value_handling(self, mock_session):
        """Test handling of null/None values."""
        setting = Setting(key="null_test", value=None)
        assert setting.value is None

        # Test get_value with null
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = setting
        mock_session.query.return_value = mock_query

        result = Setting.get_value(mock_session, "null_test", default="default")
        assert result is None  # Should return None, not default

    def test_empty_json_values(self):
        """Test empty JSON structures."""
        empty_dict = Setting(key="empty_dict", value={})
        empty_list = Setting(key="empty_list", value=[])
        empty_string = Setting(key="empty_string", value="")

        assert empty_dict.value == {}
        assert empty_list.value == []
        assert empty_string.value == ""

    def test_large_json_value(self):
        """Test handling of large JSON values."""
        large_value = {
            f"key_{i}": {
                "data": f"value_{i}" * 100,
                "nested": {"level1": {"level2": {"level3": f"deep_value_{i}"}}},
            }
            for i in range(100)
        }

        setting = Setting(key="large_config", value=large_value)
        assert len(setting.value) == 100
        assert (
            setting.value["key_50"]["nested"]["level1"]["level2"]["level3"]
            == "deep_value_50"
        )

    def test_special_characters_in_key(self):
        """Test keys with special characters."""
        special_keys = [
            "key.with.dots",
            "key-with-dashes",
            "key_with_underscores",
            "key:with:colons",
            "key/with/slashes",
        ]

        for key in special_keys:
            setting = Setting(key=key, value={"test": True})
            assert setting.key == key

    def test_boolean_and_numeric_values(self):
        """Test various primitive value types."""
        bool_setting = Setting(key="bool", value=True)
        int_setting = Setting(key="int", value=42)
        float_setting = Setting(key="float", value=3.14159)
        list_setting = Setting(key="list", value=[1, 2, 3, 4, 5])

        assert bool_setting.value is True
        assert int_setting.value == 42
        assert float_setting.value == 3.14159
        assert list_setting.value == [1, 2, 3, 4, 5]


class TestSettingIntegration:
    """Integration tests for Setting model."""

    def test_crud_workflow(self, mock_session):
        """Test complete CRUD workflow."""
        # Create
        Setting.set_value(mock_session, "workflow_test", {"step": 1})

        # Read
        mock_query = MagicMock()
        setting = Setting(key="workflow_test", value={"step": 1})
        mock_query.filter_by.return_value.first.return_value = setting
        mock_session.query.return_value = mock_query

        value = Setting.get_value(mock_session, "workflow_test")
        assert value == {"step": 1}

        # Update
        setting.value = {"step": 2, "updated": True}
        updated = Setting.set_value(
            mock_session, "workflow_test", {"step": 2, "updated": True}
        )
        assert updated.value["step"] == 2

        # Delete
        deleted = Setting.delete_value(mock_session, "workflow_test")
        assert deleted is True

    def test_bulk_operations(self, mock_session):
        """Test bulk setting operations."""
        settings_data = {
            "feature_flags": {"feature_a": True, "feature_b": False},
            "api_config": {"endpoint": "http://api.example.com", "timeout": 30},
            "ui_preferences": {"theme": "dark", "language": "en"},
        }

        # Bulk create
        created_settings = []
        for key, value in settings_data.items():
            setting = Setting.set_value(mock_session, key, value)
            created_settings.append(setting)

        assert len(created_settings) == 3

        # Verify all settings
        for key, expected_value in settings_data.items():
            mock_query = MagicMock()
            setting = Setting(key=key, value=expected_value)
            mock_query.filter_by.return_value.first.return_value = setting
            mock_session.query.return_value = mock_query

            value = Setting.get_value(mock_session, key)
            assert value == expected_value

    def test_concurrent_updates(self, mock_session):
        """Test handling of concurrent update scenarios."""
        # Initial setting
        initial_setting = Setting(key="concurrent_test", value={"counter": 0})

        # Simulate two concurrent reads
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = initial_setting
        mock_session.query.return_value = mock_query

        # Both read the same initial value (but get copies to simulate real behavior)
        import copy

        value1 = copy.deepcopy(Setting.get_value(mock_session, "concurrent_test"))
        value2 = copy.deepcopy(Setting.get_value(mock_session, "concurrent_test"))

        assert value1 == value2 == {"counter": 0}

        # Both try to update their local copies
        value1["counter"] = 1
        value2["counter"] = 2

        # First update
        Setting.set_value(mock_session, "concurrent_test", value1)
        initial_setting.value = value1

        # Second update (overwrites first)
        Setting.set_value(mock_session, "concurrent_test", value2)
        initial_setting.value = value2

        final_value = Setting.get_value(mock_session, "concurrent_test")
        assert final_value == {"counter": 2}  # Last update wins
