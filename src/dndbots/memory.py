"""Memory projection for DCML - builds per-PC memory views from canonical state."""

from dataclasses import dataclass, field
from typing import Any

from dndbots.dcml import DCMLCategory, DCMLOp, render_lexicon_entry, render_relation
from dndbots.events import GameEvent, EventType
from dndbots.models import Character


# Class abbreviations for compact DCML
CLASS_ABBREV = {
    "Fighter": "FTR",
    "Cleric": "CLR",
    "Thief": "THF",
    "Magic-User": "MU",
    "Wizard": "MU",
    "Elf": "ELF",
    "Dwarf": "DWF",
    "Halfling": "HLF",
}


@dataclass
class MemoryBuilder:
    """Builds DCML memory blocks from campaign state."""

    event_window: int = 10  # Number of recent events to include

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

    def render_event(self, event: GameEvent) -> str:
        """Render a single event in DCML format.

        Format:
        - EVT:event_id @ location
        - participants in EVT:event_id
        - enemies (with xN count) in EVT:event_id
        - summary from content (truncated to 80 chars)
        """
        lines = []
        evt_id = f"EVT:{event.event_id}"

        # Location
        location = event.metadata.get("location")
        if location:
            lines.append(render_relation(evt_id, DCMLOp.AT, location))

        # Participants
        participants = event.metadata.get("participants", [])
        if event.source.startswith("pc_"):
            # Ensure source PC is first in the list
            participants = [event.source] + [p for p in participants if p != event.source]

        if participants:
            participant_str = ",".join(participants)
            lines.append(f"    {participant_str} in {evt_id}")

        # Enemies (for combat)
        enemies = event.metadata.get("enemies", [])
        enemy_count = event.metadata.get("enemy_count", len(enemies))
        if enemies:
            enemy_str = enemies[0]
            if enemy_count > 1:
                enemy_str += f"x{enemy_count}"
            lines.append(f"    {enemy_str} in {evt_id}")

        # Summary from content (truncated)
        summary = event.content[:80].replace("\n", " ")
        if len(event.content) > 80:
            summary += "..."
        lines.append(f'    {evt_id}::summary->"{summary}"')

        return "\n".join(lines)

    def build_pc_memory(
        self,
        pc_id: str,
        character: Character,
        events: list[GameEvent],
        party_id: str | None = None,
        quests: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build per-PC memory projection.

        Only includes:
        - Events the PC participated in
        - Facts the PC knows or inferred
        - Beliefs can be wrong (marked with !)
        """
        lines = [f"## MEMORY_{pc_id}", ""]

        # Core identity
        lines.append("# Identity & role")
        if party_id:
            lines.append(f"{pc_id} in {party_id};")

        class_abbrev = CLASS_ABBREV.get(character.char_class, character.char_class[:3].upper())
        lines.append(f"{pc_id}::class->{class_abbrev},level->{character.level};")

        # Stats (compact format)
        s = character.stats
        stats_str = f"STR{s.str},DEX{s.dex},CON{s.con},INT{s.int},WIS{s.wis},CHA{s.cha}"
        lines.append(f"{pc_id}::stats->{stats_str};")

        # Filter events by participation
        pc_events = [
            e for e in events
            if e.source == pc_id or pc_id in e.metadata.get("participants", [])
        ]

        # Window: only recent events
        recent_events = pc_events[-self.event_window:]
        old_events = pc_events[:-self.event_window] if len(pc_events) > self.event_window else []

        # Rollups for old events
        if old_events:
            rollups = self.create_rollups(old_events, pc_id)
            if rollups:
                lines.append("")
                lines.append("# Key past events (compressed)")
                lines.extend(rollups)

        # Recent events
        lines.append("")
        lines.append("# Recent events")

        for event in recent_events:
            lines.append(self.render_event(event))
            lines.append("")

        return "\n".join(lines)

    def create_rollups(self, events: list[GameEvent], pc_id: str) -> list[str]:
        """Create summary rollup facts from old events.

        Extracts key consequences:
        - Deaths (killed X)
        - Major discoveries
        - Reputation changes
        - Quest state changes
        """
        rollups = []

        for event in events:
            # Check for kills
            killed = event.metadata.get("killed", [])
            for victim in killed:
                rollups.append(f"{pc_id} -> KILLED:{victim}")

            # Check for quest changes
            quest_id = event.metadata.get("quest_id")
            quest_state = event.metadata.get("quest_state")
            if quest_id and quest_state:
                rollups.append(f"!QST:{quest_id}::state->{quest_state}")

        return rollups

    def build_memory_document(
        self,
        pc_id: str,
        character: Character,
        all_characters: list[Character],
        events: list[GameEvent],
        npcs: list[dict[str, Any]] | None = None,
        locations: list[dict[str, Any]] | None = None,
        party_id: str | None = None,
    ) -> str:
        """Build complete DCML memory document for a PC.

        Structure:
        - ## LEXICON (all known entities)
        - ## MEMORY_<pc_id> (filtered, subjective view)

        Returns:
            Combined document in format "## LEXICON\\n...\\n\\n## MEMORY_pc_id\\n..."
        """
        sections = []

        # Build lexicon from all known entities
        lexicon = self.build_lexicon(
            characters=all_characters,
            npcs=npcs,
            locations=locations,
        )
        sections.append(lexicon)

        # Build PC-specific memory
        memory = self.build_pc_memory(
            pc_id=pc_id,
            character=character,
            events=events,
            party_id=party_id,
        )
        sections.append(memory)

        return "\n\n".join(sections)
