"""Discord bot interface for the Grug assistant server."""

import asyncio
import logging
from collections import deque
from typing import Deque

import discord.utils
import orjson
from discord.ext import voice_recv
from discord.ext.voice_recv import VoiceRecvClient
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.graph import CompiledGraph
from loguru import logger
from tembo_pgmq_python.async_queue import PGMQueue

from grug.ai_agents.base_react_agent import get_react_agent
from grug.discord_speech_recognition import SpeechRecognitionSink
from grug.settings import settings


class DiscordClient(discord.Client):
    react_agent: CompiledGraph | None = None

    def __init__(self):
        # Define Discord Intents required for the bot session
        intents = discord.Intents.default()
        intents.members = True  # TODO: link to justification for intent

        # Initialize the background voice responder tasks set to keep track of running tasks
        self.background_voice_responder_tasks: set = set()

        super().__init__(intents=intents)
        discord.utils.setup_logging(handler=InterceptLogHandler())

    def get_bot_invite_url(self) -> str | None:
        return (
            f"https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot"
            if self.user
            else None
        )

    async def on_ready(self):
        """
        Event handler for when the bot is ready.

        Documentation: https://discordpy.readthedocs.io/en/stable/api.html#discord.on_ready
        """
        if not self.react_agent:
            raise ValueError("ReAct agent not Initialized")

        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Discord bot invite URL: {self.get_bot_invite_url()}")

    async def on_message(
        self,
        message: discord.Message,
    ):
        """on_message event handler for the Discord bot."""
        if not self.react_agent:
            raise ValueError("ReAct agent not Initialized!")

        # TODO: make a tool that can search chat history for a given channel

        # ignore messages from self and all bots
        if message.author == self.user or message.author.bot:
            return

        channel_is_text_or_thread = isinstance(message.channel, discord.TextChannel) or isinstance(
            message.channel, discord.Thread
        )

        # get the agent config based on the current message
        agent_config = {
            "configurable": {
                "thread_id": str(message.channel.id),
                "user_id": f"{str(message.guild.id) + '-' if message.guild else ''}{message.author.id}",
            }
        }

        # Respond if message is @mention or DM or should_respond is True
        is_direct_message = isinstance(message.channel, discord.DMChannel)
        is_at_message = channel_is_text_or_thread and self.user in message.mentions
        if is_direct_message or is_at_message:
            async with message.channel.typing():
                messages: list[BaseMessage] = []

                # Handle replies
                if message_replied_to := message.reference.resolved.content if message.reference else None:
                    messages.append(
                        SystemMessage(
                            f'You previously sent the following message: "{message_replied_to}", assume that that '
                            "you are responding to a reply to that message."
                        )
                    )

                # Add the message that the user sent
                messages.append(HumanMessage(message.content))

                final_state = await self.react_agent.ainvoke(
                    input={"messages": messages},
                    config=agent_config,
                )

                await message.channel.send(
                    content=final_state["messages"][-1].content,
                    reference=message if channel_is_text_or_thread else None,
                )

        # Otherwise, add the message to the conversation history without requesting a response
        else:
            await self.react_agent.aupdate_state(
                config=agent_config,
                values={"messages": [HumanMessage(message.content)]},
            )

    if settings.discord_enable_voice_client:

        async def on_voice_state_update(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState,
        ):
            # TODO: store this in the DB so that it can be configured for each server
            bot_voice_channel_id = 1049728769541283883

            # Ignore bot users
            if member.bot:
                return

            # TODO: make sure to send a message to all users that join a bot voice channel what the bot is doing and
            #       how their data is being handled

            # If the user joined the bot voice channel
            if after.channel is not None and after.channel.id == bot_voice_channel_id and before.channel is None:
                logger.info(f"{member.display_name} joined {after.channel.name}")

                # If the bot is not currently in the voice channel, connect to the voice channel
                if self.user not in after.channel.members:
                    logger.info(f"Connecting to {after.channel.name}")
                    voice_channel = await after.channel.connect(cls=voice_recv.VoiceRecvClient)
                    voice_channel.listen(SpeechRecognitionSink(discord_channel=after.channel))

                    # Start the voice responder agent
                    voice_responder_task = asyncio.create_task(self._listen_to_voice_channel(voice_channel))
                    self.background_voice_responder_tasks.add(voice_responder_task)
                    voice_responder_task.add_done_callback(self.background_voice_responder_tasks.discard)

            # If the user left the bot voice channel
            elif before.channel.id == bot_voice_channel_id and before.channel is not None:
                logger.info(f"{member.display_name} left {before.channel.name}")

                # If there are no members in the voice channel and the bot is in the voice channel, disconnect from
                # the voice channel
                if len(before.channel.members) <= 1 and self.user in before.channel.members:
                    logger.info(f"No members in {before.channel.name}, disconnecting...")
                    voice_channel = next((vc for vc in self.voice_clients if vc.channel == before.channel), None)
                    await voice_channel.disconnect(force=True)

    async def _listen_to_voice_channel(self, voice_channel: VoiceRecvClient):
        """A looping task that listens for messages in a voice channel and responds to them."""
        queue = PGMQueue(
            host=settings.postgres_host,
            port=settings.postgres_port,
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            database=settings.postgres_db,
        )

        await queue.init()

        message_buffer: Deque = deque(maxlen=100)

        while voice_channel.is_connected():
            if not self.react_agent:
                raise ValueError("ReAct agent not Initialized!")

            for message in await queue.read_with_poll(
                queue=str(voice_channel.channel.id),
                vt=30,
                qty=5,
                max_poll_seconds=5,
                poll_interval_ms=100,
            ):
                # Append the message to the current buffer
                message_buffer.append(message.message)

                # Delete the message from the queue
                await queue.delete(str(voice_channel.channel.id), message.msg_id)

                # TODO: only respond if someone calls grug by name (or whatever the bot's name is)
                # TODO: don't respond if someone is currently talking, or consider how to handle when/how grug should
                #       respond.  at the very least, there should be a wait for a pause from whoever initiated the
                #       grug response

                # Respond to the message
                final_state = await self.react_agent.ainvoke(
                    {
                        "messages": [
                            SystemMessage(
                                content=(
                                    "The following is a list of messages that have been spoken in voice chat, remember that the speach "
                                    "to text is not perfect, so there may be some errors in the text.  Do you best to assume what the "
                                    "users meant to say, but DO NOT try to make sense of gibberish.  This list will be in json, each item "
                                    "in the list will be a dict containing the `user_id`, `message_timestamp`, and `message`."
                                    "Respond accordingly."
                                )
                            ),
                            HumanMessage(content=orjson.dumps(list(message_buffer)).decode()),
                        ]
                    },
                    config={
                        "configurable": {
                            "thread_id": str(voice_channel.channel.id),
                            "user_id": f"{str(voice_channel.guild.id)}-{message.message["user_id"]}",
                        }
                    },
                )

                await voice_channel.channel.send(content=final_state["messages"][-1].content)

        logger.info(f"Voice channel {voice_channel.channel.name} disconnected, stopping voice responder...")

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        """Start the Discord bot."""
        if not settings.discord_token:
            raise ValueError("Discord bot token not set!")

        async with get_react_agent() as self.react_agent:
            try:
                await self.login(token)
                await self.connect(reconnect=reconnect)
            finally:
                # Disconnect from all voice channels
                logger.info("Disconnecting from all voice channels...")
                for vc in self.voice_clients:
                    await vc.disconnect(force=True)

                # Close the Discord client
                logger.info("Closing the Discord client...")
                await self.close()


class InterceptLogHandler(logging.Handler):
    """
    Default log handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord):
        """Intercept standard logging records."""
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            if frame.f_back:
                frame = frame.f_back
                depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
