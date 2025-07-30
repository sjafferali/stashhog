"""Tests for job context logging functionality."""

import logging

from app.core.job_context import (
    JobContextFilter,
    job_logging_context,
    setup_job_logging,
)


class TestJobContextLogging:
    """Test job context logging functionality."""

    def test_job_context_filter_without_context(self):
        """Test that filter works without active job context."""
        filter = JobContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Filter should return True
        assert filter.filter(record) is True

        # Message should be unchanged
        assert record.msg == "Test message"

        # Job fields should be empty
        assert record.job_id == ""
        assert record.job_type == ""
        assert record.parent_job_id == ""

    def test_job_context_filter_with_context(self):
        """Test that filter adds context to message when active."""
        filter = JobContextFilter()

        with job_logging_context(job_id="test-123", job_type="test_job"):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Filter should return True
            assert filter.filter(record) is True

            # Message should include context prefix
            assert record.msg == "[job_type=test_job, job_id=test-123] Test message"

            # Job fields should be set
            assert record.job_id == "test-123"
            assert record.job_type == "test_job"
            assert record.parent_job_id == ""

    def test_job_context_filter_with_parent_job(self):
        """Test that filter includes parent job ID when present."""
        filter = JobContextFilter()

        with job_logging_context(
            job_id="child-123", job_type="child_job", parent_job_id="parent-456"
        ):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            assert filter.filter(record) is True
            assert "parent_job_id=parent-456" in record.msg
            assert record.parent_job_id == "parent-456"

    def test_nested_job_contexts(self):
        """Test that nested job contexts work correctly."""
        filter = JobContextFilter()

        with job_logging_context(job_id="outer-123", job_type="outer_job"):
            # Test outer context
            record1 = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Outer message",
                args=(),
                exc_info=None,
            )
            filter.filter(record1)
            assert "job_id=outer-123" in record1.msg

            with job_logging_context(
                job_id="inner-456", job_type="inner_job", parent_job_id="outer-123"
            ):
                # Test inner context
                record2 = logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="Inner message",
                    args=(),
                    exc_info=None,
                )
                filter.filter(record2)
                assert "job_id=inner-456" in record2.msg
                assert "parent_job_id=outer-123" in record2.msg

            # Test that outer context is restored
            record3 = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Back to outer",
                args=(),
                exc_info=None,
            )
            filter.filter(record3)
            assert "job_id=outer-123" in record3.msg
            assert "parent_job_id" not in record3.msg

    def test_setup_job_logging_integration(self, caplog):
        """Test full integration with logging system."""
        # Set up job logging first
        setup_job_logging()

        # Get a logger
        logger = logging.getLogger("test_job_logger")
        logger.setLevel(logging.INFO)

        # Test logging without context
        with caplog.at_level(logging.INFO, logger="test_job_logger"):
            logger.info("No context message")
            # The filter modifies the message, so check the record instead
            assert len(caplog.records) == 1
            assert caplog.records[0].msg == "No context message"
            assert "[job_type=" not in caplog.text

        caplog.clear()

        # Test logging with context
        with job_logging_context(job_id="test-789", job_type="integration_test"):
            with caplog.at_level(logging.INFO, logger="test_job_logger"):
                logger.info("With context message")
                # The message should contain the job context
                assert len(caplog.records) == 1
                # Check that context is in the message (it might be added multiple times due to test setup)
                assert (
                    "[job_type=integration_test, job_id=test-789]"
                    in caplog.records[0].msg
                )
                assert "With context message" in caplog.records[0].msg

    def test_setup_job_logging_idempotent(self):
        """Test that setup_job_logging can be called multiple times safely."""
        root_logger = logging.getLogger()

        # Clear filters for clean test
        root_logger.filters.clear()

        # First call
        setup_job_logging()
        filter_count = len(
            [f for f in root_logger.filters if isinstance(f, JobContextFilter)]
        )
        assert filter_count == 1

        # Second call - should not add duplicate
        setup_job_logging()
        filter_count = len(
            [f for f in root_logger.filters if isinstance(f, JobContextFilter)]
        )
        assert filter_count == 1

    def test_empty_job_context_fields(self):
        """Test handling of empty job context fields."""
        filter = JobContextFilter()

        # Test with empty job_id
        with job_logging_context(job_id="", job_type="test_job"):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            filter.filter(record)
            # Should only include non-empty fields
            assert "job_type=test_job" in record.msg
            assert "job_id=" not in record.msg

    def test_special_characters_in_context(self):
        """Test that special characters in job context are handled properly."""
        filter = JobContextFilter()

        with job_logging_context(
            job_id="test-123-[special]", job_type="test_job (with parens)"
        ):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            filter.filter(record)

            # Check that special characters are preserved
            assert "job_id=test-123-[special]" in record.msg
            assert "job_type=test_job (with parens)" in record.msg
