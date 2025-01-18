"""Database setup and initialization."""

import asyncio
import subprocess  # nosec B404
import sys

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from grug.settings import settings

# Set the event loop policy for Windows
# NOTE: https://youtrack.jetbrains.com/issue/PY-57667/Asyncio-support-for-the-debugger-EXPERIMENTAL-FEATURE
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Database engine singleton
async_engine = create_async_engine(
    url=settings.postgres_dsn,
    echo=False,
    future=True,
)

# Database session factory singleton
get_async_session = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


def init_db():
    # Run the Alembic migrations
    result = subprocess.run(  # nosec B607, B603
        ["alembic", "upgrade", "head"],
        cwd=settings.root_dir.as_posix(),
        capture_output=True,
        text=True,
    )
    logger.info(result.stdout)
    logger.error(result.stderr)

    logger.info("Database initialized [alembic upgrade head].")
