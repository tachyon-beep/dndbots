"""Command-line interface for running DnDBots."""

import asyncio
import os

from dotenv import load_dotenv

from dndbots.game import DnDGame
from dndbots.models import Character, Stats


# Default test scenario
DEFAULT_SCENARIO = """
The party stands at the entrance to the Caves of Chaos - a dark opening
in the hillside that locals say is home to goblins and worse.

The village of Millbrook has offered 50 gold pieces for clearing out
the goblin threat. Merchants have been attacked on the road, and
three villagers went missing last week.

Inside the cave entrance, you can see crude torches flickering in
wall sconces, and you hear guttural voices echoing from deeper within.

Start by describing the scene and asking the party what they want to do.
"""


def create_default_character() -> Character:
    """Create a default fighter character for testing."""
    return Character(
        name="Throk",
        char_class="Fighter",
        level=1,
        hp=8,
        hp_max=8,
        ac=5,
        stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
        equipment=["longsword", "chain mail", "shield", "backpack", "torch x3", "rope 50ft"],
        gold=25,
    )


def main() -> None:
    """Run a test game session."""
    # Load environment variables
    load_dotenv()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
        return

    print("=" * 60)
    print("DnDBots - Basic D&D AI Campaign")
    print("=" * 60)
    print("\nStarting test session with 1 player (Throk the Fighter)")
    print("Type Ctrl+C to stop\n")

    # Create game
    character = create_default_character()
    game = DnDGame(
        scenario=DEFAULT_SCENARIO,
        characters=[character],
        dm_model="gpt-4o",
        player_model="gpt-4o",
    )

    # Run the game
    try:
        asyncio.run(game.run(max_turns=20))
    except KeyboardInterrupt:
        print("\n\n[System] Session interrupted by user.")

    print("\n" + "=" * 60)
    print("Session ended")
    print("=" * 60)


if __name__ == "__main__":
    main()
