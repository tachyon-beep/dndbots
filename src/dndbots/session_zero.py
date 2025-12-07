"""Session Zero: Collaborative campaign and character creation."""

import re
from dataclasses import dataclass
from typing import Any

from dndbots.models import Character, Stats


@dataclass
class SessionZeroResult:
    """Output from a completed Session Zero."""

    scenario: str
    characters: list[Character]
    party_document: str
    transcript: list[Any]  # Message objects from AutoGen


def build_session_zero_dm_prompt() -> str:
    """Build the DM system prompt for Session Zero."""
    return """You are the Dungeon Master for a Session Zero - collaborative campaign creation.

Your job is to FACILITATE, not dominate. Guide the players to create a cohesive party.

## Phases

PHASE 1 (Pitch): Share your campaign concept, then ask each player for their character pitch.
PHASE 2 (Converge): Help players find connections between characters and to your campaign.
PHASE 3 (Lock): Get final mechanical details, then produce the scenario and party document.

## Tools

Use these tools to look up rules and guides:
- lookup_rules("guides/interesting-campaigns", detail="full") - for your campaign design
- lookup_rules("guides/interesting-encounters", detail="full") - for planning encounters
- lookup_rules("guides/interesting-dungeons", detail="full") - for dungeon design
- lookup_rules("classes/X", detail="full") - for class details when players ask

## Phase Transitions

When a phase is complete, say the marker phrase EXACTLY:
- "PITCH COMPLETE" - after all players have pitched
- "CONVERGENCE COMPLETE" - after connections are established
- "SESSION ZERO LOCKED" - after all details are finalized

## Final Output

After saying "SESSION ZERO LOCKED", output these blocks:

[SCENARIO]
<your complete scenario text for the adventure>
[/SCENARIO]

[PARTY_DOCUMENT]
<relationships, hooks, shared history, potential tensions>
[/PARTY_DOCUMENT]

## Facilitation Tips

- Ask ONE player at a time for their pitch
- Actively suggest connections: "Player 2, how might you know Player 1?"
- Incorporate character backgrounds into your scenario
- Keep things moving - don't let discussion stall
"""


def build_session_zero_player_prompt(player_number: int) -> str:
    """Build a player system prompt for Session Zero.

    Args:
        player_number: Which player this is (1, 2, or 3)

    Returns:
        Complete player system prompt for session zero
    """
    return f"""You are Player {player_number} in a Session Zero - collaborative character creation.

Follow the DM's lead through each phase.

## Your Tasks

When the DM asks for your pitch:
- Look up the character guide: lookup_rules("guides/interesting-characters", detail="full")
- Propose an interesting character concept with personality, goals, and flaws
- Keep it brief - 2-3 paragraphs max

When the DM asks about connections:
- Find ways your character relates to other players' characters
- Connect your background to the DM's campaign hook
- Be flexible - adjust your concept to fit the party

When the DM asks for final details:
- Look up your class: lookup_rules("classes/X", detail="full")
- Finalize your mechanical stats

## Final Output

After the DM says "SESSION ZERO LOCKED", output your character:

[CHARACTER]
Name: <character name>
Class: <Fighter/Cleric/Magic-User/Thief/Elf/Dwarf/Halfling>
Stats: STR <n>, INT <n>, WIS <n>, DEX <n>, CON <n>, CHA <n>
HP: <number>
AC: <number>
Equipment: <comma-separated list>
Background: <1-2 sentence background>
[/CHARACTER]

## Guidelines

- Stay in character when describing your concept
- Be collaborative - build on others' ideas
- Don't dominate - let others shine too
- Be ready to adjust your concept to fit the party
"""


def parse_scenario(text: str) -> str:
    """Extract scenario from [SCENARIO]...[/SCENARIO] block.

    Args:
        text: Text containing scenario block

    Returns:
        Scenario content, or empty string if not found
    """
    match = re.search(r"\[SCENARIO\]\s*(.*?)\s*\[/SCENARIO\]", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def parse_party_document(text: str) -> str:
    """Extract party document from [PARTY_DOCUMENT]...[/PARTY_DOCUMENT] block.

    Args:
        text: Text containing party document block

    Returns:
        Party document content, or empty string if not found
    """
    match = re.search(r"\[PARTY_DOCUMENT\]\s*(.*?)\s*\[/PARTY_DOCUMENT\]", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def parse_character(text: str) -> Character | None:
    """Parse character from [CHARACTER]...[/CHARACTER] block.

    Args:
        text: Text containing character block

    Returns:
        Character object, or None if not found/invalid
    """
    match = re.search(r"\[CHARACTER\]\s*(.*?)\s*\[/CHARACTER\]", text, re.DOTALL)
    if not match:
        return None

    content = match.group(1)

    # Parse fields
    name_match = re.search(r"Name:\s*(.+)", content)
    class_match = re.search(r"Class:\s*(.+)", content)
    stats_match = re.search(
        r"Stats:\s*STR\s*(\d+),\s*INT\s*(\d+),\s*WIS\s*(\d+),\s*DEX\s*(\d+),\s*CON\s*(\d+),\s*CHA\s*(\d+)",
        content
    )
    hp_match = re.search(r"HP:\s*(\d+)", content)
    ac_match = re.search(r"AC:\s*(\d+)", content)
    equipment_match = re.search(r"Equipment:\s*(.+)", content)
    background_match = re.search(r"Background:\s*(.+)", content)

    if not all([name_match, class_match, stats_match, hp_match, ac_match]):
        return None

    equipment = []
    if equipment_match:
        equipment = [e.strip() for e in equipment_match.group(1).split(",")]

    return Character(
        name=name_match.group(1).strip(),
        char_class=class_match.group(1).strip(),
        level=1,
        hp=int(hp_match.group(1)),
        hp_max=int(hp_match.group(1)),
        ac=int(ac_match.group(1)),
        stats=Stats(
            str=int(stats_match.group(1)),
            int=int(stats_match.group(2)),
            wis=int(stats_match.group(3)),
            dex=int(stats_match.group(4)),
            con=int(stats_match.group(5)),
            cha=int(stats_match.group(6)),
        ),
        equipment=equipment,
        gold=0,
    )
