import asyncio
import logging.config

# noinspection PyUnresolvedReferences
import alembic_postgresql_enum
from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic import context
from grug import models
from grug.db import sqa_async_engine
from grug.settings import settings

logging.config.fileConfig(context.config.config_file_name)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.postgres_dsn,
        target_metadata=models.SQLModel.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=models.SQLModel.metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

    # Create the vector extension if it doesn't exist
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print("Created vector extension")

    # create the PGMQ extension if it doesn't exist
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgmq"))
    print("Created pgmq extension")


async def run_migrations_online() -> None:
    async with sqa_async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await sqa_async_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
