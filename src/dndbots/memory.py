"""Memory projection for DCML - builds per-PC memory views from canonical state."""

from dataclasses import dataclass, field
from typing import Any

from dndbots.dcml import DCMLCategory, render_lexicon_entry
from dndbots.models import Character


@dataclass
class MemoryBuilder:
    """Builds DCML memory blocks from campaign state."""

    def build_lexicon(
        self,
        characters: list[Character] | None = None,
        npcs: list[dict[str, Any]] | None = None,
        locations: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build ## LEXICON block from entities."""
        lines = ["## LEXICON"]

        # Player characters
        for char in characters or []:
            char_id = getattr(char, 'char_id', None) or f"pc_{char.name.lower()}_001"
            entry = render_lexicon_entry(DCMLCategory.PC, char_id, char.name)
            lines.append(entry)

        # NPCs
        for npc in npcs or []:
            entry = render_lexicon_entry(
                DCMLCategory.NPC,
                npc["uid"],
                npc["name"]
            )
            lines.append(entry)

        # Locations
        for loc in locations or []:
            entry = render_lexicon_entry(
                DCMLCategory.LOC,
                loc["uid"],
                loc["name"]
            )
            lines.append(entry)

        # Ensure consistent format with newline after header
        if len(lines) == 1:
            return lines[0] + "\n"
        return "\n".join(lines)
