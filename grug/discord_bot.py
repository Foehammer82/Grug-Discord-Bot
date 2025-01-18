"""Discord bot interface for the Grug assistant server."""

import discord
import discord.utils
from discord import app_commands
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres import AsyncPostgresStore
from loguru import logger

from grug.ai_tools import all_ai_tools
from grug.settings import settings
from grug.utils import InterceptLogHandler, get_interaction_response

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


class Client(discord.Client):
    ai_agent: CompiledGraph = None

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


discord_client = Client()
discord.utils.setup_logging(handler=InterceptLogHandler())


# Command Error Handling
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    return await get_interaction_response(interaction).send_message(
        content=str(error),
        ephemeral=True,
    )


discord_client.tree.on_error = on_tree_error


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

    if discord_client.ai_agent is None:
        raise ValueError("ai_app not initialized in the Discord bot.")

    logger.info(f"Logged in as {discord_client.user} (ID: {discord_client.user.id})")
    logger.info(f"Discord bot invite URL: {get_bot_invite_url()}")

    # TODO: Make sure all the guilds are loaded in the server (see old code)
    # TODO: Add persistent views to the discord bot (see old code)


@discord_client.event
async def on_message(message: discord.Message):
    """on_message event handler for the Discord bot."""

    # TODO: working on figuring out how to pass all conversation history to the AI's memory so it can reference it
    # TODO: when in group chats, have it check using a smaller model to see if it should respond to the current
    #       conversation.

    # ignore messages from self and all bots
    if message.author == discord_client.user or message.author.bot:
        return

    # Message is @mention or DM
    elif isinstance(message.channel, discord.DMChannel) or (
        (isinstance(message.channel, discord.TextChannel) or isinstance(message.channel, discord.Thread))
        and discord_client.user in message.mentions
    ):

        final_state = await discord_client.ai_agent.ainvoke(
            {"messages": [HumanMessage(content=message.content)]},
            config={
                "configurable": {
                    "thread_id": str(message.channel.id),
                    "user_id": f"{str(message.guild.id) + '-' if message.guild else ''}{message.author.id}",
                }
            },
        )

        await message.channel.send(final_state["messages"][-1].content)
        # TODO: don't forget to also send the response messages to the chat history.  might be good to set a TTL on the
        #       overall history so it doesn't get too big.

    # TODO: send chat messages to DB and build tools that can look back at chat history to to get summaries of what
    #       was talked about


async def start_discord_bot():
    async with AsyncPostgresStore.from_conn_string(settings.postgres_dsn.replace("+psycopg", "")) as store:
        await store.setup()

        async with AsyncPostgresSaver.from_conn_string(settings.postgres_dsn.replace("+psycopg", "")) as checkpointer:
            await checkpointer.setup()

            discord_client.ai_agent = create_react_agent(
                model=ChatOpenAI(
                    model=settings.ai_openai_model,
                    temperature=0,
                    max_tokens=None,
                    timeout=None,
                    max_retries=2,
                    api_key=settings.openai_api_key.get_secret_value(),
                ),
                tools=all_ai_tools,
                checkpointer=checkpointer,
                store=store,
                state_modifier=settings.ai_base_instructions,
            )

            await discord_client.start(settings.discord_token.get_secret_value())
