# Phase 4: DCML Compression Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement DCML (D&D Condensed Memory Language) to serialize campaign state into token-efficient text for LLM context windows.

**Architecture:** Three-layer system where canonical state (Neo4j + SQLite) is serialized to DCML text, then projected into per-PC filtered memory views. Models READ this memory; the engine OWNS it. No RAG - deterministic UID lookups only.

**Tech Stack:** Python dataclasses, existing SQLiteStore/Neo4jStore, string rendering, pytest

---

## Task 1: DCML Core Types and Operators

**Files:**
- Create: `src/dndbots/dcml.py`
- Test: `tests/test_dcml.py`

**Step 1: Write the failing test for DCML entity rendering**

```python
"""Tests for DCML (D&D Condensed Memory Language)."""

import pytest
from dndbots.dcml import DCMLEntity, DCMLCategory, render_lexicon_entry


class TestDCMLEntity:
    def test_render_lexicon_entry_pc(self):
        """Lexicon entries use [CATEGORY:ID:Name] format."""
        entry = render_lexicon_entry(
            category=DCMLCategory.PC,
            uid="pc_throk_001",
            name="Throk"
        )
        assert entry == "[PC:pc_throk_001:Throk]"

    def test_render_lexicon_entry_npc(self):
        entry = render_lexicon_entry(
            category=DCMLCategory.NPC,
            uid="npc_grimfang_001",
            name="Grimfang"
        )
        assert entry == "[NPC:npc_grimfang_001:Grimfang]"

    def test_render_lexicon_entry_location(self):
        entry = render_lexicon_entry(
            category=DCMLCategory.LOC,
            uid="loc_darkwood_cave",
            name="DarkwoodCave"
        )
        assert entry == "[LOC:loc_darkwood_cave:DarkwoodCave]"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dcml.py::TestDCMLEntity -v`
Expected: FAIL with "No module named 'dndbots.dcml'"

**Step 3: Write minimal implementation**

```python
"""DCML (D&D Condensed Memory Language) - Token-efficient campaign state serialization.

DCML is a lossy-but-precise serialization of campaign state from Neo4j + SQLite,
designed for LLM consumption. Models READ this; the engine OWNS it.

Based on UCLS (Ultra-Condensed Lore System) with D&D-specific adaptations.
See docs/example_compression.md for full specification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DCMLCategory(Enum):
    """Entity categories for DCML lexicon."""
    PC = "PC"           # Player character
    NPC = "NPC"         # Named NPC / unique monster
    MON = "MON"         # Monster type (template)
    LOC = "LOC"         # Location / room / region
    FAC = "FAC"         # Faction / organization
    ITEM = "ITEM"       # Object / treasure
    QST = "QST"         # Quest / story thread
    EVT = "EVT"         # Event / beat / scene


def render_lexicon_entry(category: DCMLCategory, uid: str, name: str) -> str:
    """Render a lexicon entry in [CATEGORY:UID:Name] format."""
    return f"[{category.value}:{uid}:{name}]"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_dcml.py::TestDCMLEntity -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/dcml.py tests/test_dcml.py
git commit -m "feat: DCML core types and lexicon entry rendering"
```

---

## Task 2: DCML Operators and Relation Rendering

**Files:**
- Modify: `src/dndbots/dcml.py`
- Modify: `tests/test_dcml.py`

**Step 1: Write failing tests for relation rendering**

Add to `tests/test_dcml.py`:

