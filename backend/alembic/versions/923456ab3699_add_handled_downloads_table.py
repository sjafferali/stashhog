"""add_handled_downloads_table

Revision ID: 923456ab3699
Revises: 7c11b1a6bde7
Create Date: 2025-07-31 22:22:22.526219

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "923456ab3699"
down_revision: Union[str, None] = "7c11b1a6bde7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create handled_downloads table
    op.create_table(
        "handled_downloads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("download_name", sa.String(), nullable=False),
        sa.Column("destination_path", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        op.f("ix_handled_downloads_job_id"),
        "handled_downloads",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_handled_downloads_timestamp"),
        "handled_downloads",
        ["timestamp"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        op.f("ix_handled_downloads_timestamp"), table_name="handled_downloads"
    )
    op.drop_index(op.f("ix_handled_downloads_job_id"), table_name="handled_downloads")

    # Drop table
    op.drop_table("handled_downloads")
