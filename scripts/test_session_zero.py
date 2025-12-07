#!/usr/bin/env python3
"""End-to-end test: Full Session Zero with 3 players."""

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncio
from dndbots.session_zero import SessionZero


async def main():
    print("=" * 70)
    print("SESSION ZERO: Collaborative Campaign Creation")
    print("=" * 70)

    sz = SessionZero(
        num_players=3,
        dm_model="gpt-4o-mini",  # Use mini for faster/cheaper test
        player_model="gpt-4o-mini",
    )

    result = await sz.run()

    print("\n" + "=" * 70)
    print("SESSION ZERO COMPLETE")
    print("=" * 70)

    print("\n### SCENARIO ###")
    print(result.scenario)

    print("\n### PARTY DOCUMENT ###")
    print(result.party_document)

    print("\n### CHARACTERS ###")
    for char in result.characters:
        print(f"\n{char.to_sheet()}")

    print("\n" + "=" * 70)
    print(f"Total messages in transcript: {len(result.transcript)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