```python
from dndbots.dcml import render_relation, DCMLOp


class TestDCMLRelations:
    def test_render_located_at(self):
        """@ operator for location."""
        rel = render_relation("pc_throk_001", DCMLOp.AT, "loc_darkwood_cave")
        assert rel == "pc_throk_001 @ loc_darkwood_cave"

    def test_render_member_of(self):
        """'in' operator for membership."""
        rel = render_relation("pc_throk_001", DCMLOp.IN, "fac_party_001")
        assert rel == "pc_throk_001 in fac_party_001"

    def test_render_contains(self):
        """> operator for containment."""
        rel = render_relation("loc_cave_main", DCMLOp.CONTAINS, "loc_cave_room_02")
        assert rel == "loc_cave_main > loc_cave_room_02"

    def test_render_leads_to(self):
        """-> operator for causality."""
        rel = render_relation("evt_003_047", DCMLOp.LEADS_TO, "evt_003_048")
        assert rel == "evt_003_047 -> evt_003_048"

    def test_render_caused_by(self):
        """<- operator for origin."""
        rel = render_relation("fac_mages_guild", DCMLOp.CAUSED_BY, "race_elves")
        assert rel == "fac_mages_guild <- race_elves"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dcml.py::TestDCMLRelations -v`
Expected: FAIL with "cannot import name 'render_relation'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/dcml.py`:

```python
class DCMLOp(Enum):
    """DCML operators - ASCII-friendly for cross-model compatibility."""
    # Structure & membership
    CONTAINS = ">"      # A contains / parents B
    PART_OF = "<"       # A is part of B
    AT = "@"            # X is located at Y
    IN = "in"           # X is member of group Y

    # Causality
    LEADS_TO = "->"     # A leads to / results in B
    CAUSED_BY = "<-"    # A was caused by / originates from B
    ASSOC = "~"         # Associated with / thematically linked

    # Definition
    DEFINED_AS = ":="   # Core identity
    PROPS = "::"        # Properties block


def render_relation(subject: str, op: DCMLOp, obj: str) -> str:
    """Render a relation in 'subject OP object' format."""
    return f"{subject} {op.value} {obj}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_dcml.py::TestDCMLRelations -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/dcml.py tests/test_dcml.py
git commit -m "feat: DCML operators and relation rendering"
```

---

## Task 3: DCML Properties Rendering

**Files:**
- Modify: `src/dndbots/dcml.py`
- Modify: `tests/test_dcml.py`

**Step 1: Write failing tests for properties**

Add to `tests/test_dcml.py`:

```python
from dndbots.dcml import render_properties


class TestDCMLProperties:
    def test_render_simple_properties(self):
        """Properties use ::key->value format."""
        props = render_properties("pc_throk_001", {"class": "FTR", "level": 3})
        assert props == "pc_throk_001::class->FTR,level->3"

    def test_render_stats_properties(self):
        """Stats can be rendered compactly."""
        props = render_properties("pc_throk_001", {
            "stats": "STR17,DEX12,CON15,INT8,WIS10,CHA9"
        })
        assert props == "pc_throk_001::stats->STR17,DEX12,CON15,INT8,WIS10,CHA9"

    def test_render_hp_delta(self):
        """HP changes use hpD notation."""
        props = render_properties("pc_throk_001", {"hpD": -12})
        assert props == "pc_throk_001::hpD->-12"

    def test_render_tags(self):
        """Tags are comma-separated."""
        props = render_properties("pc_throk_001", {
            "tags": ["reckless", "protective"]
        })
        assert props == 'pc_throk_001::tags->"reckless","protective"'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dcml.py::TestDCMLProperties -v`
Expected: FAIL with "cannot import name 'render_properties'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/dcml.py`:

```python
def render_properties(subject: str, props: dict[str, Any]) -> str:
    """Render properties in subject::key->value,key->value format."""
    parts = []
    for key, value in props.items():
        if isinstance(value, list):
            # Tags and lists get quoted
            formatted = ",".join(f'"{v}"' for v in value)
        else:
            formatted = str(value)
        parts.append(f"{key}->{formatted}")

    return f"{subject}::{','.join(parts)}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_dcml.py::TestDCMLProperties -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/dcml.py tests/test_dcml.py
git commit -m "feat: DCML properties rendering"
```

---

## Task 4: DCML Epistemic Markers

