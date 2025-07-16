"""Rename date fields to use stash_ prefix for clarity

Revision ID: 008_rename_stash_date_fields
Revises: 007_add_rejected_column_to_plan_change
Create Date: 2025-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '008_rename_stash_date_fields'
down_revision = '007_add_rejected_column_to_plan_change'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename date fields and add stash_updated_at column"""
    # Get database dialect to handle SQLite vs PostgreSQL differences
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    
    # Check if we're using SQLite (which has limited ALTER TABLE support)
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # First, create a new table with the desired schema
        op.create_table(
            'scene_new',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('url', sa.String(), nullable=True),
            sa.Column('stash_created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('stash_updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('stash_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('rating', sa.Integer(), nullable=True),
            sa.Column('organized', sa.Boolean(), nullable=False),
            sa.Column('studio_id', sa.String(), nullable=True),
            sa.Column('paths', sa.JSON(), nullable=True),
            sa.Column('duration', sa.Float(), nullable=True),
            sa.Column('size', sa.Integer(), nullable=True),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('framerate', sa.Float(), nullable=True),
            sa.Column('bitrate', sa.Integer(), nullable=True),
            sa.Column('codec', sa.String(), nullable=True),
            sa.Column('last_synced', sa.DateTime(timezone=True), nullable=False),
            sa.Column('content_checksum', sa.String(), nullable=True),
            sa.Column('analyzed', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['studio_id'], ['studio.id'], ),
        )
        
        # Copy data from old table to new table
        op.execute('''
            INSERT INTO scene_new (
                id, created_at, updated_at, title, details, url,
                stash_created_at, stash_date, rating, organized, studio_id,
                paths, duration, size, width, height, framerate, bitrate, codec,
                last_synced, content_checksum, analyzed
            )
            SELECT 
                id, created_at, updated_at, title, details, url,
                created_date, scene_date, rating, organized, studio_id,
                paths, duration, size, width, height, framerate, bitrate, codec,
                last_synced, content_checksum, analyzed
            FROM scene
        ''')
        
        # Drop the old table
        op.drop_table('scene')
        
        # Rename the new table to the original name
        op.rename_table('scene_new', 'scene')
        
        # Recreate indexes
        op.create_index('idx_scene_organized_date', 'scene', ['organized', 'stash_date'])
        op.create_index('idx_scene_studio_date', 'scene', ['studio_id', 'stash_date'])
        op.create_index('idx_scene_sync_status', 'scene', ['last_synced', 'organized'])
        op.create_index('idx_scene_analyzed', 'scene', ['analyzed'])
        op.create_index('idx_scene_analyzed_organized', 'scene', ['analyzed', 'organized'])
        op.create_index('ix_scene_stash_date', 'scene', ['stash_date'])
        
    else:
        # PostgreSQL supports ALTER COLUMN
        # Rename columns
        op.alter_column('scene', 'created_date', new_column_name='stash_created_at')
        op.alter_column('scene', 'scene_date', new_column_name='stash_date')
        
        # Add new column
        op.add_column('scene',
            sa.Column('stash_updated_at', sa.DateTime(timezone=True), nullable=True)
        )
        
        # Update indexes
        op.drop_index('idx_scene_organized_date', 'scene')
        op.drop_index('idx_scene_studio_date', 'scene')
        op.drop_index('ix_scene_scene_date', 'scene')
        
        op.create_index('idx_scene_organized_date', 'scene', ['organized', 'stash_date'])
        op.create_index('idx_scene_studio_date', 'scene', ['studio_id', 'stash_date'])
        op.create_index('ix_scene_stash_date', 'scene', ['stash_date'])


def downgrade() -> None:
    """Revert field name changes"""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    
    if is_sqlite:
        # For SQLite, we need to recreate the table again
        op.create_table(
            'scene_new',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('url', sa.String(), nullable=True),
            sa.Column('created_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('scene_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('rating', sa.Integer(), nullable=True),
            sa.Column('organized', sa.Boolean(), nullable=False),
            sa.Column('studio_id', sa.String(), nullable=True),
            sa.Column('paths', sa.JSON(), nullable=True),
            sa.Column('duration', sa.Float(), nullable=True),
            sa.Column('size', sa.Integer(), nullable=True),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('framerate', sa.Float(), nullable=True),
            sa.Column('bitrate', sa.Integer(), nullable=True),
            sa.Column('codec', sa.String(), nullable=True),
            sa.Column('last_synced', sa.DateTime(timezone=True), nullable=False),
            sa.Column('content_checksum', sa.String(), nullable=True),
            sa.Column('analyzed', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['studio_id'], ['studio.id'], ),
        )
        
        # Copy data back
        op.execute('''
            INSERT INTO scene_new (
                id, created_at, updated_at, title, details, url,
                created_date, scene_date, rating, organized, studio_id,
                paths, duration, size, width, height, framerate, bitrate, codec,
                last_synced, content_checksum, analyzed
            )
            SELECT 
                id, created_at, updated_at, title, details, url,
                stash_created_at, stash_date, rating, organized, studio_id,
                paths, duration, size, width, height, framerate, bitrate, codec,
                last_synced, content_checksum, analyzed
            FROM scene
        ''')
        
        op.drop_table('scene')
        op.rename_table('scene_new', 'scene')
        
        # Recreate original indexes
        op.create_index('idx_scene_organized_date', 'scene', ['organized', 'scene_date'])
        op.create_index('idx_scene_studio_date', 'scene', ['studio_id', 'scene_date'])
        op.create_index('idx_scene_sync_status', 'scene', ['last_synced', 'organized'])
        op.create_index('idx_scene_analyzed', 'scene', ['analyzed'])
        op.create_index('idx_scene_analyzed_organized', 'scene', ['analyzed', 'organized'])
        op.create_index('ix_scene_scene_date', 'scene', ['scene_date'])
        
    else:
        # PostgreSQL
        # Drop new indexes
        op.drop_index('idx_scene_organized_date', 'scene')
        op.drop_index('idx_scene_studio_date', 'scene')
        op.drop_index('ix_scene_stash_date', 'scene')
        
        # Remove column
        op.drop_column('scene', 'stash_updated_at')
        
        # Rename columns back
        op.alter_column('scene', 'stash_created_at', new_column_name='created_date')
        op.alter_column('scene', 'stash_date', new_column_name='scene_date')
        
        # Recreate original indexes
        op.create_index('idx_scene_organized_date', 'scene', ['organized', 'scene_date'])
        op.create_index('idx_scene_studio_date', 'scene', ['studio_id', 'scene_date'])
        op.create_index('ix_scene_scene_date', 'scene', ['scene_date'])