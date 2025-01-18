import logging

import discord
from loguru import logger


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


def get_interaction_response(interaction: discord.Interaction) -> discord.InteractionResponse:
    """
    Get the interaction response object from the interaction object.  Used to help with type hinting.
    """
    # noinspection PyTypeChecker
    return interaction.response
