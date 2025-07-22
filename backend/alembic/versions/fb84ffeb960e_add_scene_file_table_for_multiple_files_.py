"""add scene_file table for multiple files per scene

Revision ID: fb84ffeb960e
Revises: add_accepted_column
Create Date: 2025-07-21 22:28:32.714793

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb84ffeb960e"
down_revision: Union[str, None] = "add_accepted_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scene_file table
    op.create_table(
        "scene_file",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("basename", sa.String(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, default=False),
        sa.Column("parent_folder_id", sa.String(), nullable=True),
        sa.Column("zip_file_id", sa.String(), nullable=True),
        sa.Column("mod_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("format", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("video_codec", sa.String(), nullable=True),
        sa.Column("audio_codec", sa.String(), nullable=True),
        sa.Column("frame_rate", sa.Float(), nullable=True),
        sa.Column("bit_rate", sa.Integer(), nullable=True),
        sa.Column("oshash", sa.String(), nullable=True),
        sa.Column("phash", sa.String(), nullable=True),
        sa.Column("stash_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stash_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scene_id"], ["scene.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_scene_file_id", "scene_file", ["id"])
    op.create_index("ix_scene_file_scene_id", "scene_file", ["scene_id"])
    op.create_index(
        "idx_scene_file_scene_primary", "scene_file", ["scene_id", "is_primary"]
    )
    op.create_index("ix_scene_file_oshash", "scene_file", ["oshash"])
    op.create_index("ix_scene_file_last_synced", "scene_file", ["last_synced"])

    # Create partial unique constraint to ensure only one primary file per scene
    # This is PostgreSQL-specific syntax, adjust for other databases
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_scene_file_primary_per_scene
            ON scene_file (scene_id)
            WHERE is_primary = true
        """
        )
    else:
        # For other databases, we might need to use a different approach
        # or rely on application-level validation
        op.create_unique_constraint(
            "uq_scene_file_primary", "scene_file", ["scene_id", "is_primary"]
        )

    # Migrate existing data from scene table to scene_file table
    # This will create one scene_file record for each scene that has file data
    op.execute(
        """
        INSERT INTO scene_file (
            id,
            scene_id,
            path,
            is_primary,
            size,
            width,
            height,
            duration,
            video_codec,
            frame_rate,
            bit_rate,
            last_synced,
            created_at,
            updated_at
        )
        SELECT
            scene.id || '_primary',  -- Generate ID by appending _primary
            scene.id,
            COALESCE(scene.file_path, ''),  -- Use file_path if available
            true,  -- Mark as primary
            scene.size,
            scene.width,
            scene.height,
            scene.duration,
            scene.codec,
            scene.framerate,
            scene.bitrate,
            scene.last_synced,
            NOW(),
            NOW()
        FROM scene
        WHERE scene.file_path IS NOT NULL
           OR scene.size IS NOT NULL
           OR scene.duration IS NOT NULL
    """
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_scene_file_last_synced", table_name="scene_file")
    op.drop_index("ix_scene_file_oshash", table_name="scene_file")
    op.drop_index("idx_scene_file_scene_primary", table_name="scene_file")
    op.drop_index("ix_scene_file_scene_id", table_name="scene_file")
    op.drop_index("ix_scene_file_id", table_name="scene_file")

    # Drop the partial unique constraint if it exists
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_scene_file_primary_per_scene")
    else:
        try:
            op.drop_constraint("uq_scene_file_primary", "scene_file", type_="unique")
        except Exception:
            pass  # Constraint might not exist

    # Drop the table
    op.drop_table("scene_file")
