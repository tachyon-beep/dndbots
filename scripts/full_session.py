#!/usr/bin/env python3
"""Full session: Session Zero followed by game play with disk logging."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from dndbots.session_zero import SessionZero, get_content_as_string
from dndbots.game import DnDGame
from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    session_zero_log = output_dir / f"session_zero_{timestamp}.jsonl"
    game_log = output_dir / f"game_{timestamp}.jsonl"
    transcript_file = output_dir / f"transcript_{timestamp}.txt"

    print("=" * 70)
    print("DNDBOTS FULL SESSION")
    print(f"Output directory: {output_dir}")
    print("=" * 70)

    # ========================================
    # PHASE 1: SESSION ZERO
    # ========================================
    print("\n" + "=" * 70)
    print("PHASE 1: SESSION ZERO - Collaborative Campaign Creation")
    print("=" * 70 + "\n")

    sz = SessionZero(
        num_players=3,
        dm_model="gpt-4o-mini",
        player_model="gpt-4o-mini",
        campaign_theme="Classic dungeon crawl with ancient ruins and treasure",
        session_notes="Keep Session Zero focused - aim for 10-15 messages total",
    )

    result = await sz.run()

    # Write Session Zero transcript to file
    with open(transcript_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("SESSION ZERO TRANSCRIPT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")

        for msg in result.transcript:
            source = getattr(msg, 'source', 'unknown')
            content = get_content_as_string(msg)
            f.write(f"[{source.upper()}]\n")
            f.write(f"{content}\n")
            f.write("-" * 40 + "\n\n")

            # Also print to console
            print(f"[{source.upper()}] {content[:200]}...")

    print("\n" + "=" * 70)
    print("SESSION ZERO COMPLETE")
    print("=" * 70)

    print("\n### SCENARIO ###")
    print(result.scenario or "(No scenario parsed - check transcript)")

    print("\n### PARTY DOCUMENT ###")
    print(result.party_document or "(No party document parsed - check transcript)")

    print("\n### CHARACTERS ###")
    if result.characters:
        for char in result.characters:
            print(f"\n{char.to_sheet()}")
    else:
        print("(No characters parsed - check transcript)")

    # Append session results to transcript file
    with open(transcript_file, "a") as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write("PARSED RESULTS\n")
        f.write("=" * 70 + "\n\n")

        f.write("### SCENARIO ###\n")
        f.write(result.scenario or "(Not parsed)\n")
        f.write("\n")

        f.write("### PARTY DOCUMENT ###\n")
        f.write(result.party_document or "(Not parsed)\n")
        f.write("\n")

        f.write("### CHARACTERS ###\n")
        for char in result.characters:
            f.write(f"{char.to_sheet()}\n\n")

    # Check if we have enough to run a game
    if not result.scenario or not result.characters:
        print("\n[ERROR] Session Zero didn't produce complete output.")
        print("Check the transcript file for details.")
        print(f"Transcript saved to: {transcript_file}")
        return

    # ========================================
    # PHASE 2: GAME SESSION
    # ========================================
    print("\n" + "=" * 70)
    print("PHASE 2: GAME SESSION - Adventure Begins!")
    print("=" * 70 + "\n")

    # Set up event bus with console and file logging
    event_bus = EventBus()
    event_bus.register(ConsolePlugin(show_timestamps=True))
    event_bus.register(JsonLogPlugin(log_path=str(game_log)))

    # Create and run game
    game = DnDGame(
        scenario=result.scenario,
        characters=result.characters,
        dm_model="gpt-4o-mini",
        player_model="gpt-4o-mini",
        event_bus=event_bus,
        party_document=result.party_document,
        enable_referee=True,
    )

    try:
        await game.run()
    except Exception as e:
        print(f"\n[Game ended: {e}]")

    # ========================================
    # FINAL SUMMARY
    # ========================================
    print("\n" + "=" * 70)
    print("SESSION COMPLETE")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  - Transcript: {transcript_file}")
    print(f"  - Game log:   {game_log}")


if __name__ == "__main__":
    asyncio.run(main())
