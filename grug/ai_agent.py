from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres import AsyncPostgresStore

from grug.ai_tools import all_ai_tools
from grug.db import get_genai_psycopg_async_pool
from grug.settings import settings


@asynccontextmanager
async def get_react_agent() -> AsyncGenerator[CompiledGraph, Any]:
    conn_pool = await get_genai_psycopg_async_pool()
    await conn_pool.open()

    # Create the db schema for the scheduler
    async with conn_pool.connection() as conn:
        await conn.execute("CREATE SCHEMA IF NOT EXISTS genai")

    # Configure `store` and `checkpointer` for long-term and short-term memory
    # (Ref: https://langchain-ai.github.io/langgraphjs/concepts/memory/#what-is-memory)
    store = AsyncPostgresStore(conn_pool)
    await store.setup()
    checkpointer = AsyncPostgresSaver(conn_pool)
    await checkpointer.setup()

    try:
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

    finally:
        # Close the connection pool after the context manager exits
        await conn_pool.close()
