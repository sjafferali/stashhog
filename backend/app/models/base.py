"""Base model class with common fields and methods."""

from datetime import datetime
from typing import Any, Dict, Optional, Set

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declared_attr

from app.core.database import Base


class BaseModel(Base):
    """Base model with common fields for all database models."""

    __abstract__ = True
    __allow_unmapped__ = True

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )

    @declared_attr  # type: ignore[arg-type]
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        # Handle acronyms and add underscores before capitals
        result = []
        for i, char in enumerate(name):
            if i > 0 and char.isupper():
                # Check if previous char is lowercase or next char is lowercase
                if (i > 0 and name[i - 1].islower()) or (
                    i < len(name) - 1 and name[i + 1].islower()
                ):
                    result.append("_")
            result.append(char.lower())
        return "".join(result)

    def to_dict(self, exclude: Optional[Set[Any]] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude: Set of column names to exclude from output

        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        data = {}

        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()
                data[column.name] = value

        return data

    def update_from_dict(
        self, data: Dict[str, Any], exclude: Optional[Set[Any]] = None
    ) -> None:
        """
        Update model instance from dictionary.

        Args:
            data: Dictionary containing update data
            exclude: Set of column names to exclude from update
        """
        exclude = exclude or {"id", "created_at", "updated_at"}

        for key, value in data.items():
            if hasattr(self, key) and key not in exclude:
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        for column in self.__table__.columns:
            if column.primary_key:
                attrs.append(f"{column.name}={getattr(self, column.name)!r}")
        return f"<{class_name}({', '.join(attrs)})>"
