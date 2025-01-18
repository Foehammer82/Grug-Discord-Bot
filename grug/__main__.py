import anyio
from loguru import logger

from grug.db import init_db
from grug.discord_bot import start_discord_bot
from grug.scheduler import start_scheduler
from grug.settings import settings


# noinspection PyTypeChecker
async def main():
    """Main application entrypoint."""
    if not settings.discord_token:
        raise ValueError("`DISCORD_TOKEN` env variable is required to run the Grug bot.")
    if not settings.openai_api_key:
        raise ValueError("`OPENAI_API_KEY` env variable is required to run the Grug bot.")

    logger.info("Starting Grug...")

    init_db()

    async with anyio.create_task_group() as tg:
        tg.start_soon(start_discord_bot)
        tg.start_soon(start_scheduler)

    logger.info("Grug has shut down...")


if __name__ == "__main__":
    anyio.run(main)
