"""Command-line interface for running DnDBots."""

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from dndbots.campaign import Campaign
from dndbots.game import DnDGame
from dndbots.models import Character, Stats
from dndbots.session_zero import SessionZero


# Default paths
DATA_DIR = Path.home() / ".dndbots"
DEFAULT_DB = DATA_DIR / "campaigns.db"

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


async def run_game(session_zero: bool = False) -> None:
    """Run the game with persistence.

    Args:
        session_zero: If True, run Session Zero for collaborative creation
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize campaign
    campaign = Campaign(
        campaign_id="default_campaign",
        name="Caves of Chaos",
        db_path=str(DEFAULT_DB),
    )
    await campaign.initialize()

    try:
        # Handle session zero vs. normal flow
        if session_zero:
            print("\n" + "=" * 60)
            print("Starting Session Zero...")
            print("=" * 60 + "\n")

            sz = SessionZero(num_players=3)
            result = await sz.run()

            print("\n" + "=" * 60)
            print("SESSION ZERO COMPLETE")
            print("=" * 60)
            print(f"\nScenario: {result.scenario[:100]}...")
            print(f"Characters: {', '.join(c.name for c in result.characters)}")
            print(f"\nParty Document:\n{result.party_document[:200]}...")
            print()

            # Use session zero outputs
            characters = result.characters
            scenario = result.scenario
            party_document = result.party_document

            # Add characters to campaign
            for char in characters:
                await campaign.add_character(char)
        else:
            # Get or create character (existing flow)
            characters = await campaign.get_characters()
            if not characters:
                char = create_default_character()
                await campaign.add_character(char)
                characters = [char]

            scenario = DEFAULT_SCENARIO
            party_document = None

        # Start session
        await campaign.start_session()

        print(f"Campaign: {campaign.name}")
        print(f"Session: {campaign.current_session_id}")
        print(f"Characters: {', '.join(c.name for c in characters)}")
        print()

        # Create and run game
        game = DnDGame(
            scenario=scenario,
            characters=characters,
            dm_model="gpt-4o",
            player_model="gpt-4o",
            campaign=campaign,
            party_document=party_document,
        )

        await game.run()

    finally:
        await campaign.end_session("Session interrupted")
        await campaign.close()


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the admin UI server.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to listen on (default: 8000)
    """
    import uvicorn
    from dndbots.admin import app

    print(f"Starting DnDBots Admin UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="DnDBots - Multi-AI D&D Campaign System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'run' command (default behavior)
    run_parser = subparsers.add_parser("run", help="Run a game session")
    run_parser.add_argument(
        "--session-zero",
        action="store_true",
        help="Run Session Zero for collaborative campaign/character creation",
    )

    # 'serve' command
    serve_parser = subparsers.add_parser("serve", help="Start admin UI server")
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    args = parser.parse_args()

    if args.command == "serve":
        serve(host=args.host, port=args.port)
    else:
        # Default: run the game
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
            return

        print("=" * 60)
        print("DnDBots - Basic D&D AI Campaign")
        print("=" * 60)
        print(f"\nData directory: {DATA_DIR}")
        print("Type Ctrl+C to stop\n")

        # Get session_zero flag if present
        session_zero = getattr(args, 'session_zero', False)

        try:
            asyncio.run(run_game(session_zero=session_zero))
        except KeyboardInterrupt:
            print("\n\n[System] Session interrupted by user.")

        print("\n" + "=" * 60)
        print("Session ended")
        print("=" * 60)


if __name__ == "__main__":
    main()
