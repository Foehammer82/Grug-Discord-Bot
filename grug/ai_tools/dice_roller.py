import random

from langchain_core.tools import tool


@tool
def roll_dice(number_of_dice: int, sides_of_dice: int) -> list[int]:
    """
    Roll a number of dice with a certain number of sides.

    Args:
        number_of_dice: The number of dice to roll.
        sides_of_dice: The number of sides on the dice.

    Returns:
        A list of the results of the dice rolls.
    """
    # TODO: make it so that there is validation that only valid dice options are used
    return [random.randint(1, sides_of_dice) for _ in range(number_of_dice)]