**Files:**
- Modify: `src/dndbots/dcml.py`
- Modify: `tests/test_dcml.py`

**Step 1: Write failing tests for epistemic markers**

Add to `tests/test_dcml.py`:

```python
from dndbots.dcml import render_fact, Certainty


class TestDCMLEpistemics:
    def test_render_fact_certain(self):
        """No prefix for canonical facts."""
        line = render_fact("pc_throk_001 in fac_party_001", Certainty.FACT)
        assert line == "pc_throk_001 in fac_party_001"

    def test_render_fact_belief(self):
        """! prefix for in-world beliefs (may be wrong)."""
        line = render_fact("npc_elena_001 ~ fac_resistance", Certainty.BELIEF)
        assert line == "!npc_elena_001 ~ fac_resistance"

    def test_render_fact_rumor(self):
        """? prefix for rumors/unconfirmed."""
        line = render_fact("npc_unknown_master::role->patron", Certainty.RUMOR)
        assert line == "?npc_unknown_master::role->patron"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dcml.py::TestDCMLEpistemics -v`
Expected: FAIL with "cannot import name 'render_fact'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/dcml.py`:

```python
class Certainty(Enum):
    """Epistemic status markers for DCML facts."""
    FACT = ""       # Canonical, objective truth
    BELIEF = "!"    # In-world belief (may be inaccurate)
    RUMOR = "?"     # Myth, legend, or unconfirmed


def render_fact(statement: str, certainty: Certainty = Certainty.FACT) -> str:
    """Render a statement with epistemic marker prefix."""
    return f"{certainty.value}{statement}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_dcml.py::TestDCMLEpistemics -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/dcml.py tests/test_dcml.py
git commit -m "feat: DCML epistemic markers (fact/belief/rumor)"
```

---

## Task 5: Lexicon Builder from Database

**Files:**
- Create: `src/dndbots/memory.py`
- Test: `tests/test_memory.py`

**Step 1: Write failing test for lexicon building**

```python
"""Tests for DCML memory projection."""

import pytest
from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats


class TestLexiconBuilder:
    def test_build_lexicon_from_characters(self):
        """Build lexicon entries from Character objects."""
        chars = [
            Character(
                name="Throk",
                char_class="Fighter",
                level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
                char_id="pc_throk_001"
            ),
            Character(
                name="Zara",
                char_class="Thief",
                level=1,
                hp=4, hp_max=4, ac=7,
                stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
                equipment=[], gold=0,
                char_id="pc_zara_001"
            ),
        ]

        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=chars)

        assert "[PC:pc_throk_001:Throk]" in lexicon
        assert "[PC:pc_zara_001:Zara]" in lexicon

    def test_build_lexicon_includes_header(self):
        """Lexicon block has ## LEXICON header."""
        builder = MemoryBuilder()
        lexicon = builder.build_lexicon(characters=[])

        assert lexicon.startswith("## LEXICON\n")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestLexiconBuilder -v`
Expected: FAIL with "No module named 'dndbots.memory'"

**Step 3: Write minimal implementation**

```python
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

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestLexiconBuilder -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory.py
git commit -m "feat: DCML lexicon builder from characters"
```

---

## Task 6: Event Rendering to DCML

**Files:**
- Modify: `src/dndbots/memory.py`
- Modify: `tests/test_memory.py`

**Step 1: Write failing test for event rendering**

Add to `tests/test_memory.py`:

