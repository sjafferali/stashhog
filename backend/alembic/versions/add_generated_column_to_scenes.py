"""Add generated column to scene table

Revision ID: add_generated_column_to_scenes
Revises: 10705e2245ad
Create Date: 2025-08-16

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_generated_column_to_scenes"
down_revision: Union[str, None] = "10705e2245ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add generated column to scene table
    # First add as nullable to avoid long table rewrite
    op.add_column(
        "scene",
        sa.Column("generated", sa.Boolean(), nullable=True),
    )

    # Set default value for existing rows in smaller batches to avoid timeout
    connection = op.get_bind()
    batch_size = 10000
    offset = 0

    while True:
        result = connection.execute(
            sa.text(
                f"""
                UPDATE scene
                SET generated = false
                WHERE generated IS NULL
                AND id IN (
                    SELECT id FROM scene
                    WHERE generated IS NULL
                    ORDER BY id
                    LIMIT {batch_size}
                )
            """
            )
        )

        if result.rowcount == 0:
            break

        offset += batch_size
        # Small delay to prevent overwhelming the database
        connection.execute(sa.text("SELECT pg_sleep(0.1)"))

    # Now make it NOT NULL with default
    op.alter_column("scene", "generated", nullable=False, server_default="false")

    # Create index for better query performance
    op.create_index(op.f("ix_scene_generated"), "scene", ["generated"], unique=False)

    # Create composite index for common queries
    op.create_index(
        "idx_scene_generated_organized", "scene", ["generated", "organized"]
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_scene_generated_organized", table_name="scene")
    op.drop_index(op.f("ix_scene_generated"), table_name="scene")

    # Drop column
    op.drop_column("scene", "generated")
