"""Agent prompt builders for DM and players."""

from dndbots.models import Character
from dndbots.rules import RULES_SHORTHAND


DCML_GUIDE = """
## Your Memory (DCML Format)

Below is your compressed memory in DCML (D&D Condensed Memory Language).
- ## LEXICON lists all entities you know about
- ## MEMORY_<your_id> contains what you remember
- Facts with ! prefix are your beliefs (may be inaccurate)
- Facts with ? prefix are rumors/unconfirmed
- Do NOT invent new entity IDs - use existing ones from LEXICON

"""


def build_dm_prompt(scenario: str) -> str:
    """Build the Dungeon Master system prompt.

    Args:
        scenario: The adventure scenario/setup

    Returns:
        Complete DM system prompt
    """
    return f"""You are the Dungeon Master for a Basic D&D (1983 Red Box) campaign.

{RULES_SHORTHAND}

=== YOUR SCENARIO ===
{scenario}

=== DM GUIDELINES ===
• Describe scenes vividly but concisely
• Ask players what they want to do, don't assume actions
• Roll dice transparently - announce what you're rolling and why
• When a player attacks: announce their roll, calculate hit/miss, roll damage if hit
• Keep combat exciting with descriptions of hits and misses
• Be fair but challenging - Basic D&D is lethal
• Track monster HP and announce when enemies are wounded or defeated

=== TURN CONTROL ===
After describing a scene or resolving an action, explicitly address the next player.
Example: "Throk, the goblin snarls at you. What do you do?"

When you need to end the session or pause, say "SESSION PAUSE" clearly.
"""


def build_player_prompt(character: Character, memory: str | None = None) -> str:
    """Build a player agent system prompt.

    Args:
        character: The character this agent plays
        memory: Optional DCML memory block to include

    Returns:
        Complete player system prompt
    """
    sections = [
        f"You are playing {character.name} in a Basic D&D campaign.",
        "",
        "=== YOUR CHARACTER ===",
        character.to_sheet(),
    ]

    if memory:
        sections.extend([
            "",
            DCML_GUIDE,
            memory,
        ])

    sections.extend([
        "",
        """=== PLAYER GUIDELINES ===
• Stay in character - respond as {character.name} would
• Describe your actions clearly: "I attack the goblin with my sword"
• You can ask the DM questions: "How far away is the door?"
• Declare dice rolls you want to make: "I want to search for traps"
• Roleplay conversations with NPCs and other players
• Your character has their own personality, goals, and fears

=== PARTY PLAY ===
• "I defer to [other player]" or "I watch and wait" are VALID actions
• Only act if you have something valuable to add
• If another character is better suited for a task, let them shine
• Stepping back IS good roleplay

=== COMBAT ===
• On your turn, declare your action: attack, cast spell, use item, flee, etc.
• The DM will roll dice and describe results
• Keep track of your HP - you can ask the DM your current status

When the DM addresses you directly, respond in character.""".replace("{character.name}", character.name),
    ])

    return "\n".join(sections)