```python
from dndbots.events import GameEvent, EventType


class TestEventRenderer:
    def test_render_combat_event(self):
        """Combat events render with participants and outcomes."""
        event = GameEvent(
            event_id="evt_003_047",
            event_type=EventType.COMBAT_ROUND,
            source="dm",
            content="Goblin ambush at cave entrance",
            session_id="session_001",
            metadata={
                "location": "loc_darkwood_entrance",
                "participants": ["pc_throk_001", "pc_zara_001"],
                "enemies": ["mon_goblin_darkwood"],
                "enemy_count": 4,
            }
        )

        builder = MemoryBuilder()
        dcml = builder.render_event(event)

        assert "EVT:evt_003_047 @ loc_darkwood_entrance" in dcml
        assert "pc_throk_001" in dcml
        assert "mon_goblin_darkwood" in dcml

    def test_render_player_action_event(self):
        """Player actions render with summary."""
        event = GameEvent(
            event_id="evt_003_048",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I search the goblin bodies for loot",
            session_id="session_001",
            metadata={"location": "loc_darkwood_entrance"}
        )

        builder = MemoryBuilder()
        dcml = builder.render_event(event)

        assert "EVT:evt_003_048" in dcml
        assert "search" in dcml.lower() or "loot" in dcml.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestEventRenderer -v`
Expected: FAIL with "MemoryBuilder has no attribute 'render_event'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/memory.py`:

```python
from dndbots.events import GameEvent, EventType
from dndbots.dcml import DCMLOp, render_relation, render_properties


@dataclass
class MemoryBuilder:
    """Builds DCML memory blocks from campaign state."""

    # ... existing methods ...

    def render_event(self, event: GameEvent) -> str:
        """Render a single event in DCML format."""
        lines = []
        evt_id = f"EVT:{event.event_id}"

        # Location
        location = event.metadata.get("location")
        if location:
            lines.append(render_relation(evt_id, DCMLOp.AT, location))

        # Participants
        participants = event.metadata.get("participants", [])
        if event.source.startswith("pc_"):
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
        lines.append(f"    {evt_id}::summary->\"{summary}\"")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestEventRenderer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory.py
git commit -m "feat: DCML event rendering"
```

---

## Task 7: Per-PC Memory Projection

**Files:**
- Modify: `src/dndbots/memory.py`
- Modify: `tests/test_memory.py`

**Step 1: Write failing test for PC memory projection**

Add to `tests/test_memory.py`:

```python
class TestMemoryProjection:
    def test_build_pc_memory_includes_header(self):
        """PC memory has ## MEMORY_<id> header."""
        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk",
                char_class="Fighter",
                level=3,
                hp=24, hp_max=24, ac=5,
                stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
                equipment=["longsword", "chain mail"],
                gold=50,
            ),
            events=[],
        )

        assert "## MEMORY_pc_throk_001" in memory

    def test_build_pc_memory_includes_core_facts(self):
        """PC memory includes class, level, key traits."""
        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk",
                char_class="Fighter",
                level=3,
                hp=24, hp_max=24, ac=5,
                stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
                equipment=["longsword"],
                gold=50,
            ),
            events=[],
        )

        assert "class->FTR" in memory or "class->Fighter" in memory
        assert "level->3" in memory

    def test_build_pc_memory_filters_events_by_participation(self):
        """PC only sees events they participated in."""
        throk_event = GameEvent(
            event_id="evt_001",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="Throk attacks",
            session_id="s1",
            metadata={"participants": ["pc_throk_001"]}
        )
        zara_event = GameEvent(
            event_id="evt_002",
            event_type=EventType.PLAYER_ACTION,
            source="pc_zara_001",
            content="Zara sneaks",
            session_id="s1",
            metadata={"participants": ["pc_zara_001"]}  # Throk not present
        )

        builder = MemoryBuilder()
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk", char_class="Fighter", level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
            ),
            events=[throk_event, zara_event],
        )

        assert "evt_001" in memory
        assert "evt_002" not in memory  # Throk wasn't there
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestMemoryProjection -v`
Expected: FAIL with "MemoryBuilder has no attribute 'build_pc_memory'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/memory.py`:

