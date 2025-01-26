"""Discord bot interface for the Grug assistant server."""

import discord.utils
from loguru import logger

from grug.ai_agents.base_react_agent import get_react_agent
from grug.discord_client.message_handler import DiscordMessageClient
from grug.discord_client.voice_handler import DiscordVoiceClient
from grug.settings import settings
from grug.utils import InterceptLogHandler

# TODO: move these explanations to the docs and update the below comments to link to those docs
# Why the `members` intent is necessary for the Grug Discord bot:
#
# The `members` intent in a Discord bot is used to receive events and information about guild members. This includes
# receiving updates about members joining, leaving, or updating their presence or profile in the guilds (servers) the
# bot is part of. Specifically, for the Grug app, the `members` intent is necessary for several reasons:
#
# 1. **Initializing Guild Members**: When the bot starts and loads guilds, it initializes guild members by creating
# Discord accounts for them in the Grug database. This process requires access to the list of members in each guild.
# 2. **Attendance Tracking**: The bot tracks attendance for events. To do this effectively, it needs to know about all
# members in the guild, especially to send reminders or updates about events.
# 3. **Food Scheduling**: Similar to attendance tracking, food scheduling involves assigning and reminding members about
# their responsibilities. The bot needs to know who the members are to manage this feature.
# 4. **User Account Management**: The bot manages user accounts, including adding new users when they join the guild and
# updating user information. The `members` intent allows the bot to receive events related to these activities.
#
# Without the `members` intent, the bot would not be able to access detailed information about guild members, which
# would significantly limit its functionality related to user and event management.

# TODO: write out why the message_content intent is required (it's needed for the bot to make contextual responses)


discord_client = discord.Client(intents=discord.Intents.all())
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
