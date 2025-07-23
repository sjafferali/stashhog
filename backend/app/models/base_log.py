"""Base model for log/audit tables that are append-only."""

from sqlalchemy import Column, DateTime, func

from app.core.database import Base


class BaseLogModel(Base):
    """Base model for append-only log tables.

    Unlike BaseModel, this only includes created_at since log entries
    are immutable and never updated.
    """

    __abstract__ = True
    __allow_unmapped__ = True

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        for column in self.__table__.columns:
            if column.primary_key:
                attrs.append(f"{column.name}={getattr(self, column.name)!r}")
        return f"<{class_name}({', '.join(attrs)})>"