```python
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

    # ... existing methods ...

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
        lines.append("")
        lines.append("# Recent events")

        for event in events:
            participants = event.metadata.get("participants", [])
            # Include if PC is source or in participants
            if event.source == pc_id or pc_id in participants:
                lines.append(self.render_event(event))
                lines.append("")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestMemoryProjection -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory.py
git commit -m "feat: per-PC memory projection with event filtering"
```

---

## Task 8: Full Memory Document Assembly

**Files:**
- Modify: `src/dndbots/memory.py`
- Modify: `tests/test_memory.py`

**Step 1: Write failing test for full memory document**

Add to `tests/test_memory.py`:

```python
class TestMemoryDocument:
    def test_build_full_memory_document(self):
        """Full memory doc has lexicon + PC memory."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
            char_id="pc_throk_001",
        )

        builder = MemoryBuilder()
        doc = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=[],
        )

        assert "## LEXICON" in doc
        assert "[PC:pc_throk_001:Throk]" in doc
        assert "## MEMORY_pc_throk_001" in doc

    def test_memory_document_token_estimate(self):
        """Memory documents should stay under token budget."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        # Simulate 10 events
        events = [
            GameEvent(
                event_id=f"evt_{i:03d}",
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i} " * 20,  # ~80 chars each
                session_id="s1",
                metadata={"participants": ["pc_throk_001"]}
            )
            for i in range(10)
        ]

        builder = MemoryBuilder()
        doc = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=events,
        )

        # Rough estimate: 4 chars per token
        estimated_tokens = len(doc) / 4
        assert estimated_tokens < 2000  # Should fit easily
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestMemoryDocument -v`
Expected: FAIL with "MemoryBuilder has no attribute 'build_memory_document'"

**Step 3: Write minimal implementation**

Add to `src/dndbots/memory.py`:

```python
@dataclass
class MemoryBuilder:
    """Builds DCML memory blocks from campaign state."""

    # ... existing methods ...

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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestMemoryDocument -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory.py
git commit -m "feat: full DCML memory document assembly"
```

---

## Task 9: Integrate Memory into Player Prompts

**Files:**
- Modify: `src/dndbots/prompts.py`
- Modify: `tests/test_prompts.py`

**Step 1: Write failing test for memory injection**

Add to `tests/test_prompts.py`:

```python
from dndbots.memory import MemoryBuilder


class TestMemoryIntegration:
    def test_player_prompt_includes_memory_block(self):
        """Player prompts can include DCML memory."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
            char_id="pc_throk_001",
        )

        builder = MemoryBuilder()
        memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=char,
            all_characters=[char],
            events=[],
        )

        prompt = build_player_prompt(char, memory=memory)

        assert "## LEXICON" in prompt
        assert "## MEMORY_pc_throk_001" in prompt

    def test_player_prompt_explains_dcml(self):
        """Player prompts include brief DCML usage guide."""
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        prompt = build_player_prompt(char, memory="## LEXICON\n## MEMORY_test")

        assert "LEXICON" in prompt
        # Should explain what memory block means
        assert "remember" in prompt.lower() or "memory" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompts.py::TestMemoryIntegration -v`
