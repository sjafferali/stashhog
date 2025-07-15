"""Add metadata column to job table and update job types

Revision ID: 002
Revises: 001
Create Date: 2025-07-15

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata column to job table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('job')]
    
    if 'metadata' not in columns:
        op.add_column(
            "job",
            sa.Column("metadata", sa.JSON(), nullable=True, default=dict),
        )
    else:
        print("Column 'metadata' already exists in 'job' table, skipping...")

    # For PostgreSQL, we need to handle enum updates differently
    if conn.dialect.name == 'postgresql':
        # Check existing enum values
        result = conn.execute(
            sa.text(
                "SELECT enumlabel FROM pg_enum "
                "WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'jobtype')"
            )
        )
        existing_values = {row[0] for row in result}
        
        # Values to add
        new_values = ['sync', 'sync_all', 'sync_scenes', 'sync_performers', 
                      'sync_tags', 'sync_studios', 'generate_details']
        
        # Add only missing values
        for value in new_values:
            if value not in existing_values:
                # Use raw SQL with proper transaction handling
                conn.execute(sa.text(f"COMMIT"))  # Commit current transaction
                conn.execute(sa.text(f"ALTER TYPE jobtype ADD VALUE '{value}'"))
    else:
        # For other databases, just log a warning
        print("Non-PostgreSQL database detected, skipping enum updates")


def downgrade() -> None:
    # Remove metadata column from job table
    op.drop_column("job", "metadata")

    # Note: PostgreSQL doesn't support removing values from enums
    # The enum values will remain but won't be used
