from pathlib import Path

import yaml
from gradio_client import Client, handle_file
from loguru import logger

from grug.settings import settings

_CLIENT = Client(f"http://{settings.tts_f5_host}:{settings.tts_f5_port}/")
_CLIENT.predict(new_choice="F5-TTS", api_name="/switch_tts_model")


def get_tts(text: str) -> Path:
    """Get a TTS audio file for the given text.

    Args:
        text (str): The text to convert to speech.

    Returns: The path to the generated wav audio file.
    """
    voices_dir = settings.root_dir / "assets" / "bot_voices"

    logger.info(f"Generating TTS for: {text}")
    result = _CLIENT.predict(
        ref_audio_input=handle_file(voices_dir / f"{settings.tts_voice}.wav"),
        ref_text_input=yaml.safe_load((voices_dir / "reference_text.yml").read_text())[settings.tts_voice],
        gen_text_input=text,
        remove_silence=settings.tts_remove_silence,
        cross_fade_duration_slider=settings.tts_crossroad_duration_slider,
        nfe_slider=settings.tts_nfe_slider,
        speed_slider=settings.tts_speed_slider,
        api_name="/basic_tts",
    )
    logger.info("Finished generating TTS")

    return Path(result[0])
