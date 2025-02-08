from pathlib import Path

import yaml
from gradio_client import Client, handle_file
from loguru import logger

from grug.settings import settings
from grug.utils import log_runtime, timeout


@log_runtime
def get_tts(text: str) -> Path:
    """Get a TTS audio file for the given text.

    Args:
        text (str): The text to convert to speech.

    Returns: The path to the generated wav audio file.

    Notes:
        - F5-TTS Hugging Face Space: https://huggingface.co/spaces/mrfakename/E2-F5-TTS
        - F5-TTS source code: https://github.com/SWivid/F5-TTS
    """
    try:
        tts_client = Client(f"http://{settings.tts_f5_host}:{settings.tts_f5_port}/")
        tts_client.predict(new_choice="F5-TTS", api_name="/switch_tts_model")

        voices_dir = settings.root_dir / "assets" / "bot_voices"

        logger.info(f"Generating TTS for: {text}")
        with timeout(seconds=5):
            result = tts_client.predict(
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

    except ConnectionError as e:
        logger.error(f"Failed to connect to TTS server: {e}")

        # TODO: instead of raising an error, have a .wav file with an error tone or message and alert the chat that
        #       grug is unable to talk at the moment.
        raise e
