"""Alembic environment configuration."""

import logging
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Set up detailed logging for migrations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic.env")

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Import your models and database configuration
from app.core.config import get_settings  # noqa: E402
from app.core.database import Base  # noqa: E402

# Import all models to ensure they're registered
from app.models import (  # noqa: E402, F401
    AnalysisPlan,
    BaseModel,
    ChangeAction,
    Job,
    JobStatus,
    JobType,
    Performer,
    PlanChange,
    PlanStatus,
    Scene,
    SceneMarker,
    ScheduledTask,
    Setting,
    Studio,
    SyncHistory,
    Tag,
    scene_marker_tags,
    scene_performer,
    scene_tag,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get settings
settings = get_settings()

# Set the database URL from settings
config.set_main_option("sqlalchemy.url", settings.database.url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Running migrations in online mode")
    logger.info(f"Database URL: {config.get_main_option('sqlalchemy.url')}")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        logger.info("Connected to database")
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            logger.info("Starting migration transaction")
            try:
                context.run_migrations()
                logger.info("Migration transaction completed successfully")
            except Exception as e:
                logger.error(f"Migration failed during execution: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                if hasattr(e, "orig"):
                    logger.error(f"Original error: {e.orig}")
                raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
