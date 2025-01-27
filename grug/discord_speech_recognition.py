"""
Discord Speech Recognition Sink

based on the [SpeechRecognitionSink](https://github.com/imayhaveborkedit/discord-ext-voice-recv/blob/main/discord/ext/voice_recv/extras/speechrecognition.py)
from discord-ext-voice-recv.
"""

import array
import asyncio
import audioop
import concurrent.futures
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Awaitable, Final, Optional, TypedDict, TypeVar

import discord
import speech_recognition as sr
from discord.ext.voice_recv import AudioSink, SilencePacket, VoiceData
from loguru import logger
from speech_recognition.recognizers.whisper_api import openai as sr_openai
from tembo_pgmq_python import PGMQueue

from grug.settings import settings


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


class SpeechRecognitionSink(AudioSink):
    _stream_data: defaultdict[int, _StreamData] = defaultdict(
        lambda: _StreamData(stopper=None, recognizer=sr.Recognizer(), buffer=array.array("B"))
    )

    def __init__(self, discord_channel: discord.VoiceChannel):
        super().__init__(None)
        self.discord_channel: discord.VoiceChannel = discord_channel

        self.queue = PGMQueue(
            host=settings.postgres_host,
            port=settings.postgres_port,
            username=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
            database=settings.postgres_db,
        )

        # Create a queue for the voice channel if it doesn't exist
        if str(discord_channel.id) not in self.queue.list_queues():
            self.queue.create_queue(str(discord_channel.id))

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
