"""Database utility functions."""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, sync_engine, async_engine
from app.models import (
    Setting, ScheduledTask, JobType
)

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    This function should be called on application startup to ensure
    all tables exist.
    """
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data! Use only in development.
    """
    settings = get_settings()
    if settings.app.environment == "production":
        raise RuntimeError("Cannot drop database in production environment")
        
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=sync_engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
        raise


def seed_db(db: Session) -> None:
    """
    Seed database with initial data.
    
    Args:
        db: Database session
    """
    try:
        logger.info("Seeding database...")
        
        # Add default settings
        default_settings = [
            {
                "key": "sync.batch_size",
                "value": 100,
                "description": "Number of items to sync in each batch"
            },
            {
                "key": "sync.timeout",
                "value": 300,
                "description": "Sync timeout in seconds"
            },
            {
                "key": "analysis.confidence_threshold",
                "value": 0.8,
                "description": "Minimum confidence score for automatic changes"
            },
            {
                "key": "analysis.max_scenes_per_plan",
                "value": 1000,
                "description": "Maximum number of scenes per analysis plan"
            },
        ]
        
        for setting_data in default_settings:
            existing = db.query(Setting).filter_by(key=setting_data["key"]).first()
            if not existing:
                setting = Setting(**setting_data)
                db.add(setting)
                logger.info(f"Added setting: {setting_data['key']}")
        
        # Add default scheduled tasks
        default_tasks = [
            {
                "name": "Daily Sync",
                "task_type": JobType.SYNC,
                "schedule": "0 2 * * *",  # 2 AM daily
                "config": {
                    "sync_performers": True,
                    "sync_tags": True,
                    "sync_studios": True,
                    "sync_scenes": True
                },
                "enabled": False,
                "description": "Daily synchronization with Stash"
            },
            {
                "name": "Weekly Analysis",
                "task_type": JobType.ANALYSIS,
                "schedule": "0 3 * * 0",  # 3 AM on Sundays
                "config": {
                    "analyze_unorganized": True,
                    "max_scenes": 500
                },
                "enabled": False,
                "description": "Weekly AI analysis of unorganized scenes"
            },
        ]
        
        for task_data in default_tasks:
            existing = db.query(ScheduledTask).filter_by(name=task_data["name"]).first()
            if not existing:
                task = ScheduledTask(
                    name=task_data["name"],
                    task_type=task_data["task_type"],
                    schedule=task_data["schedule"],
                    config=task_data["config"],
                    enabled=task_data["enabled"]
                )
                task.update_next_run()
                db.add(task)
                logger.info(f"Added scheduled task: {task_data['name']}")
        
        db.commit()
        logger.info("Database seeded successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed database: {e}")
        raise


def check_db_health() -> dict:
    """
    Check database health and connection.
    
    Returns:
        Dictionary with health check results
    """
    health = {
        "connected": False,
        "tables_exist": False,
        "version": None,
        "error": None
    }
    
    try:
        # Check connection
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            health["connected"] = result.scalar() == 1
            
            # Check if tables exist
            inspector = conn.dialect.get_inspector(conn)
            tables = inspector.get_table_names()
            expected_tables = [
                "scene", "performer", "tag", "studio",
                "scene_performer", "scene_tag",
                "analysis_plan", "plan_change",
                "job", "setting", "scheduled_task"
            ]
            health["tables_exist"] = all(table in tables for table in expected_tables)
            health["existing_tables"] = tables
            
            # Get alembic version if available
            if "alembic_version" in tables:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.first()
                if row:
                    health["version"] = row[0]
                    
    except Exception as e:
        health["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
        
    return health


def reset_db(db: Session) -> None:
    """
    Reset database to initial state.
    
    This drops all tables, recreates them, and seeds initial data.
    
    Args:
        db: Database session
    """
    settings = get_settings()
    if settings.app.environment == "production":
        raise RuntimeError("Cannot reset database in production environment")
        
    logger.warning("Resetting database...")
    drop_db()
    init_db()
    seed_db(db)
    logger.info("Database reset complete")