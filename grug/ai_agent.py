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

# TODO: implement the consept of a "focus" where the agent uses it's focus as reference to how it answers questions.
#       For example, we will build Grug initially with a default focus on Pathfinder 2e, but we want to expand this to
#       more built in options, depending on how accessible certain tooling is.
#       Notes:
#        - have built in options for focus (first being pathfinder)
#        - user can set no focus, which will not connect to any out of the box source material except for what users
#          load into the RAG vector store.
#        - user can set custom focus (same as None, but giving a name to it, where users will still be expected to
#          provide their own material.
#        - might be neat to have the ability for users to provide API endpoints that grug can use for searching and use
#          swagger or something to define the API.


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

    # TODO: move these to be focus specific added when agent is called:
    #       - "When asked about tabletop RPGs, you should assume the party is playing pathfinder 2E."

    # TODO: this instruction should be added to the tool calls output or docstring:
    #       - "When providing information, you should try to reference or link to the source of the information."

    # Configure the base instructions for the AI agent
    base_instructions: str = "\n".join(
        [
            f"- your name is {settings.ai_name}.",
        ]
    )

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
            state_modifier=(
                f"# Primary Instructions:\n{base_instructions}\n\n"
                f"{'# Additional Instructions:\n' + settings.ai_instructions if settings.ai_instructions else ''}"
            ),
        )

    finally:
        # Close the connection pool after the context manager exits
        await conn_pool.close()
