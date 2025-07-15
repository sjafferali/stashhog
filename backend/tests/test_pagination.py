"""Tests for pagination utilities."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PaginatedResponse
from app.core.pagination import CursorPaginator, Paginator, apply_sorting, parse_filters


class TestPaginator:
    """Test Paginator class."""

    def test_paginator_init(self):
        """Test paginator initialization."""
        query = Mock(spec=Select)

        # Test default values
        paginator = Paginator(query)
        assert paginator.page == 1
        assert paginator.size == 20
        assert paginator.query == query

        # Test custom values
        paginator = Paginator(query, page=3, size=50)
        assert paginator.page == 3
        assert paginator.size == 50

        # Test page minimum
        paginator = Paginator(query, page=0)
        assert paginator.page == 1

        # Test size maximum
        paginator = Paginator(query, size=200, max_size=100)
        assert paginator.size == 100

        # Test size minimum
        paginator = Paginator(query, size=0)
        assert paginator.size == 1

    def test_paginator_offset(self):
        """Test offset calculation."""
        query = Mock(spec=Select)

        paginator = Paginator(query, page=1, size=20)
        assert paginator.offset == 0

        paginator = Paginator(query, page=2, size=20)
        assert paginator.offset == 20

        paginator = Paginator(query, page=5, size=10)
        assert paginator.offset == 40

    def test_paginator_pages(self):
        """Test pages calculation."""
        query = Mock(spec=Select)
        paginator = Paginator(query, size=20)

        # No total set yet
        assert paginator.pages == 0

        # Set total
        paginator._total = 100
        assert paginator.pages == 5

        paginator._total = 95
        assert paginator.pages == 5  # Rounded up

        paginator._total = 0
        assert paginator.pages == 0

    @pytest.mark.asyncio
    async def test_get_total(self):
        """Test getting total count."""
        # Use patch to mock the select function and avoid SQLAlchemy validation
        with patch("app.core.pagination.select") as mock_select:
            query = Mock(spec=Select)
            mock_subquery = Mock()
            query.subquery.return_value = mock_subquery

            # Mock the count query
            mock_count_query = Mock()
            mock_select.return_value.select_from.return_value = mock_count_query

            session = AsyncMock(spec=AsyncSession)
            mock_result = Mock()
            mock_result.scalar.return_value = 42
            session.execute.return_value = mock_result

            paginator = Paginator(query)
            total = await paginator.get_total(session)

            assert total == 42
            assert paginator._total == 42

            # Test caching
            await paginator.get_total(session)
            assert session.execute.call_count == 1  # Should not call again

    @pytest.mark.asyncio
    async def test_get_total_no_results(self):
        """Test getting total with no results."""
        with patch("app.core.pagination.select") as mock_select:
            query = Mock(spec=Select)
            mock_subquery = Mock()
            query.subquery.return_value = mock_subquery

            # Mock the count query
            mock_count_query = Mock()
            mock_select.return_value.select_from.return_value = mock_count_query

            session = AsyncMock(spec=AsyncSession)
            mock_result = Mock()
            mock_result.scalar.return_value = None
            session.execute.return_value = mock_result

            paginator = Paginator(query)
            total = await paginator.get_total(session)

            assert total == 0

    @pytest.mark.asyncio
    async def test_paginate(self):
        """Test pagination execution."""
        with patch("app.core.pagination.select") as mock_select:
            query = Mock(spec=Select)
            mock_subquery = Mock()
            query.subquery.return_value = mock_subquery
            query.limit.return_value.offset.return_value = query

            # Mock the count query
            mock_count_query = Mock()
            mock_select.return_value.select_from.return_value = mock_count_query

            session = AsyncMock(spec=AsyncSession)

            # Mock count query result
            count_result = Mock()
            count_result.scalar.return_value = 42

            # Mock items query result
            items_result = Mock()
            mock_items = [Mock(id=i) for i in range(20)]
            items_result.scalars.return_value.all.return_value = mock_items

            session.execute.side_effect = [count_result, items_result]

            paginator = Paginator(query, page=2, size=20)
            result = await paginator.paginate(session)

            assert isinstance(result, PaginatedResponse)
            assert result.total == 42
            assert result.page == 2
            assert result.per_page == 20
            assert result.pages == 3
            assert len(result.items) == 20

            # Verify query was limited and offset
            query.limit.assert_called_once_with(20)
            query.limit.return_value.offset.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_paginate_with_transformer(self):
        """Test pagination with item transformer."""
        with patch("app.core.pagination.select") as mock_select:
            query = Mock(spec=Select)
            mock_subquery = Mock()
            query.subquery.return_value = mock_subquery
            query.limit.return_value.offset.return_value = query

            # Mock the count query
            mock_count_query = Mock()
            mock_select.return_value.select_from.return_value = mock_count_query

            session = AsyncMock(spec=AsyncSession)

            # Mock results
            count_result = Mock()
            count_result.scalar.return_value = 10

            items_result = Mock()
            # Create mock items - transformer will handle the upper() call
            mock_items = []
            for i in range(5):
                mock_item = Mock()
                mock_item.id = i
                mock_item.name = f"Item {i}"
                mock_items.append(mock_item)
            items_result.scalars.return_value.all.return_value = mock_items

            session.execute.side_effect = [count_result, items_result]

            # Define transformer
            def transformer(item):
                return {"id": item.id, "name": item.name.upper()}

            paginator = Paginator(query)
            result = await paginator.paginate(session, transformer=transformer)

            assert len(result.items) == 5
            assert result.items[0] == {"id": 0, "name": "ITEM 0"}
            assert result.items[4] == {"id": 4, "name": "ITEM 4"}


class TestSortingAndFiltering:
    """Test sorting and filtering utilities."""

    def test_apply_sorting_no_sort(self):
        """Test apply_sorting with no sort parameter."""
        query = Mock(spec=Select)

        result = apply_sorting(query, None, {"created_at": Mock()})
        assert result == query

        result = apply_sorting(query, "", {"created_at": Mock()})
        assert result == query

        result = apply_sorting(query, "created_at", {})
        assert result == query

    def test_apply_sorting_ascending(self):
        """Test apply_sorting with ascending sort."""
        query = Mock(spec=Select)
        query.order_by.return_value = query

        mock_column = Mock()
        mock_column.asc.return_value = Mock()

        sort_fields = {"created_at": mock_column}
        apply_sorting(query, "created_at", sort_fields)

        mock_column.asc.assert_called_once()
        query.order_by.assert_called_once()

    def test_apply_sorting_descending(self):
        """Test apply_sorting with descending sort."""
        query = Mock(spec=Select)
        query.order_by.return_value = query

        mock_column = Mock()
        mock_column.desc.return_value = Mock()

        sort_fields = {"updated_at": mock_column}
        apply_sorting(query, "-updated_at", sort_fields)

        mock_column.desc.assert_called_once()
        query.order_by.assert_called_once()

    def test_apply_sorting_invalid_field(self):
        """Test apply_sorting with invalid field."""
        query = Mock(spec=Select)

        sort_fields = {"created_at": Mock()}
        result = apply_sorting(query, "invalid_field", sort_fields)

        assert result == query
        query.order_by.assert_not_called()

    def test_parse_filters(self):
        """Test parse_filters function."""
        # Test basic filtering
        filters = {"name": "test", "active": "true", "count": 5, "invalid": "ignored"}
        allowed_fields = ["name", "active", "count"]

        result = parse_filters(filters, allowed_fields)

        assert result == {"name": "test", "active": True, "count": 5}

    def test_parse_filters_boolean_conversion(self):
        """Test boolean string conversion in parse_filters."""
        filters = {"active": "True", "enabled": "FALSE", "other": "not_bool"}
        allowed_fields = ["active", "enabled", "other"]

        result = parse_filters(filters, allowed_fields)

        assert result == {"active": True, "enabled": False, "other": "not_bool"}

    def test_parse_filters_empty_values(self):
        """Test handling of empty values in parse_filters."""
        filters = {
            "name": "",
            "description": "  ",
            "tag": " valid ",
            "none_value": None,
        }
        allowed_fields = ["name", "description", "tag", "none_value"]

        result = parse_filters(filters, allowed_fields)

        assert result == {"tag": "valid"}


class TestCursorPaginator:
    """Test CursorPaginator class."""

    def test_cursor_paginator_init(self):
        """Test cursor paginator initialization."""
        query = Mock(spec=Select)
        cursor_field = Mock()

        paginator = CursorPaginator(query, cursor_field)
        assert paginator.query == query
        assert paginator.cursor_field == cursor_field
        assert paginator.size == 20
        assert paginator.cursor is None
        assert paginator.reverse is False

        # Test with custom values
        paginator = CursorPaginator(
            query, cursor_field, size=10, cursor="abc", reverse=True
        )
        assert paginator.size == 10
        assert paginator.cursor == "abc"
        assert paginator.reverse is True

    @pytest.mark.asyncio
    async def test_cursor_paginate_forward(self):
        """Test forward cursor pagination."""
        query = Mock(spec=Select)
        query.where.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query

        cursor_field = Mock()
        cursor_field.asc.return_value = Mock()
        cursor_field.key = "id"

        session = AsyncMock(spec=AsyncSession)

        # Mock items with IDs
        mock_items = [Mock(id=i) for i in range(1, 22)]  # 21 items
        result = Mock()
        result.scalars.return_value.all.return_value = mock_items
        session.execute.return_value = result

        # Encoder/decoder
        encoder = str
        decoder = int

        paginator = CursorPaginator(query, cursor_field, size=20)
        result = await paginator.paginate(session, encoder, decoder)

        assert len(result["items"]) == 20
        assert result["has_more"] is True
        assert result["next_cursor"] == "20"

        # Verify query construction
        cursor_field.asc.assert_called_once()
        query.order_by.assert_called_once()
        query.limit.assert_called_once_with(21)

    @pytest.mark.asyncio
    async def test_cursor_paginate_with_cursor(self):
        """Test cursor pagination with existing cursor."""
        query = Mock(spec=Select)
        query.where.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query

        cursor_field = Mock()
        cursor_field.asc.return_value = Mock()
        cursor_field.__gt__ = Mock(return_value=Mock())  # Use = instead of .
        cursor_field.key = "id"

        session = AsyncMock(spec=AsyncSession)

        # Mock items
        mock_items = [Mock(id=i) for i in range(11, 21)]  # 10 items
        result = Mock()
        result.scalars.return_value.all.return_value = mock_items
        session.execute.return_value = result

        # Encoder/decoder
        encoder = str
        decoder = int

        paginator = CursorPaginator(query, cursor_field, size=20, cursor="10")
        result = await paginator.paginate(session, encoder, decoder)

        assert len(result["items"]) == 10
        assert result["has_more"] is False
        assert result["next_cursor"] is None

        # Verify cursor filter was applied
        cursor_field.__gt__.assert_called_once_with(10)
        query.where.assert_called_once()

    @pytest.mark.asyncio
    async def test_cursor_paginate_reverse(self):
        """Test reverse cursor pagination."""
        query = Mock(spec=Select)
        query.where.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query

        cursor_field = Mock()
        cursor_field.desc.return_value = Mock()
        cursor_field.__lt__ = Mock(return_value=Mock())  # Use = instead of .
        cursor_field.key = "id"

        session = AsyncMock(spec=AsyncSession)

        # Mock items
        mock_items = [Mock(id=i) for i in range(20, 0, -1)]  # 20 items descending
        result = Mock()
        result.scalars.return_value.all.return_value = mock_items[:15]
        session.execute.return_value = result

        # Encoder/decoder
        encoder = str
        decoder = int

        paginator = CursorPaginator(
            query, cursor_field, size=20, cursor="25", reverse=True
        )
        result = await paginator.paginate(session, encoder, decoder)

        assert len(result["items"]) == 15
        assert result["has_more"] is False

        # Verify reverse ordering and filter
        cursor_field.desc.assert_called_once()
        cursor_field.__lt__.assert_called_once_with(25)
