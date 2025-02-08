from datetime import date

from langchain_core.tools import tool
from loguru import logger
from openai import AsyncOpenAI
from openai.types import Image
from sqlalchemy import Date, cast, func
from sqlmodel import select

from grug.db import async_session_factory
from grug.models import DalleImageRequest
from grug.settings import settings


@tool
async def generate_ai_image(prompt: str) -> dict[str, str | int] | None:
    """
    Generate an image using OpenAI's DALL-E model, and returns a URL to the generated image.

    Args:
        prompt (str): The prompt to generate the image from.

    Returns:
        dict: A dictionary with the following keys:
            - image_url (str): The URL to the generated image.
            - model (str): The model used to generate the image.
            - size (str): The size of the generated image.
            - image_generations_left_today (Optional(int)): The number of image generations left today, based on the app's
              settings, and Grugs wallet.
        None: If the image generation limit has been exceeded or if the assistant is not available.
    """
    # Notes:
    #   - as of 6/9/2024, it costs $0.04 per dall-e-3 image, and $0.02 per dall-e-2 image
    #   - pricing reference: https://openai.com/api/pricing/
    #   - API reference: https://platform.openai.com/docs/guides/images/usage?context=python

    # TODO: have it so you can make recommendations for image that was just output.

    if not settings.ai_image_generation_enabled:
        raise ValueError("AI image generation is disabled.")

    # Return None if the assistant is not available
    async with async_session_factory() as session:

        # Get the image requests remaining for the day
        # noinspection PyTypeChecker,Pydantic
        picture_request_count_for_today = (
            await session.execute(
                select(func.count("*"))
                .select_from(DalleImageRequest)
                .where(cast(DalleImageRequest.request_time, Date) == date.today())
            )
        ).scalar()

        remaining_image_requests = settings.ai_image_daily_generation_limit - picture_request_count_for_today

        # Check if the user has exceeded the daily image generation limit
        if remaining_image_requests and remaining_image_requests <= 0:
            raise ValueError("You have exceeded the daily image generation limit.")
        logger.info(f"Remaining Dall-E image requests: {remaining_image_requests}")

        logger.info("### Generating AI Image ###")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Model: {settings.ai_image_default_model}")
        logger.info(f"Size: {settings.ai_image_default_size}")
        logger.info(f"Quality: {settings.ai_image_default_quality}")

        if not settings.openai_api_key:
            raise ValueError("`OPENAI_API_KEY` env variable is required to run the Grug Discord Agent.")

        openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        response = await openai_client.images.generate(
            model=settings.ai_image_default_model,
            prompt=prompt,
            size=settings.ai_image_default_size,
            quality=settings.ai_image_default_quality,
            n=1,
        )
        response_image: Image = response.data[0]

        logger.info(f"revised prompt: {response_image.revised_prompt}")
        logger.info(f"Image URL: {response_image.url}")
        logger.info("### Completed Generating AI Image ###")

        # Save the image request to the database
        dalle_image_request = DalleImageRequest(
            prompt=prompt,
            model=settings.ai_image_default_model,
            size=settings.ai_image_default_size,
            quality=settings.ai_image_default_quality,
            revised_prompt=response_image.revised_prompt,
            image_url=response_image.url,
        )
        session.add(dalle_image_request)
        await session.commit()

    return {
        "image_url": response_image.url,
        "model": settings.ai_image_default_model,
        "size": settings.ai_image_default_size,
        "image_generations_left_today": remaining_image_requests,
    }
