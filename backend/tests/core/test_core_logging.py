"""Tests for core logging configuration."""

import json
import logging
import logging.config
from unittest.mock import MagicMock, patch

from app.core.logging import JSONFormatter, configure_logging


class TestJSONFormatter:
    """Test JSON formatter functionality."""

    def test_basic_format(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        result = formatter.format(record)

        # Parse JSON result
        data = json.loads(result)

        # Verify basic fields
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "path"
        assert data["line"] == 42

    def test_format_with_request_id(self):
        """Test formatting with request ID."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add request ID
        record.request_id = "test-request-123"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["request_id"] == "test-request-123"

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JSONFormatter()

        # Create exception info
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]

    def test_format_with_custom_fields(self):
        """Test formatting with custom extra fields."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add custom fields
        record.user_id = 123
        record.action = "test_action"
        record.custom_data = {"key": "value"}

        result = formatter.format(record)
        data = json.loads(result)

        assert data["user_id"] == 123
        assert data["action"] == "test_action"
        assert data["custom_data"] == {"key": "value"}

    def test_format_excludes_standard_fields(self):
        """Test that standard LogRecord fields are not duplicated."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add fields that should be excluded
        record.processName = "MainProcess"
        record.thread = 12345

        result = formatter.format(record)
        data = json.loads(result)

        # These should not be in the custom fields
        assert "processName" not in data
        assert "thread" not in data


class TestConfigureLogging:
    """Test logging configuration functionality."""

    @patch("logging.config.dictConfig")
    def test_configure_logging_json_mode(self, mock_dict_config):
        """Test logging configuration with JSON mode."""
        # Mock settings at module level
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = True
        mock_settings.logging.level = "INFO"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = False

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            # Verify dictConfig was called
            mock_dict_config.assert_called_once()
            config = mock_dict_config.call_args[0][0]

            # Verify JSON formatter is used
            assert (
                "app.core.logging.JSONFormatter"
                in config["formatters"]["default"]["class"]
            )
            assert config["formatters"]["default"]["format"] is None

    @patch("logging.config.dictConfig")
    def test_configure_logging_text_mode(self, mock_dict_config):
        """Test logging configuration with text mode."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = False
        mock_settings.logging.level = "DEBUG"
        mock_settings.logging.format = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        mock_settings.database.echo = False

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            # Verify dictConfig was called
            mock_dict_config.assert_called_once()
            config = mock_dict_config.call_args[0][0]

            # Verify standard formatter is used
            assert config["formatters"]["default"]["class"] == "logging.Formatter"
            assert (
                config["formatters"]["default"]["format"]
                == mock_settings.logging.format
            )

    @patch("logging.config.dictConfig")
    def test_configure_logging_handlers(self, mock_dict_config):
        """Test logging handlers configuration."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = False
        mock_settings.logging.level = "WARNING"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = False

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            config = mock_dict_config.call_args[0][0]

            # Verify handlers
            assert "default" in config["handlers"]
            assert "access" in config["handlers"]
            assert "error" in config["handlers"]

            # Check default handler
            assert config["handlers"]["default"]["class"] == "logging.StreamHandler"
            assert config["handlers"]["default"]["level"] == "WARNING"
            assert config["handlers"]["default"]["stream"] == "ext://sys.stdout"

            # Check error handler
            assert config["handlers"]["error"]["stream"] == "ext://sys.stderr"

    @patch("logging.config.dictConfig")
    def test_configure_logging_loggers(self, mock_dict_config):
        """Test logger configuration."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = False
        mock_settings.logging.level = "INFO"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = True  # Enable SQL echo

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            config = mock_dict_config.call_args[0][0]

            # Verify loggers
            assert "app" in config["loggers"]
            assert "uvicorn.access" in config["loggers"]
            assert "uvicorn.error" in config["loggers"]
            assert "sqlalchemy.engine" in config["loggers"]

            # Check app logger
            assert config["loggers"]["app"]["level"] == "INFO"
            assert config["loggers"]["app"]["handlers"] == ["default", "error"]
            assert config["loggers"]["app"]["propagate"] is False

            # Check SQLAlchemy logger with echo enabled
            assert config["loggers"]["sqlalchemy.engine"]["level"] == "INFO"

    @patch("logging.config.dictConfig")
    def test_configure_logging_sqlalchemy_echo_disabled(self, mock_dict_config):
        """Test SQLAlchemy logger when echo is disabled."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = False
        mock_settings.logging.level = "INFO"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = False  # Disable SQL echo

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            config = mock_dict_config.call_args[0][0]

            # SQLAlchemy should be WARNING level when echo is disabled
            assert config["loggers"]["sqlalchemy.engine"]["level"] == "WARNING"

    @patch("logging.getLogger")
    @patch("logging.config.dictConfig")
    def test_configure_logging_logs_info(self, mock_dict_config, mock_get_logger):
        """Test that configuration info is logged."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = True
        mock_settings.logging.level = "DEBUG"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = False

        # Mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            # Verify info was logged
            mock_logger.info.assert_called_once_with(
                "Logging configured - Level: DEBUG, JSON: True"
            )

    @patch("logging.config.dictConfig")
    def test_configure_logging_root_logger(self, mock_dict_config):
        """Test root logger configuration."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.logging.json_logs = False
        mock_settings.logging.level = "ERROR"
        mock_settings.logging.format = "%(message)s"
        mock_settings.database.echo = False

        with patch("app.core.logging.settings", mock_settings):
            # Configure logging
            configure_logging()

            config = mock_dict_config.call_args[0][0]

            # Verify root logger
            assert config["root"]["level"] == "ERROR"
            assert config["root"]["handlers"] == ["default"]


class TestIntegration:
    """Integration tests for logging functionality."""

    def test_json_formatter_integration(self, caplog):
        """Test JSON formatter with actual logging."""
        formatter = JSONFormatter()

        # Create a handler with our formatter
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        # Create logger and add handler
        logger = logging.getLogger("test_integration")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message
        with caplog.at_level(logging.INFO):
            logger.info("Integration test message", extra={"user_id": 42})

        # Verify we got JSON output
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # The formatter should be applied when the record is formatted
        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["message"] == "Integration test message"
        assert data["user_id"] == 42
