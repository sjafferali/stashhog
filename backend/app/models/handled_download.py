"""Model for tracking processed downloads."""

from sqlalchemy import BigInteger, Column, DateTime, String, text

from app.core.database import Base


class HandledDownload(Base):
    """Model to track downloads that have been processed by the process_downloads job."""

    __tablename__ = "handled_downloads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    download_name = Column(String, nullable=False)
    destination_path = Column(String, nullable=False)
    job_id = Column(String, nullable=False, index=True)
