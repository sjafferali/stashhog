"""
Logging configuration for the application.
"""

import json
import logging
import logging.config
from typing import Any, Dict, Type

from app.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def configure_logging() -> None:
    """Configure application logging."""
    # Determine formatter based on settings
    formatter_class: Type[logging.Formatter]
    if settings.logging.json_logs:
        formatter_class = JSONFormatter
        format_string = None
    else:
        formatter_class = logging.Formatter
        format_string = settings.logging.format

    # Logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "class": (
                    f"{formatter_class.__module__}.{formatter_class.__name__}"
                    if settings.logging.json_logs
                    else "logging.Formatter"
                ),
                "format": format_string,
            },
            "access": {
                "class": (
                    f"{formatter_class.__module__}.{formatter_class.__name__}"
                    if settings.logging.json_logs
                    else "logging.Formatter"
                ),
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(client_addr)s - %(request_line)s - %(status_code)s",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "level": settings.logging.level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "access",
                "stream": "ext://sys.stdout",
            },
            "error": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "app": {
                "level": settings.logging.level,
                "handlers": ["default", "error"],
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["default", "error"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING" if not settings.database.echo else "INFO",
                "handlers": ["default"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.logging.level,
            "handlers": ["default"],
        },
    }

    # Apply configuration
    logging.config.dictConfig(config)

    # Log configuration info
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.logging.level}, "
        f"JSON: {settings.logging.json_logs}"
    )
