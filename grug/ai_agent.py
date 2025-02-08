from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres import AsyncPostgresStore
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from grug.ai_tools import all_ai_tools
from grug.settings import settings


@asynccontextmanager
async def get_react_agent() -> AsyncGenerator[CompiledGraph, Any]:
    # Create the db schema for the scheduler
    async with await AsyncConnection.connect(settings.postgres_dsn.replace("+psycopg", "")) as conn:
        await conn.execute("CREATE SCHEMA IF NOT EXISTS genai")

    # Create a connection pool to the Postgres database for the GenAI agents to use
    async with AsyncConnectionPool(
        conninfo=settings.postgres_dsn.replace("+psycopg", ""),
        max_size=20,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "options": "-c search_path=genai",
        },
    ) as pool:
        # Configure `store` and `checkpointer` for long-term and short-term memory
        # (Ref: https://langchain-ai.github.io/langgraphjs/concepts/memory/#what-is-memory)
        store = AsyncPostgresStore(pool)
        await store.setup()
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        yield create_react_agent(
            model=ChatOpenAI(
                model_name=settings.ai_openai_model,
                temperature=0,
                max_tokens=None,
                max_retries=2,
                openai_api_key=settings.openai_api_key,
            ),
            tools=all_ai_tools,
            checkpointer=checkpointer,
            store=store,
            state_modifier=settings.ai_base_instructions,
        )
