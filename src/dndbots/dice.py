"""Dice rolling utilities for D&D mechanics."""

import random
import re
from typing import TypedDict


class ParsedRoll(TypedDict):
    dice: int
    sides: int
    modifier: int


def roll(dice: int, sides: int, modifier: int = 0) -> int:
    """Roll dice and return total with modifier.

    Args:
        dice: Number of dice to roll
        sides: Number of sides per die
        modifier: Flat modifier to add to result

    Returns:
        Total of all dice plus modifier
    """
    total = sum(random.randint(1, sides) for _ in range(dice))
    return total + modifier


def parse_roll(notation: str) -> ParsedRoll:
    """Parse dice notation like '2d6+3' into components.

    Args:
        notation: Dice notation string (e.g., 'd20', '2d6', '3d6+2', 'd20-1')

    Returns:
        Dict with dice count, sides, and modifier

    Raises:
        ValueError: If notation is invalid
    """
    pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, notation.lower().replace(" ", ""))

    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    dice_str, sides_str, mod_str = match.groups()

    return ParsedRoll(
        dice=int(dice_str) if dice_str else 1,
        sides=int(sides_str),
        modifier=int(mod_str) if mod_str else 0,
    )
