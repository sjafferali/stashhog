"""Setting model for application configuration storage."""

from typing import Any, Optional

from sqlalchemy import JSON, Column, String, Text

from app.models.base import BaseModel


class Setting(BaseModel):
    """
    Model for storing application settings as key-value pairs.

    Settings are stored as JSON values to support complex configurations.
    """

    # Primary key is the setting key
    key = Column(String, primary_key=True, index=True)

    # Setting value (stored as JSON for flexibility)
    value = Column(JSON, nullable=False)

    # Optional description for documentation
    description = Column(Text, nullable=True)

    # updated_at is inherited from BaseModel

    @classmethod
    def get_value(cls, session: Any, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a setting value by key.

        Args:
            session: Database session
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        setting = session.query(cls).filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(
        cls, session: Any, key: str, value: Any, description: Optional[str] = None
    ) -> "Setting":
        """
        Set a setting value.

        Args:
            session: Database session
            key: Setting key
            value: Setting value
            description: Optional description

        Returns:
            Setting instance
        """
        setting = session.query(cls).filter_by(key=key).first()
        if setting:
            setting.value = value
            if description is not None:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            session.add(setting)
        return setting  # type: ignore[no-any-return]

    @classmethod
    def delete_value(cls, session: Any, key: str) -> bool:
        """
        Delete a setting.

        Args:
            session: Database session
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        setting = session.query(cls).filter_by(key=key).first()
        if setting:
            session.delete(setting)
            return True
        return False

    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert to dictionary."""
        data = super().to_dict(exclude)
        # Ensure value is included even if it's a complex type
        data["value"] = self.value
        return data
