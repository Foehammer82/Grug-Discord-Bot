"""
Discord voice client for handling voice channels and speech recognition.
"""

import array
import asyncio
import audioop
import concurrent.futures
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any, Awaitable, Deque, Final, Optional, TypedDict, TypeVar

import discord
import speech_recognition as sr
from discord import FFmpegPCMAudio
from discord.ext import voice_recv
from discord.ext.voice_recv import AudioSink, SilencePacket, VoiceData, VoiceRecvClient
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph.graph import CompiledGraph
from loguru import logger
from pydantic import BaseModel
from rapidfuzz import fuzz
from speech_recognition.recognizers.whisper_api import openai as sr_openai
from tembo_pgmq_python import async_queue
from tembo_pgmq_python import queue as sync_queue

from grug.settings import settings


class _RespondingTo(BaseModel):
    user_id: int
    last_message_timestamp: datetime


class _StreamData(TypedDict):
    stopper: Optional[Any]
    recognizer: sr.Recognizer
    buffer: array.array[int]


class _DiscordSRAudioSource(sr.AudioSource):
    little_endian: Final[bool] = True
    SAMPLE_RATE: Final[int] = 48_000
    SAMPLE_WIDTH: Final[int] = 2
    CHANNELS: Final[int] = 2
    CHUNK: Final[int] = 960

    # noinspection PyMissingConstructor
    def __init__(self, buffer: array.array[int], read_timeout: int = 10):
        self.read_timeout = read_timeout
        self.buffer = buffer
        self._entered: bool = False

    @property
    def stream(self):
        return self

    def __enter__(self):
        if self._entered:
            logger.warning("Already entered sr audio source")
        self._entered = True
        return self

    def __exit__(self, *exc) -> None:
        self._entered = False
        if any(exc):
            logger.exception("Error closing sr audio source")

    def read(self, size: int) -> bytes:
        for _ in range(self.read_timeout):
            if len(self.buffer) < size * self.CHANNELS:
                time.sleep(0.01)
            else:
                break
        else:
            if len(self.buffer) <= 100:
                return b""

        chunk_size = size * self.CHANNELS
        audio_chunk = self.buffer[:chunk_size].tobytes()
        del self.buffer[: min(chunk_size, len(audio_chunk))]
        audio_chunk = audioop.tomono(audio_chunk, 2, 1, 1)
        return audio_chunk

    def close(self) -> None:
        self.buffer.clear()


class _SpeechRecognitionSink(AudioSink):
    """
    Speech recognition sink for Discord voice channels.

    source: https://github.com/imayhaveborkedit/discord-ext-voice-recv/blob/main/discord/ext/voice_recv/extras/speechrecognition.py
    """

    _stream_data: defaultdict[int, _StreamData] = defaultdict(
        lambda: _StreamData(stopper=None, recognizer=sr.Recognizer(), buffer=array.array("B"))
    )

    def __init__(self, discord_channel: discord.VoiceChannel):
        super().__init__(None)
        self.discord_channel: discord.VoiceChannel = discord_channel

        self.queue = sync_queue.PGMQueue(
            host=settings.postgres_host,
            port=settings.postgres_port,
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            database=settings.postgres_db,
        )

        # Create a queue for the voice channel if it doesn't exist.
        if str(self.discord_channel.id) not in self.queue.list_queues():
            self.queue.create_queue(str(self.discord_channel.id))

    def _await(self, coro: Awaitable[TypeVar]) -> concurrent.futures.Future[TypeVar]:
        assert self.client is not None
        return asyncio.run_coroutine_threadsafe(coro, self.client.loop)

    def wants_opus(self) -> bool:
        return False

    def write(self, user: Optional[discord.User], data: VoiceData) -> None:
        # Ignore silence packets and packets from users we don't have data for
        if isinstance(data.packet, SilencePacket) or user is None:
            return

        sdata = self._stream_data[user.id]
        sdata["buffer"].extend(data.pcm)

        if not sdata["stopper"]:
            sdata["stopper"] = sdata["recognizer"].listen_in_background(
                source=_DiscordSRAudioSource(sdata["buffer"]),
                callback=self.background_listener(user),
                phrase_time_limit=10,
            )

    def background_listener(self, user: discord.User):
        def callback(_recognizer: sr.Recognizer, _audio: sr.AudioData):
            # Don't process empty audio data or audio data that is too small
            if _audio.frame_data == b"" or len(bytes(_audio.frame_data)) < 10000:
                return None

            # Get the text from the audio data
            text_output = None
            try:
                text_output = sr_openai.recognize(_recognizer, _audio)
            except sr.UnknownValueError:
                logger.debug("Bad speech chunk")

            # WEIRDEST BUG EVER: for some reason whisper keeps getting the word "you" from the recognizer, so
            #                    we'll just ignore any text segments that are just "you"
            if text_output and text_output.lower() != "you":
                self.queue.send(
                    str(self.discord_channel.id),
                    {
                        "user_id": user.id,
                        "message_timestamp": datetime.now(tz=UTC).isoformat(),
                        "message": text_output,
                    },
                )

        return callback

    def cleanup(self) -> None:
        for user_id in tuple(self._stream_data.keys()):
            self._drop(user_id)

    def _drop(self, user_id: int) -> None:
        if user_id in self._stream_data:
            data = self._stream_data.pop(user_id)
            stopper = data.get("stopper")
            if stopper:
                stopper()

            buffer = data.get("buffer")
            if buffer:
                # arrays don't have a clear function
                del buffer[:]


