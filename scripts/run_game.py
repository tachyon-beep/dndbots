#!/usr/bin/env python3
"""Run a game session with pre-generated characters from Session Zero."""

import asyncio
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from dndbots.models import Character, Stats
from dndbots.game import DnDGame
from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin


# Characters from Session Zero transcript
LIRAEL = Character(
    name="Lirael",
    char_class="Thief",
    level=1,
    hp=4,
    hp_max=4,
    ac=7,  # Leather armor in BECMI (AC 7)
    stats=Stats(str=10, int=12, wis=10, dex=16, con=10, cha=14),
    equipment=["Thieves' Tools", "Dagger (1d4)", "Short bow", "Leather armor", "Cloak"],
)

FENNICK = Character(
    name="Fennick",
    char_class="Cleric",
    level=1,
    hp=6,
    hp_max=6,
    ac=4,  # Chain + shield
    stats=Stats(str=12, int=10, wis=16, dex=10, con=12, cha=12),
    equipment=["Mace (1d6)", "Shield", "Chain mail", "Holy symbol", "Healing herbs"],
)

KAELAN = Character(
    name="Kaelan",
    char_class="Magic-User",
    level=1,
    hp=3,
    hp_max=3,
    ac=9,  # No armor
    stats=Stats(str=8, int=16, wis=10, dex=12, con=10, cha=10),
    equipment=["Dagger (1d4)", "Spellbook", "Robes", "Staff"],
)

SCENARIO = """
The Shattered Realm - Eldra's Hollow

The party finds themselves in the town of Eldra's Hollow, a settlement struggling
in the aftermath of the Shattering - a cataclysmic magical event that tore the
Realm of Eldoria apart.

Reports of strange magical disturbances coincide with rumors of ancient artifacts
hidden within the nearby ruins of a temple lost to time.

- Lirael seeks to capitalize on the chaos, hoping to recover treasures that can
  restore her family's name.
- Kaelan sees the potential for ancient knowledge that will allow him to wrest
  control over the chaotic magic of the realm.
- Fennick aims to uncover the source of these disturbances to heal the rifts
  formed by the Shattering.

As they explore the temple, they will encounter both physical challenges, such
as traps and guardians left behind, and moral challenges involving the power
imbued in the artifacts. The party must decide not just what they want for
themselves, but what kind of legacy they wish to leave behind.

START: The party arrives at the entrance to the ruined temple as dusk falls.
Strange lights flicker within the crumbling structure.
"""

PARTY_DOCUMENT = """
## Party Composition
- Lirael Brightsky (Thief) - Former noble seeking to restore family honor
- Fennick Torun (Cleric) - Acolyte of a forgotten deity, seeking balance
- Kaelan Wynter (Magic-User) - Reckless mage obsessed with the Shattering's magic

## Relationships
- Fennick acts as the party's moral compass, often mediating between Lirael and Kaelan
- Lirael views Kaelan's recklessness with a mix of fascination and concern
- Kaelan respects Fennick's wisdom but sometimes finds his caution frustrating

## Potential Tensions
- Lirael's treasure-hunting may conflict with Fennick's restorative mission
- Kaelan's curiosity about dangerous magic could put the party at risk
- All three have different views on what to do with powerful artifacts

## Shared Goal
Explore the temple ruins and uncover the source of the magical disturbances
"""


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    game_log = output_dir / f"game_{timestamp}.jsonl"
    game_transcript = output_dir / f"game_transcript_{timestamp}.txt"

    print("=" * 70)
    print("DNDBOTS GAME SESSION")
    print("The Shattered Realm - Eldra's Hollow")
    print("=" * 70)

    print("\n### PARTY ###")
    for char in [LIRAEL, FENNICK, KAELAN]:
        print(f"\n{char.to_sheet()}")

    print("\n" + "=" * 70)
    print("ADVENTURE BEGINS")
    print("=" * 70 + "\n")

    # Set up event bus with console and file logging
    event_bus = EventBus()
    event_bus.register(ConsolePlugin(show_timestamps=True))
    event_bus.register(JsonLogPlugin(log_path=str(game_log)))

    # Create transcript file
    transcript_lines = []

    # Create custom plugin to capture transcript
    class TranscriptPlugin:
        name = "transcript"
        handled_types = None

        async def start(self):
            pass

        async def stop(self):
            # Write transcript at end
            with open(game_transcript, "w") as f:
                f.write("=" * 70 + "\n")
                f.write("GAME TRANSCRIPT\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 70 + "\n\n")
                f.write(SCENARIO + "\n\n")
                f.write("-" * 70 + "\n\n")
                for line in transcript_lines:
                    f.write(line + "\n")

        async def handle(self, event):
            if event.event_type in (OutputEventType.NARRATION, OutputEventType.PLAYER_ACTION,
                                     OutputEventType.REFEREE, OutputEventType.DICE_ROLL):
                transcript_lines.append(f"[{event.source.upper()}]")
                transcript_lines.append(event.content if isinstance(event.content, str) else str(event.content))
                transcript_lines.append("")

    event_bus.register(TranscriptPlugin())

    # Create and run game
    game = DnDGame(
        scenario=SCENARIO,
        characters=[LIRAEL, FENNICK, KAELAN],
        dm_model="gpt-4o-mini",
        player_model="gpt-4o-mini",
        event_bus=event_bus,
        party_document=PARTY_DOCUMENT,
        enable_referee=True,
    )

    try:
        await game.run()
    except Exception as e:
        print(f"\n[Game ended: {e}]")

    print("\n" + "=" * 70)
    print("SESSION COMPLETE")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  - Game log (JSONL):  {game_log}")
    print(f"  - Game transcript:   {game_transcript}")


if __name__ == "__main__":
    asyncio.run(main())
