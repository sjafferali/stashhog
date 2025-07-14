"""
Pagination utilities for the application.
"""
from typing import TypeVar, Generic, List, Optional, Callable, Dict, Any
from math import ceil

from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.api.schemas import PaginatedResponse

T = TypeVar('T')


class Paginator(Generic[T]):
    """Generic paginator for database queries."""
    
    def __init__(
        self,
        query: Select,
        page: int = 1,
        size: int = 20,
        max_size: int = 100
    ):
        """
        Initialize paginator.
        
        Args:
            query: SQLAlchemy select query
            page: Page number (1-based)
            size: Page size
            max_size: Maximum allowed page size
        """
        self.query = query
        self.page = max(1, page)
        self.size = min(max_size, max(1, size))
        self._total: Optional[int] = None
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self._total is None:
            return 0
        return ceil(self._total / self.size) if self.size > 0 else 0
    
    async def get_total(self, session: AsyncSession) -> int:
        """
        Get total count of items.
        
        Args:
            session: Database session
            
        Returns:
            Total count
        """
        if self._total is None:
            # Create count query from the original query
            count_query = select(func.count()).select_from(self.query.subquery())
            result = await session.execute(count_query)
            self._total = result.scalar() or 0
        
        return self._total
    
    async def paginate(
        self,
        session: AsyncSession,
        transformer: Optional[Callable[[Any], T]] = None
    ) -> PaginatedResponse[T]:
        """
        Execute paginated query.
        
        Args:
            session: Database session
            transformer: Optional function to transform results
            
        Returns:
            Paginated response
        """
        # Get total count
        total = await self.get_total(session)
        
        # Execute paginated query
        paginated_query = self.query.limit(self.size).offset(self.offset)
        result = await session.execute(paginated_query)
        items = result.scalars().all()
        
        # Transform items if transformer provided
        if transformer:
            items = [transformer(item) for item in items]
        
        return PaginatedResponse[T](
            items=items,
            total=total,
            page=self.page,
            size=self.size,
            pages=self.pages
        )


def apply_sorting(query: Select, sort: Optional[str], sort_fields: Dict[str, Any]) -> Select:
    """
    Apply sorting to a query.
    
    Args:
        query: Base query
        sort: Sort string (e.g., "-created_at" for descending)
        sort_fields: Mapping of field names to SQLAlchemy columns
        
    Returns:
        Query with sorting applied
    """
    if not sort or not sort_fields:
        return query
    
    # Parse sort string
    if sort.startswith('-'):
        field = sort[1:]
        descending = True
    else:
        field = sort
        descending = False
    
    # Apply sorting if field is valid
    if field in sort_fields:
        column = sort_fields[field]
        if descending:
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    
    return query


def parse_filters(
    filters: Dict[str, Any],
    allowed_fields: List[str]
) -> Dict[str, Any]:
    """
    Parse and validate filters.
    
    Args:
        filters: Raw filters from request
        allowed_fields: List of allowed field names
        
    Returns:
        Validated filters
    """
    parsed_filters = {}
    
    for field, value in filters.items():
        if field in allowed_fields and value is not None:
            # Handle special cases
            if isinstance(value, str):
                # Convert string booleans
                if value.lower() in ('true', 'false'):
                    parsed_filters[field] = value.lower() == 'true'
                # Handle empty strings
                elif value.strip():
                    parsed_filters[field] = value.strip()
            else:
                parsed_filters[field] = value
    
    return parsed_filters


class CursorPaginator:
    """
    Cursor-based pagination for large datasets.
    
    This is more efficient than offset-based pagination for large datasets.
    """
    
    def __init__(
        self,
        query: Select,
        cursor_field: Any,
        size: int = 20,
        cursor: Optional[str] = None,
        reverse: bool = False
    ):
        """
        Initialize cursor paginator.
        
        Args:
            query: Base query
            cursor_field: Field to use for cursor (must be unique and sortable)
            size: Page size
            cursor: Cursor value from previous page
            reverse: Whether to reverse the order
        """
        self.query = query
        self.cursor_field = cursor_field
        self.size = size
        self.cursor = cursor
        self.reverse = reverse
    
    async def paginate(
        self,
        session: AsyncSession,
        encoder: Callable[[Any], str],
        decoder: Callable[[str], Any]
    ) -> Dict[str, Any]:
        """
        Execute cursor-paginated query.
        
        Args:
            session: Database session
            encoder: Function to encode cursor value to string
            decoder: Function to decode cursor string to value
            
        Returns:
            Dict with items, next_cursor, and has_more
        """
        # Apply cursor filter if provided
        if self.cursor:
            cursor_value = decoder(self.cursor)
            if self.reverse:
                self.query = self.query.where(self.cursor_field < cursor_value)
            else:
                self.query = self.query.where(self.cursor_field > cursor_value)
        
        # Apply ordering
        if self.reverse:
            self.query = self.query.order_by(self.cursor_field.desc())
        else:
            self.query = self.query.order_by(self.cursor_field.asc())
        
        # Fetch one extra item to check if there are more
        self.query = self.query.limit(self.size + 1)
        
        result = await session.execute(self.query)
        items = result.scalars().all()
        
        # Check if there are more items
        has_more = len(items) > self.size
        if has_more:
            items = items[:self.size]
        
        # Get next cursor
        next_cursor = None
        if items and has_more:
            last_item = items[-1]
            cursor_value = getattr(last_item, self.cursor_field.key)
            next_cursor = encoder(cursor_value)
        
        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more
        }