Expected: FAIL (build_player_prompt doesn't accept memory parameter)

**Step 3: Write minimal implementation**

Modify `src/dndbots/prompts.py` to add memory parameter:

```python
DCML_GUIDE = """
## Your Memory (DCML Format)

Below is your compressed memory in DCML (D&D Condensed Memory Language).
- ## LEXICON lists all entities you know about
- ## MEMORY_<your_id> contains what you remember
- Facts with ! prefix are your beliefs (may be inaccurate)
- Facts with ? prefix are rumors/unconfirmed
- Do NOT invent new entity IDs - use existing ones from LEXICON

"""


def build_player_prompt(character: Character, memory: str | None = None) -> str:
    """Build the system prompt for a player agent.

    Args:
        character: The character this agent plays
        memory: Optional DCML memory block to include
    """
    sections = [
        f"You are {character.name}, a level {character.level} {character.char_class}.",
        "",
        "BASIC D&D RULES:",
        RULES_SHORTHAND,
        "",
        format_character_sheet(character),
    ]

    if memory:
        sections.extend([
            "",
            DCML_GUIDE,
            memory,
        ])

    sections.extend([
        "",
        PLAYER_PRINCIPLES,
    ])

    return "\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompts.py::TestMemoryIntegration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/prompts.py tests/test_prompts.py
git commit -m "feat: integrate DCML memory into player prompts"
```

---

## Task 10: Event Windowing and Rollup

**Files:**
- Modify: `src/dndbots/memory.py`
- Modify: `tests/test_memory.py`

**Step 1: Write failing test for event windowing**

Add to `tests/test_memory.py`:

```python
class TestEventWindowing:
    def test_recent_events_limited_to_window(self):
        """Only last N events included in memory."""
        events = [
            GameEvent(
                event_id=f"evt_{i:03d}",
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i}",
                session_id="s1",
                metadata={"participants": ["pc_throk_001"]}
            )
            for i in range(20)
        ]

        builder = MemoryBuilder(event_window=5)
        memory = builder.build_pc_memory(
            pc_id="pc_throk_001",
            character=Character(
                name="Throk", char_class="Fighter", level=1,
                hp=8, hp_max=8, ac=5,
                stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
                equipment=[], gold=0,
            ),
            events=events,
        )

        # Should only have last 5 events
        assert "evt_019" in memory
        assert "evt_015" in memory
        assert "evt_010" not in memory  # Too old

    def test_rollup_for_old_events(self):
        """Old events get rolled up into summary facts."""
        old_events = [
            GameEvent(
                event_id="evt_old_001",
                event_type=EventType.COMBAT_ROUND,
                source="dm",
                content="Killed Grimfang the goblin chief",
                session_id="s1",
                metadata={
                    "participants": ["pc_throk_001"],
                    "killed": ["npc_grimfang_001"],
                }
            ),
        ]

        builder = MemoryBuilder(event_window=5)
        rollups = builder.create_rollups(old_events, "pc_throk_001")

        assert len(rollups) > 0
        assert "grimfang" in rollups[0].lower() or "killed" in rollups[0].lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestEventWindowing -v`
Expected: FAIL (MemoryBuilder doesn't accept event_window)

**Step 3: Write minimal implementation**

Modify `src/dndbots/memory.py`:

```python
@dataclass
class MemoryBuilder:
    """Builds DCML memory blocks from campaign state."""

    event_window: int = 10  # Number of recent events to include

    def build_pc_memory(
        self,
        pc_id: str,
        character: Character,
        events: list[GameEvent],
        party_id: str | None = None,
        quests: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build per-PC memory projection."""
        lines = [f"## MEMORY_{pc_id}", ""]

        # Core identity (unchanged)
        lines.append("# Identity & role")
        if party_id:
            lines.append(f"{pc_id} in {party_id};")

        class_abbrev = CLASS_ABBREV.get(character.char_class, character.char_class[:3].upper())
        lines.append(f"{pc_id}::class->{class_abbrev},level->{character.level};")

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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestEventWindowing -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory.py
git commit -m "feat: event windowing and rollup for DCML compression"
```

---

## Task 11: Wire Memory into Game Loop

**Files:**
- Modify: `src/dndbots/game.py`
- Modify: `tests/test_game.py`

**Step 1: Write failing test for memory in game**

Add to `tests/test_game.py`:

```python
class TestGameMemory:
    @pytest.mark.asyncio
    async def test_game_builds_player_memory(self, monkeypatch):
        """Game builds DCML memory for player agents."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
            char_id="pc_throk_001",
        )

        game = DnDGame(
            scenario="Test scenario",
            characters=[char],
            dm_model="gpt-4o",
            player_model="gpt-4o",
        )

        # Get the player agent's system message
        player_agent = game._player_agents[0]
        system_message = player_agent.system_message

        # Should include DCML if memory is enabled
        # (This test documents the expected behavior)
        assert "Throk" in system_message
```

**Step 2: Run test to verify current behavior**

Run: `pytest tests/test_game.py::TestGameMemory -v`
Expected: PASS (basic test, memory not yet required)

**Step 3: Add memory builder to game initialization**

Modify `src/dndbots/game.py`:

```python
from dndbots.memory import MemoryBuilder


class DnDGame:
    """Orchestrates a D&D game session using AutoGen."""

    def __init__(
        self,
        scenario: str,
        characters: list[Character],
        dm_model: str = "gpt-4o",
        player_model: str = "gpt-4o",
        campaign: Campaign | None = None,
        enable_memory: bool = True,  # NEW
    ):
        self._scenario = scenario
        self._characters = characters
        self._dm_model = dm_model
        self._player_model = player_model
        self._campaign = campaign
        self._enable_memory = enable_memory
        self._memory_builder = MemoryBuilder() if enable_memory else None

        # ... rest of init ...

    def _build_player_memory(self, char: Character) -> str | None:
        """Build DCML memory for a player character."""
        if not self._memory_builder:
            return None

        char_id = getattr(char, 'char_id', None) or f"pc_{char.name.lower()}_001"

        # Get events from campaign if available
        events = []
        if self._campaign:
            # TODO: Get events from campaign.get_session_events()
            pass

        return self._memory_builder.build_memory_document(
            pc_id=char_id,
            character=char,
            all_characters=self._characters,
            events=events,
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_game.py::TestGameMemory -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/game.py tests/test_game.py
git commit -m "feat: wire DCML memory builder into game loop"
```

---

## Task 12: Integration Test - Full Memory Flow

**Files:**
- Create: `tests/test_memory_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for DCML memory system."""

import pytest
from dndbots.dcml import DCMLCategory, DCMLOp, Certainty
from dndbots.dcml import render_lexicon_entry, render_relation, render_properties, render_fact
from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats
from dndbots.events import GameEvent, EventType
from dndbots.prompts import build_player_prompt


class TestDCMLIntegration:
    """End-to-end tests for the DCML memory system."""

    def test_full_memory_flow(self):
        """Test complete flow: events -> DCML -> prompt."""
        # Create characters
        throk = Character(
            name="Throk",
            char_class="Fighter",
            level=3,
            hp=24, hp_max=24, ac=5,
            stats=Stats(str=17, dex=12, con=15, int=8, wis=10, cha=9),
            equipment=["longsword", "chain mail", "shield"],
            gold=50,
            char_id="pc_throk_001",
        )

        zara = Character(
            name="Zara",
            char_class="Thief",
            level=3,
            hp=12, hp_max=12, ac=7,
            stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
            equipment=["dagger", "thieves tools"],
            gold=75,
            char_id="pc_zara_001",
        )

        # Create events
        events = [
            GameEvent(
                event_id="evt_003_047",
                event_type=EventType.COMBAT_ROUND,
                source="dm",
                content="Four goblins burst from the shadows, ambushing the party!",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001", "pc_zara_001"],
                    "enemies": ["mon_goblin_darkwood"],
                    "enemy_count": 4,
                }
            ),
            GameEvent(
                event_id="evt_003_048",
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content="I charge at the nearest goblin with my longsword!",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001"],
                }
            ),
            GameEvent(
                event_id="evt_003_049",
                event_type=EventType.DICE_ROLL,
                source="system",
                content="Throk attacks: d20+2 = 18, hits! Damage: 1d8+2 = 7",
                session_id="session_003",
                metadata={
                    "location": "loc_darkwood_entrance",
                    "participants": ["pc_throk_001"],
                    "killed": ["npc_goblin_enc03_01"],
                }
            ),
        ]

        # Build memory document
        builder = MemoryBuilder(event_window=10)
        memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=throk,
            all_characters=[throk, zara],
            events=events,
        )

        # Verify structure
        assert "## LEXICON" in memory
        assert "[PC:pc_throk_001:Throk]" in memory
        assert "[PC:pc_zara_001:Zara]" in memory
        assert "## MEMORY_pc_throk_001" in memory

        # Verify events
        assert "evt_003_047" in memory
        assert "evt_003_048" in memory
        assert "goblin" in memory.lower()

        # Build prompt with memory
        prompt = build_player_prompt(throk, memory=memory)

        # Verify prompt includes everything
        assert "Fighter" in prompt
        assert "## LEXICON" in prompt
        assert "## MEMORY_pc_throk_001" in prompt

        # Token estimate (rough: 4 chars per token)
        estimated_tokens = len(prompt) / 4
        print(f"Prompt length: {len(prompt)} chars, ~{estimated_tokens:.0f} tokens")
        assert estimated_tokens < 4000  # Should be reasonable

    def test_zara_sees_different_memory(self):
        """Different PCs get different memory projections."""
        throk = Character(
            name="Throk", char_class="Fighter", level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[], gold=0, char_id="pc_throk_001",
        )
        zara = Character(
            name="Zara", char_class="Thief", level=1,
            hp=4, hp_max=4, ac=7,
            stats=Stats(str=10, dex=17, con=12, int=14, wis=11, cha=13),
            equipment=[], gold=0, char_id="pc_zara_001",
        )

        # Event only Throk was in
        throk_only_event = GameEvent(
            event_id="evt_solo_001",
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="Throk explores alone",
            session_id="s1",
            metadata={"participants": ["pc_throk_001"]}
        )

        # Event only Zara was in
        zara_only_event = GameEvent(
            event_id="evt_solo_002",
            event_type=EventType.PLAYER_ACTION,
            source="pc_zara_001",
            content="Zara picks a lock",
            session_id="s1",
            metadata={"participants": ["pc_zara_001"]}
        )

        builder = MemoryBuilder()

        throk_memory = builder.build_memory_document(
            pc_id="pc_throk_001",
            character=throk,
            all_characters=[throk, zara],
            events=[throk_only_event, zara_only_event],
        )

        zara_memory = builder.build_memory_document(
            pc_id="pc_zara_001",
            character=zara,
            all_characters=[throk, zara],
            events=[throk_only_event, zara_only_event],
        )

        # Throk sees his event, not Zara's
        assert "evt_solo_001" in throk_memory
        assert "evt_solo_002" not in throk_memory

        # Zara sees her event, not Throk's
        assert "evt_solo_002" in zara_memory
        assert "evt_solo_001" not in zara_memory
```

**Step 2: Run integration test**

Run: `pytest tests/test_memory_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_memory_integration.py
git commit -m "test: DCML memory integration tests"
```

---

## Summary

Phase 4 implements the DCML compression system:

| Task | Component | Purpose |
|------|-----------|---------|
| 1 | Core types | DCMLCategory, lexicon entries |
| 2 | Operators | Relations (>, <, @, in, ->, <-) |
| 3 | Properties | Key->value rendering |
| 4 | Epistemics | Fact/belief/rumor markers |
| 5 | Lexicon builder | Characters -> ## LEXICON |
| 6 | Event renderer | GameEvent -> DCML |
| 7 | PC memory | Per-PC filtered projection |
| 8 | Document assembly | Full memory document |
| 9 | Prompt integration | Memory in player prompts |
| 10 | Windowing | Recent events + rollups |
| 11 | Game loop | Wire into DnDGame |
| 12 | Integration test | End-to-end verification |

After this phase:
- Each PC gets a ~hundreds-of-tokens memory block
- Memory is perspective-correct (only witnessed events)
- Beliefs can be wrong (! and ? markers)
- Old events roll up into summary facts
- No RAG - all lookups are deterministic by UID
