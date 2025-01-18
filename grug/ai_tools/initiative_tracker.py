# TODO: build out tooling to track initiative and combat rounds for D&D games.
from langchain_core.tools import tool


@tool
async def get_weather(location: str):
    """Get the current weather for a location"""
    # TODO: this was just a test to make sure we could run async functions in the AI tools.

    return f"The weather in {location} is currently sunny with a high of 75 degrees and a low of 55 degrees."
