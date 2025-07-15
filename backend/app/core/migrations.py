"""
Database migration utilities.

This module handles automatic database migrations using Alembic.
All database schema changes should be managed through migrations,
not through SQLAlchemy's create_all() method.

To create a new migration:
1. Make changes to your models
2. Run: alembic revision --autogenerate -m "Description of changes"
3. Review and edit the generated migration file
4. The migration will run automatically on app startup
"""

import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _find_alembic_config() -> Path:
    """Find alembic.ini file in common locations."""
    possible_paths = [
        Path(__file__).parent.parent.parent / "alembic.ini",  # backend/alembic.ini
        Path("/app/alembic.ini"),  # Docker container path
        Path("alembic.ini"),  # Current directory
    ]

    for path in possible_paths:
        if path.exists():
            return path

    logger.error(f"alembic.ini not found in any of: {[str(p) for p in possible_paths]}")
    raise FileNotFoundError("alembic.ini not found")


def _setup_alembic_config(alembic_ini_path: Path, database_url: str) -> Config:
    """Setup Alembic configuration with correct paths and database URL."""
    alembic_cfg = Config(str(alembic_ini_path))

    # Set the script location to be relative to the ini file
    alembic_dir = alembic_ini_path.parent / "alembic"
    if not alembic_dir.exists():
        # Try absolute path in Docker container
        alembic_dir = Path("/app/alembic")

    if not alembic_dir.exists():
        logger.error(f"Alembic directory not found at {alembic_dir}")
        raise FileNotFoundError("Alembic directory not found")

    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    return alembic_cfg


def _ensure_alembic_version_table(engine: Engine) -> None:
    """Ensure alembic_version table exists."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "alembic_version" not in tables:
        logger.info("Creating alembic_version table...")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """
                )
            )


def _check_migrations_needed(engine: Engine, alembic_cfg: Config) -> bool:
    """Check if migrations are needed."""
    script_dir = ScriptDirectory.from_config(alembic_cfg)

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        head_rev = script_dir.get_current_head()

        if current_rev == head_rev:
            logger.info(f"Database is already up to date at revision: {current_rev}")
            return False

        logger.info(f"Current revision: {current_rev or 'None (fresh database)'}")
        logger.info(f"Latest revision: {head_rev}")

        # List pending migrations
        pending_revisions = []
        for revision in script_dir.walk_revisions():
            if revision.revision == current_rev:
                break
            pending_revisions.append(revision.revision)

        if pending_revisions:
            logger.info(f"Pending migrations: {', '.join(reversed(pending_revisions))}")

    return True


def run_migrations() -> None:
    """
    Run all pending database migrations.

    This function will:
    1. Check if the database is already initialized
    2. Create alembic_version table if it doesn't exist
    3. Run all pending migrations
    """
    settings = get_settings()

    logger.info("Running database migrations...")

    try:
        # Find and setup Alembic configuration
        alembic_ini_path = _find_alembic_config()
        alembic_cfg = _setup_alembic_config(alembic_ini_path, settings.database.url)

        # Create engine to check current state
        engine = create_engine(settings.database.url)

        # Ensure alembic_version table exists
        _ensure_alembic_version_table(engine)

        # Check if we're using SQLite and warn about potential limitations
        if settings.database.url.startswith("sqlite"):
            logger.warning(
                "Using SQLite database - some migrations may have limitations"
            )

        # Check if migrations are needed
        if not _check_migrations_needed(engine, alembic_cfg):
            return

        # Run migrations
        logger.info("Applying pending migrations...")
        try:
            # Set a statement timeout for PostgreSQL to prevent hanging
            if settings.database.url.startswith("postgresql"):
                with engine.begin() as conn:
                    conn.execute(text("SET statement_timeout = '300000'"))  # 5 minutes
                    logger.info("Set PostgreSQL statement timeout to 5 minutes")
            
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations completed successfully")
        except Exception as migration_error:
            logger.error(f"Migration failed with error: {migration_error}")
            logger.error(f"Error type: {type(migration_error).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def run_migrations_async() -> None:
    """
    Run migrations asynchronously.

    This is a wrapper around run_migrations() for use in async contexts.
    """
    # Migrations use sync SQLAlchemy, so we just call the sync function
    run_migrations()
