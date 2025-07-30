"""Job context management for logging.

This module provides context management for job execution that automatically
includes job metadata in all log messages emitted during job execution.
"""

import contextvars
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:

    class JobLogRecord(logging.LogRecord):
        job_id: str
        job_type: str
        parent_job_id: str
        job_context: str


# Context variables for job execution
_job_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "job_context", default={}
)


class JobContextFilter(logging.Filter):
    """Logging filter that adds job context information to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add job context fields to the log record."""
        context = _job_context.get()

        # Add job context fields to the record
        record.job_id = context.get("job_id", "")  # type: ignore[attr-defined]
        record.job_type = context.get("job_type", "")  # type: ignore[attr-defined]
        record.parent_job_id = context.get("parent_job_id", "")  # type: ignore[attr-defined]

        # If we have job context, modify the message to include it
        if context:
            job_parts = []
            if record.job_type:  # type: ignore[attr-defined]
                job_parts.append(f"job_type={record.job_type}")  # type: ignore[attr-defined]
            if record.job_id:  # type: ignore[attr-defined]
                job_parts.append(f"job_id={record.job_id}")  # type: ignore[attr-defined]
            if record.parent_job_id:  # type: ignore[attr-defined]
                job_parts.append(f"parent_job_id={record.parent_job_id}")  # type: ignore[attr-defined]

            if job_parts:
                # Prepend job context to the message
                context_prefix = f"[{', '.join(job_parts)}] "
                record.msg = f"{context_prefix}{record.msg}"

        return True


@contextmanager
def job_logging_context(
    job_id: str,
    job_type: str,
    parent_job_id: Optional[str] = None,
    **extra_context: Any,
):
    """Context manager that sets up job-specific logging context.

    Args:
        job_id: The ID of the current job
        job_type: The type of the current job
        parent_job_id: The ID of the parent job (for subjobs in workflows)
        **extra_context: Additional context to include

    Example:
        with job_logging_context(job_id="123", job_type="sync_scenes"):
            logger.info("Starting scene sync")  # Will include job context
    """
    # Get current context and create new context with job info
    current_context = _job_context.get()
    new_context = {
        **current_context,
        "job_id": job_id,
        "job_type": job_type,
        **extra_context,
    }

    if parent_job_id:
        new_context["parent_job_id"] = parent_job_id

    # Set the new context
    token = _job_context.set(new_context)
    try:
        yield
    finally:
        # Restore previous context
        _job_context.reset(token)


def get_current_job_context() -> Dict[str, Any]:
    """Get the current job context.

    Returns:
        Dictionary containing current job context
    """
    return _job_context.get().copy()


def setup_job_logging():
    """Set up job context logging for the application.

    This should be called once during application initialization to add
    the job context filter to all loggers.
    """
    # Get the root logger
    root_logger = logging.getLogger()

    # Check if filter already added to avoid duplicates
    for filter in root_logger.filters:
        if isinstance(filter, JobContextFilter):
            return

    # Create a single filter instance to reuse
    job_filter = JobContextFilter()

    # Add the job context filter to the root logger
    root_logger.addFilter(job_filter)

    # Also add the filter to all existing handlers to ensure it's applied
    # This is needed because handlers added after setup_job_logging() might not inherit filters
    for handler in root_logger.handlers:
        handler_has_filter = any(
            isinstance(f, JobContextFilter) for f in handler.filters
        )
        if not handler_has_filter:
            handler.addFilter(job_filter)
