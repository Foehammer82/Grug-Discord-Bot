import random

from langchain_core.tools import tool


@tool(parse_docstring=True)
def roll_dice(number_of_dice: int, sides_of_dice: int) -> tuple[list[int], int]:
    """
    Roll a number of dice with a certain number of sides.

    Args:
        number_of_dice: The number of dice to roll.
        sides_of_dice: The number of sides on the dice.  Valid options are 4, 6, 8, 10, 12, 20, and 100.

    Returns:
        A Tuple with the first value being a list of the results of the dice rolls, and the second value is the sum
        of the dice rolls.

    Raises:
        ValueError: If the number of sides on the dice is not one of the valid options
    """
    if sides_of_dice not in [4, 6, 8, 10, 12, 20, 100]:
        raise ValueError(f"Invalid number of sides on dice: {sides_of_dice}")

    result = [random.randint(1, sides_of_dice) for _ in range(number_of_dice)]

    return result, sum(result)
