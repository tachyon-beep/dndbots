"""Memory projection for DCML - builds per-PC memory views from canonical state."""

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from dndbots.dcml import DCMLCategory, DCMLOp, render_lexicon_entry, render_relation
from dndbots.events import GameEvent, EventType
from dndbots.models import Character

if TYPE_CHECKING:
    from dndbots.storage.neo4j_store import Neo4jStore


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

    async def build_from_graph(
        self,
        pc_id: str,
        character: Character,
        neo4j: "Neo4jStore",
        party_id: str | None = None,
    ) -> str:
        """Build DCML memory from Neo4j graph.

        Args:
            pc_id: Player character ID
            character: Character object
            neo4j: Neo4jStore instance
            party_id: Optional party faction ID

        Returns:
            DCML formatted memory document
        """
        # Query graph for character's knowledge
        kills = await neo4j.get_character_kills(pc_id)
        moments = await neo4j.get_witnessed_moments(pc_id)
        known_entities = await neo4j.get_known_entities(pc_id)

        # Build LEXICON from known entities
        lexicon_lines = ["## LEXICON"]
        lexicon_lines.append(render_lexicon_entry(DCMLCategory.PC, pc_id, character.name))

        for entity in known_entities:
            entity_id = entity["entity_id"]
            name = entity["name"]
            entity_type = entity["entity_type"]

            if entity_type == "character":
                if entity_id.startswith("pc_"):
                    cat = DCMLCategory.PC
                else:
                    cat = DCMLCategory.NPC
            elif entity_type == "location":
                cat = DCMLCategory.LOC
            elif entity_type == "faction":
                cat = DCMLCategory.FAC
            else:
                continue

            lexicon_lines.append(render_lexicon_entry(cat, entity_id, name))

        # Build MEMORY section
        memory_lines = [f"## MEMORY_{pc_id}", ""]

        # Identity
        memory_lines.append("# Identity & role")
        if party_id:
            memory_lines.append(f"{pc_id} in {party_id};")

        class_abbrev = CLASS_ABBREV.get(character.char_class, character.char_class[:3].upper())
        memory_lines.append(f"{pc_id}::class->{class_abbrev},level->{character.level};")

        s = character.stats
        stats_str = f"STR{s.str},DEX{s.dex},CON{s.con},INT{s.int},WIS{s.wis},CHA{s.cha}"
        memory_lines.append(f"{pc_id}::stats->{stats_str};")

        # Kills
        if kills:
            memory_lines.append("")
            memory_lines.append("# Kills")
            for kill in kills:
                target = kill["target_id"]
                weapon = kill.get("weapon", "weapon")
                narrative = kill.get("narrative", "")

                line = f"{pc_id} -> KILLED:{target} ({weapon})"
                if narrative:
                    line += f' "{narrative}"'
                memory_lines.append(line)

        # Recent moments
        if moments:
            memory_lines.append("")
            memory_lines.append("# Recent events")
            for m in moments[:self.event_window]:
                mtype = m.get("moment_type", "event")
                desc = m.get("description", "")
                narrative = m.get("narrative", "")

                if narrative:
                    memory_lines.append(f"[{mtype}] {narrative}")
                else:
                    memory_lines.append(f"[{mtype}] {desc}")

        # Combine sections
        return "\n".join(lexicon_lines) + "\n\n" + "\n".join(memory_lines)
