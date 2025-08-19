"""Test tag deletion functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.entities import delete_tag
from app.core.config import Settings
from app.models import Tag


@pytest.mark.asyncio
async def test_delete_tag_success(test_async_session: AsyncSession):
    """Test successful tag deletion from both Stash and local database."""
    # Create a test tag in the database
    test_tag = Tag(
        id="test-tag-123",
        name="Test Tag",
        last_synced=datetime.now(timezone.utc),
    )
    test_async_session.add(test_tag)
    await test_async_session.commit()

    # Mock settings
    mock_settings = MagicMock(spec=Settings)
    mock_settings.stash = MagicMock()
    mock_settings.stash.url = "http://localhost:9999"
    mock_settings.stash.api_key = "test-key"

    # Mock StashService
    with patch("app.api.routes.entities.StashService") as MockStashService:
        mock_stash_instance = AsyncMock()
        mock_stash_instance.delete_tag = AsyncMock(return_value=True)
        mock_stash_instance.__aenter__ = AsyncMock(return_value=mock_stash_instance)
        mock_stash_instance.__aexit__ = AsyncMock()
        MockStashService.return_value = mock_stash_instance

        # Call the delete endpoint
        result = await delete_tag(
            tag_id="test-tag-123", db=test_async_session, settings=mock_settings
        )

        # Verify the result
        assert result["success"] is True
        assert "Test Tag" in result["message"]
        assert result["deleted_tag_id"] == "test-tag-123"

        # Verify StashService was called correctly
        MockStashService.assert_called_once_with("http://localhost:9999", "test-key")
        mock_stash_instance.delete_tag.assert_called_once_with("test-tag-123")

        # Verify tag was deleted from database
        from sqlalchemy import select

        query = select(Tag).where(Tag.id == "test-tag-123")
        result = await test_async_session.execute(query)
        deleted_tag = result.scalar_one_or_none()
        assert deleted_tag is None


@pytest.mark.asyncio
async def test_delete_tag_not_found(test_async_session: AsyncSession):
    """Test deletion of non-existent tag."""
    from fastapi import HTTPException

    mock_settings = MagicMock(spec=Settings)

    with pytest.raises(HTTPException) as exc_info:
        await delete_tag(
            tag_id="non-existent-tag", db=test_async_session, settings=mock_settings
        )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_tag_stash_failure(test_async_session: AsyncSession):
    """Test handling of Stash deletion failure."""
    from fastapi import HTTPException
    from sqlalchemy import select

    # Create a test tag
    test_tag = Tag(
        id="test-tag-456",
        name="Test Tag 2",
        last_synced=datetime.now(timezone.utc),
    )
    test_async_session.add(test_tag)
    await test_async_session.commit()

    mock_settings = MagicMock(spec=Settings)
    mock_settings.stash = MagicMock()
    mock_settings.stash.url = "http://localhost:9999"
    mock_settings.stash.api_key = None

    # Mock StashService to return False (deletion failed)
    with patch("app.api.routes.entities.StashService") as MockStashService:
        mock_stash_instance = AsyncMock()
        mock_stash_instance.delete_tag = AsyncMock(return_value=False)
        mock_stash_instance.__aenter__ = AsyncMock(return_value=mock_stash_instance)
        mock_stash_instance.__aexit__ = AsyncMock(return_value=None)
        MockStashService.return_value = mock_stash_instance

        # Use a try-except block instead of pytest.raises
        exception_raised = False
        exception_detail = None
        exception_status = None

        try:
            await delete_tag(
                tag_id="test-tag-456", db=test_async_session, settings=mock_settings
            )
        except HTTPException as e:
            exception_raised = True
            exception_status = e.status_code
            exception_detail = e.detail

        # Assert that exception was raised with correct details
        assert exception_raised, "HTTPException was not raised"
        assert exception_status == 500, f"Expected status 500, got {exception_status}"
        assert (
            "Failed to delete tag from Stash" in exception_detail
        ), f"Unexpected detail: {exception_detail}"

        # Verify tag still exists in database
        query = select(Tag).where(Tag.id == "test-tag-456")
        result = await test_async_session.execute(query)
        tag = result.scalar_one_or_none()
        assert tag is not None
        assert tag.name == "Test Tag 2"
