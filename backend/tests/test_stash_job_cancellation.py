"""Test cancellation behavior for Stash jobs."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.jobs.stash_generate_jobs import _poll_job_status as generate_poll_job_status
from app.jobs.stash_scan_jobs import _poll_job_status as scan_poll_job_status


@pytest.mark.asyncio
async def test_stash_generate_job_cancellation_continues_polling():
    """Test that stash generate job continues polling after cancellation request."""
    # Mock stash service
    stash_service = Mock()
    stash_service.execute_graphql = AsyncMock()

    # Mock cancellation token
    cancellation_token = Mock()
    cancellation_token.is_cancelled = False

    # Mock progress callback
    progress_callback = AsyncMock()

    # Setup mock responses
    job_responses = [
        # First response - job is running
        {
            "findJob": {
                "status": "RUNNING",
                "progress": 0.5,
                "description": "Processing",
            }
        },
        # Second response - after cancellation, job is stopping
        {"findJob": {"status": "STOPPING", "progress": 0.6, "description": "Stopping"}},
        # Third response - job is cancelled
        {
            "findJob": {
                "status": "CANCELLED",
                "progress": 0.6,
                "description": "Cancelled",
            }
        },
    ]

    call_count = 0

    async def mock_execute_graphql(query, variables):
        nonlocal call_count
        if "stopJob" in query:
            # Stop job mutation
            return {"stopJob": True}
        else:
            # Find job query
            result = job_responses[min(call_count, len(job_responses) - 1)]
            call_count += 1
            return result

    stash_service.execute_graphql = mock_execute_graphql

    # Mock asyncio.sleep to make test instant
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Start polling in background
        poll_task = asyncio.create_task(
            generate_poll_job_status(
                stash_service, "test-job-id", progress_callback, cancellation_token
            )
        )

        # Let the event loop run one iteration to start polling
        await asyncio.sleep(0)

        # Trigger cancellation
        cancellation_token.is_cancelled = True

        # Wait for result
        result = await poll_task

    # Verify result
    assert result["status"] == "cancelled"
    assert result["message"] == "Metadata generation was cancelled"
    assert result["stash_job_id"] == "test-job-id"

    # Verify that polling continued after cancellation request
    assert call_count >= 2  # Should have polled at least twice


@pytest.mark.asyncio
async def test_stash_scan_job_cancellation_continues_polling():
    """Test that stash scan job continues polling after cancellation request."""
    # Mock stash service
    stash_service = Mock()
    stash_service.execute_graphql = AsyncMock()

    # Mock cancellation token
    cancellation_token = Mock()
    cancellation_token.is_cancelled = False

    # Mock progress callback
    progress_callback = AsyncMock()

    # Setup mock responses
    job_responses = [
        # First response - job is running
        {"findJob": {"status": "RUNNING", "progress": 0.3, "description": "Scanning"}},
        # Second response - after cancellation, job is stopping
        {"findJob": {"status": "STOPPING", "progress": 0.4, "description": "Stopping"}},
        # Third response - job is cancelled
        {
            "findJob": {
                "status": "CANCELLED",
                "progress": 0.4,
                "description": "Cancelled",
            }
        },
    ]

    call_count = 0

    async def mock_execute_graphql(query, variables):
        nonlocal call_count
        if "stopJob" in query:
            # Stop job mutation
            return {"stopJob": True}
        else:
            # Find job query
            result = job_responses[min(call_count, len(job_responses) - 1)]
            call_count += 1
            return result

    stash_service.execute_graphql = mock_execute_graphql

    # Mock asyncio.sleep to make test instant
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Start polling in background
        poll_task = asyncio.create_task(
            scan_poll_job_status(
                stash_service, "test-job-id", progress_callback, cancellation_token
            )
        )

        # Let the event loop run one iteration to start polling
        await asyncio.sleep(0)

        # Trigger cancellation
        cancellation_token.is_cancelled = True

        # Wait for result
        result = await poll_task

    # Verify result
    assert result["status"] == "cancelled"
    assert result["message"] == "Stash scan was cancelled"
    assert result["stash_job_id"] == "test-job-id"

    # Verify that polling continued after cancellation request
    assert call_count >= 2  # Should have polled at least twice
