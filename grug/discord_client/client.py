"""Discord bot interface for the Grug assistant server."""

import discord.utils
from loguru import logger

from grug.ai_agents.base_react_agent import get_react_agent
from grug.discord_client.message_handler import DiscordMessageClient
from grug.discord_client.voice_handler import DiscordVoiceClient
from grug.settings import settings
from grug.utils import InterceptLogHandler


def get_discord_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.members = True
    return intents


discord_client = discord.Client(intents=get_discord_intents())
discord.utils.setup_logging(handler=InterceptLogHandler())


def get_bot_invite_url() -> str | None:
    return (
        f"https://discord.com/api/oauth2/authorize?client_id={discord_client.user.id}&permissions=8&scope=bot"
        if discord_client.user
        else None
    )


@discord_client.event
async def on_ready():
    """
    Event handler for when the bot is ready.

    Documentation: https://discordpy.readthedocs.io/en/stable/api.html#discord.on_ready
    """

    logger.info(f"Logged in as {discord_client.user} (ID: {discord_client.user.id})")
    logger.info(f"Discord bot invite URL: {get_bot_invite_url()}")


async def start_discord_bot(
    enable_voice_client: bool = True,
):
    if not settings.discord_token:
        raise ValueError("`DISCORD_TOKEN` env variable is required to run the Grug bot.")

    """Start the Discord bot."""
    async with get_react_agent() as react_agent:
        DiscordMessageClient(discord_client, react_agent)

        if enable_voice_client:
            DiscordVoiceClient(discord_client, react_agent)

        try:
            await discord_client.start(settings.discord_token.get_secret_value())
        finally:
            # Disconnect from all voice channels
            logger.info("Disconnecting from all voice channels...")
            for vc in discord_client.voice_clients:
                await vc.disconnect(force=True)

            # Close the Discord client
            logger.info("Closing the Discord client...")
            await discord_client.close()
