"""Discord bot interface for the Grug assistant server."""

import asyncio
from collections import deque
from typing import Deque

import discord
import orjson
from discord import Member, VoiceState
from discord.ext import voice_recv
from discord.ext.voice_recv import VoiceRecvClient
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.graph import CompiledGraph
from loguru import logger
from tembo_pgmq_python.async_queue import PGMQueue

from grug.discord_client.voice_utils import SpeechRecognitionSink
from grug.settings import settings


class DiscordVoiceClient:
    """Discord voice client for the Grug assistant server."""

    def __init__(self, discord_client: discord.Client, react_agent: CompiledGraph):
        self.discord_client = discord_client
        self.react_agent = react_agent
        self._should_respond_llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            openai_api_key=settings.openai_api_key,
        )

        # Initialize the background voice responder tasks set to keep track of running tasks
        self.background_voice_responder_tasks: set = set()

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
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
            if self.discord_client.user not in after.channel.members:
                logger.info(f"Connecting to {after.channel.name}")
                voice_channel = await after.channel.connect(cls=voice_recv.VoiceRecvClient)
                voice_channel.listen(SpeechRecognitionSink(discord_channel=after.channel))

                # Start the voice responder agent
                voice_responder_task = asyncio.create_task(self.voice_responder_task(voice_channel))
                self.background_voice_responder_tasks.add(voice_responder_task)
                voice_responder_task.add_done_callback(self.background_voice_responder_tasks.discard)

        # If the user left the bot voice channel
        elif before.channel.id == bot_voice_channel_id and before.channel is not None:
            logger.info(f"{member.display_name} left {before.channel.name}")

            # If there are no members in the voice channel and the bot is in the voice channel, disconnect from
            # the voice channel
            if len(before.channel.members) <= 1 and self.discord_client.user in before.channel.members:
                logger.info(f"No members in {before.channel.name}, disconnecting...")
                voice_channel = next(
                    (vc for vc in self.discord_client.voice_clients if vc.channel == before.channel), None
                )
                await voice_channel.disconnect(force=True)

    async def voice_responder_task(self, voice_channel: VoiceRecvClient):
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
