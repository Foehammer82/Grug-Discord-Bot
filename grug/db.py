"""Database setup and initialization."""

import asyncio
import subprocess  # nosec B404
import sys

from loguru import logger
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from grug.settings import settings

# Set the event loop policy for Windows
# NOTE: https://youtrack.jetbrains.com/issue/PY-57667/Asyncio-support-for-the-debugger-EXPERIMENTAL-FEATURE
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Database engine singleton
sqa_async_engine = create_async_engine(
    url=settings.postgres_dsn,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
)

# Database session factory singleton
sqa_async_session_factory = async_sessionmaker(bind=sqa_async_engine, class_=AsyncSession, expire_on_commit=False)

# psycopg connection pool singleton
_genai_psycopg_async_pool: AsyncConnectionPool | None = None


async def get_genai_psycopg_async_pool() -> AsyncConnectionPool:
    global _genai_psycopg_async_pool

    if _genai_psycopg_async_pool is None:
        _genai_psycopg_async_pool = AsyncConnectionPool(
            conninfo=settings.postgres_dsn.replace("+psycopg", ""),
            open=False,
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
                "options": "-c search_path=genai",
            },
        )

    return _genai_psycopg_async_pool


def init_db():
    # Run the Alembic migrations
    result = subprocess.run(  # nosec B607, B603
        ["alembic", "upgrade", "head"],
        cwd=settings.root_dir.absolute(),
        capture_output=True,
        text=True,
    )
    logger.info(result.stdout)
    logger.info(result.stderr)
    logger.info("Database initialized [alembic upgrade head].")