class DiscordVoiceClient:
    def __init__(self, discord_client: discord.Client, react_agent: CompiledGraph):
        if not react_agent:
            raise ValueError("ReAct agent not Initialized")

        self.discord_client = discord_client
        self.react_agent = react_agent

        # Initialize the background voice responder tasks set to keep track of running tasks
        self.background_voice_responder_tasks: set = set()

        # Register the on_voice_state_update event
        self.discord_client.event(self.on_voice_state_update)

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
            if self.discord_client.user not in after.channel.members:
                logger.info(f"Connecting to {after.channel.name}")
                voice_channel = await after.channel.connect(cls=voice_recv.VoiceRecvClient)
                voice_channel.listen(_SpeechRecognitionSink(discord_channel=after.channel))

                # Start the voice responder agent
                voice_responder_task = asyncio.create_task(self._listen_to_voice_channel(voice_channel))
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

    async def _listen_to_voice_channel(self, voice_channel: VoiceRecvClient):
        """A looping task that listens for messages in a voice channel and responds to them."""

        # Initialize the queue
        queue = async_queue.PGMQueue(
            host=settings.postgres_host,
            port=settings.postgres_port,
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            database=settings.postgres_db,
        )
        await queue.init()
        await queue.purge(str(voice_channel.channel.id))  # Start with a fresh queue when the bot joins

        while voice_channel.is_connected():
            if not self.react_agent:
                raise ValueError("ReAct agent not Initialized!")

            responding_to: Optional[_RespondingTo] = None
            message_buffer: Deque = deque(maxlen=100)
            poll_interval_seconds = 0.1
            end_of_statement_seconds = 1
            while True:
                # Read messages in batches off the queue
                for message in await queue.read_batch(
                    queue=str(voice_channel.channel.id),
                    vt=30,
                    batch_size=5,
                ):
                    # Delete the message from the queue
                    await queue.delete(str(voice_channel.channel.id), message.msg_id)

                    # if currently responding to a message, add the user messages to the buffer
                    if responding_to and message.message.get("user_id") == responding_to.user_id:
                        message_buffer.append(message.message.get("message"))

                    # Check if the bot was called by name
                    elif (
                        fuzz.partial_ratio(
                            s1=f"hey, {settings.ai_name.lower()}",
                            s2=message.message.get("message").lower(),
                        )
                        > 80
                    ):
                        # TODO: give indication the bot is thinking...
                        audio_source = FFmpegPCMAudio(
                            (settings.root_dir / "assets/sound_effects" / "boop.wav").as_posix()
                        )
                        voice_channel.play(audio_source)

                        logger.info(f"Bot was called by name by {message.message.get('user_id')}")
                        message_buffer.clear()
                        message_buffer.append(message.message.get("message"))
                        responding_to = _RespondingTo(
                            user_id=message.message.get("user_id"),
                            last_message_timestamp=message.enqueued_at,
                        )

                # Check to see if the bot should respond to its summons
                if (
                    responding_to
                    and (datetime.now(tz=UTC) - responding_to.last_message_timestamp).seconds > end_of_statement_seconds
                ):
                    # Respond to the message
                    final_state = await self.react_agent.ainvoke(
                        {
                            "messages": [
                                SystemMessage(
                                    content=(
                                        "- you are are responding to a message sent by a user in voice chat. \n"
                                        "- remember that the speach to text is not perfect, so there may be some errors in the text. \n"
                                        "- Do your best to assume what the users meant to say, but DO NOT try to make sense of gibberish. \n"
                                        "- If you are unsure what the user said, ask them to clarify. \n"
                                        "- DO NOT correct the user about your name or who you are, assume they misspoke and ignore it. \n"
                                    )
                                ),
                                HumanMessage(content=" ".join(list(message_buffer))),
                            ]
                        },
                        config={
                            "configurable": {
                                "thread_id": str(voice_channel.channel.id),
                                "user_id": f"{str(voice_channel.guild.id)}-{responding_to.user_id}",
                            }
                        },
                    )
                    await voice_channel.channel.send(content=final_state["messages"][-1].content)
                    logger.info(f"Responded to {responding_to.user_id} for request: {' '.join(list(message_buffer))}")

                    # Reset the responding_to object
                    responding_to = None

                # Wait for the poll interval
                await asyncio.sleep(poll_interval_seconds)

        logger.info(f"Voice channel {voice_channel.channel.name} disconnected, stopping voice responder...")
