"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-14

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create studio table
    op.create_table(
        "studio",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_studio_name_lower", "studio", ["name"], unique=False)
    op.create_index(
        op.f("ix_studio_created_at"), "studio", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_studio_id"), "studio", ["id"], unique=False)
    op.create_index(
        op.f("ix_studio_last_synced"), "studio", ["last_synced"], unique=False
    )
    op.create_index(op.f("ix_studio_name"), "studio", ["name"], unique=False)
    op.create_index(
        op.f("ix_studio_updated_at"), "studio", ["updated_at"], unique=False
    )

    # Create analysis_plan table
    op.create_table(
        "analysis_plan",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "REVIEWING", "APPLIED", "CANCELLED", name="planstatus"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_plan_status_applied",
        "analysis_plan",
        ["status", "applied_at"],
        unique=False,
    )
    op.create_index(
        "idx_plan_status_created",
        "analysis_plan",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_plan_applied_at"),
        "analysis_plan",
        ["applied_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_plan_created_at"),
        "analysis_plan",
        ["created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_analysis_plan_id"), "analysis_plan", ["id"], unique=False)
    op.create_index(
        op.f("ix_analysis_plan_name"), "analysis_plan", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_analysis_plan_status"), "analysis_plan", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_analysis_plan_updated_at"),
        "analysis_plan",
        ["updated_at"],
        unique=False,
    )

    # Create job table
    op.create_table(
        "job",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "SYNC",
                "ANALYSIS",
                "APPLY_PLAN",
                "EXPORT",
                "IMPORT",
                "CLEANUP",
                name="jobtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="jobstatus",
            ),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("processed_items", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_job_completed", "job", ["completed_at"], unique=False)
    op.create_index(
        "idx_job_status_created", "job", ["status", "created_at"], unique=False
    )
    op.create_index("idx_job_type_status", "job", ["type", "status"], unique=False)
    op.create_index(op.f("ix_job_completed_at"), "job", ["completed_at"], unique=False)
    op.create_index(op.f("ix_job_created_at"), "job", ["created_at"], unique=False)
    op.create_index(op.f("ix_job_id"), "job", ["id"], unique=False)
    op.create_index(op.f("ix_job_started_at"), "job", ["started_at"], unique=False)
    op.create_index(op.f("ix_job_status"), "job", ["status"], unique=False)
    op.create_index(op.f("ix_job_type"), "job", ["type"], unique=False)
    op.create_index(op.f("ix_job_updated_at"), "job", ["updated_at"], unique=False)

    # Create performer table
    op.create_table(
        "performer",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_performer_name_lower", "performer", ["name"], unique=False)
    op.create_index(
        op.f("ix_performer_created_at"), "performer", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_performer_id"), "performer", ["id"], unique=False)
    op.create_index(
        op.f("ix_performer_last_synced"), "performer", ["last_synced"], unique=False
    )
    op.create_index(op.f("ix_performer_name"), "performer", ["name"], unique=False)
    op.create_index(
        op.f("ix_performer_updated_at"), "performer", ["updated_at"], unique=False
    )

    # Create scheduled_task table
    op.create_table(
        "scheduled_task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("schedule", sa.String(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "idx_scheduled_task_enabled_next",
        "scheduled_task",
        ["enabled", "next_run"],
        unique=False,
    )
    op.create_index(
        "idx_scheduled_task_type_enabled",
        "scheduled_task",
        ["task_type", "enabled"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_task_created_at"),
        "scheduled_task",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_task_enabled"), "scheduled_task", ["enabled"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_task_id"), "scheduled_task", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_task_last_run"), "scheduled_task", ["last_run"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_task_name"), "scheduled_task", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_task_next_run"), "scheduled_task", ["next_run"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_task_task_type"),
        "scheduled_task",
        ["task_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_task_updated_at"),
        "scheduled_task",
        ["updated_at"],
        unique=False,
    )

    # Create setting table
    op.create_table(
        "setting",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_setting_created_at"), "setting", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_setting_key"), "setting", ["key"], unique=False)
    op.create_index(
        op.f("ix_setting_updated_at"), "setting", ["updated_at"], unique=False
    )

    # Create tag table
    op.create_table(
        "tag",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_tag_name_lower", "tag", ["name"], unique=False)
    op.create_index(op.f("ix_tag_created_at"), "tag", ["created_at"], unique=False)
    op.create_index(op.f("ix_tag_id"), "tag", ["id"], unique=False)
    op.create_index(op.f("ix_tag_last_synced"), "tag", ["last_synced"], unique=False)
    op.create_index(op.f("ix_tag_name"), "tag", ["name"], unique=False)
    op.create_index(op.f("ix_tag_updated_at"), "tag", ["updated_at"], unique=False)

    # Create scene table
    op.create_table(
        "scene",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("paths", sa.JSON(), nullable=False),
        sa.Column("organized", sa.Boolean(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scene_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("studio_id", sa.String(), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["studio_id"], ["studio.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_scene_organized_date", "scene", ["organized", "scene_date"], unique=False
    )
    op.create_index(
        "idx_scene_studio_date", "scene", ["studio_id", "scene_date"], unique=False
    )
    op.create_index(
        "idx_scene_sync_status", "scene", ["last_synced", "organized"], unique=False
    )
    op.create_index(op.f("ix_scene_created_at"), "scene", ["created_at"], unique=False)
    op.create_index(op.f("ix_scene_id"), "scene", ["id"], unique=False)
    op.create_index(
        op.f("ix_scene_last_synced"), "scene", ["last_synced"], unique=False
    )
    op.create_index(op.f("ix_scene_organized"), "scene", ["organized"], unique=False)
    op.create_index(op.f("ix_scene_scene_date"), "scene", ["scene_date"], unique=False)
    op.create_index(op.f("ix_scene_studio_id"), "scene", ["studio_id"], unique=False)
    op.create_index(op.f("ix_scene_title"), "scene", ["title"], unique=False)
    op.create_index(op.f("ix_scene_updated_at"), "scene", ["updated_at"], unique=False)

    # Create plan_change table
    op.create_table(
        "plan_change",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("ADD", "REMOVE", "UPDATE", "SET", name="changeaction"),
            nullable=False,
        ),
        sa.Column("current_value", sa.JSON(), nullable=True),
        sa.Column("proposed_value", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("applied", sa.Boolean(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["analysis_plan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scene.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_change_applied_plan", "plan_change", ["applied", "plan_id"], unique=False
    )
    op.create_index(
        "idx_change_confidence", "plan_change", ["confidence"], unique=False
    )
    op.create_index(
        "idx_change_plan_field", "plan_change", ["plan_id", "field"], unique=False
    )
    op.create_index(
        "idx_change_scene_field", "plan_change", ["scene_id", "field"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_action"), "plan_change", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_applied"), "plan_change", ["applied"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_applied_at"), "plan_change", ["applied_at"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_created_at"), "plan_change", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_field"), "plan_change", ["field"], unique=False
    )
    op.create_index(op.f("ix_plan_change_id"), "plan_change", ["id"], unique=False)
    op.create_index(
        op.f("ix_plan_change_plan_id"), "plan_change", ["plan_id"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_scene_id"), "plan_change", ["scene_id"], unique=False
    )
    op.create_index(
        op.f("ix_plan_change_updated_at"), "plan_change", ["updated_at"], unique=False
    )

    # Create scene_performer association table
    op.create_table(
        "scene_performer",
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("performer_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["performer_id"], ["performer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scene.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scene_id", "performer_id"),
        sa.UniqueConstraint("scene_id", "performer_id", name="uq_scene_performer"),
    )
    op.create_index(
        "idx_scene_performer_performer",
        "scene_performer",
        ["performer_id"],
        unique=False,
    )
    op.create_index(
        "idx_scene_performer_scene", "scene_performer", ["scene_id"], unique=False
    )

    # Create scene_tag association table
    op.create_table(
        "scene_tag",
        sa.Column("scene_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scene.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("scene_id", "tag_id"),
        sa.UniqueConstraint("scene_id", "tag_id", name="uq_scene_tag"),
    )
    op.create_index("idx_scene_tag_scene", "scene_tag", ["scene_id"], unique=False)
    op.create_index("idx_scene_tag_tag", "scene_tag", ["tag_id"], unique=False)


def downgrade() -> None:
    # Drop association tables first
    op.drop_index("idx_scene_tag_tag", table_name="scene_tag")
    op.drop_index("idx_scene_tag_scene", table_name="scene_tag")
    op.drop_table("scene_tag")

    op.drop_index("idx_scene_performer_scene", table_name="scene_performer")
    op.drop_index("idx_scene_performer_performer", table_name="scene_performer")
    op.drop_table("scene_performer")

    # Drop plan_change table
    op.drop_index(op.f("ix_plan_change_updated_at"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_scene_id"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_plan_id"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_id"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_field"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_created_at"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_applied_at"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_applied"), table_name="plan_change")
    op.drop_index(op.f("ix_plan_change_action"), table_name="plan_change")
    op.drop_index("idx_change_scene_field", table_name="plan_change")
    op.drop_index("idx_change_plan_field", table_name="plan_change")
    op.drop_index("idx_change_confidence", table_name="plan_change")
    op.drop_index("idx_change_applied_plan", table_name="plan_change")
    op.drop_table("plan_change")

    # Drop scene table
    op.drop_index(op.f("ix_scene_updated_at"), table_name="scene")
    op.drop_index(op.f("ix_scene_title"), table_name="scene")
    op.drop_index(op.f("ix_scene_studio_id"), table_name="scene")
    op.drop_index(op.f("ix_scene_scene_date"), table_name="scene")
    op.drop_index(op.f("ix_scene_organized"), table_name="scene")
    op.drop_index(op.f("ix_scene_last_synced"), table_name="scene")
    op.drop_index(op.f("ix_scene_id"), table_name="scene")
    op.drop_index(op.f("ix_scene_created_at"), table_name="scene")
    op.drop_index("idx_scene_sync_status", table_name="scene")
    op.drop_index("idx_scene_studio_date", table_name="scene")
    op.drop_index("idx_scene_organized_date", table_name="scene")
    op.drop_table("scene")

    # Drop remaining tables
    op.drop_index(op.f("ix_tag_updated_at"), table_name="tag")
    op.drop_index(op.f("ix_tag_name"), table_name="tag")
    op.drop_index(op.f("ix_tag_last_synced"), table_name="tag")
    op.drop_index(op.f("ix_tag_id"), table_name="tag")
    op.drop_index(op.f("ix_tag_created_at"), table_name="tag")
    op.drop_index("idx_tag_name_lower", table_name="tag")
    op.drop_table("tag")

    op.drop_index(op.f("ix_setting_updated_at"), table_name="setting")
    op.drop_index(op.f("ix_setting_key"), table_name="setting")
    op.drop_index(op.f("ix_setting_created_at"), table_name="setting")
    op.drop_table("setting")

    op.drop_index(op.f("ix_scheduled_task_updated_at"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_task_type"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_next_run"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_name"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_last_run"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_id"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_enabled"), table_name="scheduled_task")
    op.drop_index(op.f("ix_scheduled_task_created_at"), table_name="scheduled_task")
    op.drop_index("idx_scheduled_task_type_enabled", table_name="scheduled_task")
    op.drop_index("idx_scheduled_task_enabled_next", table_name="scheduled_task")
    op.drop_table("scheduled_task")

    op.drop_index(op.f("ix_performer_updated_at"), table_name="performer")
    op.drop_index(op.f("ix_performer_name"), table_name="performer")
    op.drop_index(op.f("ix_performer_last_synced"), table_name="performer")
    op.drop_index(op.f("ix_performer_id"), table_name="performer")
    op.drop_index(op.f("ix_performer_created_at"), table_name="performer")
    op.drop_index("idx_performer_name_lower", table_name="performer")
    op.drop_table("performer")

    op.drop_index(op.f("ix_job_updated_at"), table_name="job")
    op.drop_index(op.f("ix_job_type"), table_name="job")
    op.drop_index(op.f("ix_job_status"), table_name="job")
    op.drop_index(op.f("ix_job_started_at"), table_name="job")
    op.drop_index(op.f("ix_job_id"), table_name="job")
    op.drop_index(op.f("ix_job_created_at"), table_name="job")
    op.drop_index(op.f("ix_job_completed_at"), table_name="job")
    op.drop_index("idx_job_type_status", table_name="job")
    op.drop_index("idx_job_status_created", table_name="job")
    op.drop_index("idx_job_completed", table_name="job")
    op.drop_table("job")

    op.drop_index(op.f("ix_analysis_plan_updated_at"), table_name="analysis_plan")
    op.drop_index(op.f("ix_analysis_plan_status"), table_name="analysis_plan")
    op.drop_index(op.f("ix_analysis_plan_name"), table_name="analysis_plan")
    op.drop_index(op.f("ix_analysis_plan_id"), table_name="analysis_plan")
    op.drop_index(op.f("ix_analysis_plan_created_at"), table_name="analysis_plan")
    op.drop_index(op.f("ix_analysis_plan_applied_at"), table_name="analysis_plan")
    op.drop_index("idx_plan_status_created", table_name="analysis_plan")
    op.drop_index("idx_plan_status_applied", table_name="analysis_plan")
    op.drop_table("analysis_plan")

    op.drop_index(op.f("ix_studio_updated_at"), table_name="studio")
    op.drop_index(op.f("ix_studio_name"), table_name="studio")
    op.drop_index(op.f("ix_studio_last_synced"), table_name="studio")
    op.drop_index(op.f("ix_studio_id"), table_name="studio")
    op.drop_index(op.f("ix_studio_created_at"), table_name="studio")
    op.drop_index("idx_studio_name_lower", table_name="studio")
    op.drop_table("studio")
