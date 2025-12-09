# Neo4j Phase F: DCML From Graph

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update MemoryBuilder to construct DCML memory from Neo4j graph instead of event logs.

**Architecture:** Add build_from_graph() method that queries Neo4j for a character's witnessed moments, kills, relationships. Render to DCML format for player agent prompts.

**Tech Stack:** MemoryBuilder, Neo4jStore, DCML format

---

## Task 1: Add Graph Query Methods for Memory

**Files:**
- Modify: `src/dndbots/storage/neo4j_store.py`
- Create: `tests/test_neo4j_memory_queries.py`

**Step 1: Write the failing test**

```python
"""Tests for Neo4j memory-related queries."""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set"
)


@pytest.fixture
async def graph_store():
    """Create Neo4j store for testing."""
    from dndbots.storage.neo4j_store import Neo4jStore

    store = Neo4jStore(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    await store.initialize()
    await store.clear_campaign("test_memory")

    yield store

    await store.clear_campaign("test_memory")
    await store.close()


class TestMemoryQueries:
    """Test queries needed for DCML memory building."""

    async def test_get_character_kills(self, graph_store):
        """get_character_kills returns kill relationships with details."""
        # Setup
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="npc_goblin_01",
            name="Goblin Scout",
            char_class="Goblin",
            level=1,
        )
        await graph_store.record_kill(
            campaign_id="test_memory",
            attacker_id="pc_hero",
            target_id="npc_goblin_01",
            weapon="sword",
            damage=8,
            session="session_001",
            turn=5,
            narrative="Clean strike through the heart",
        )

        # Query
        kills = await graph_store.get_character_kills("pc_hero")

        assert len(kills) == 1
        assert kills[0]["target_name"] == "Goblin Scout"
        assert kills[0]["weapon"] == "sword"
        assert kills[0]["narrative"] == "Clean strike through the heart"

    async def test_get_witnessed_moments(self, graph_store):
        """get_witnessed_moments returns moments character was present for."""
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_ally",
            name="Ally",
            char_class="Thief",
            level=1,
        )

        # Hero performs a moment
        moment_id = await graph_store.record_moment(
            campaign_id="test_memory",
            actor_id="pc_hero",
            moment_type="creative",
            description="Hero swings from chandelier",
            session="session_001",
            turn=10,
        )

        # Mark ally as witness
        await graph_store.add_witness(moment_id, "pc_ally")

        # Query ally's witnessed moments
        witnessed = await graph_store.get_witnessed_moments("pc_ally")

        assert len(witnessed) >= 1
        assert any("chandelier" in m.get("description", "") for m in witnessed)

    async def test_get_known_entities(self, graph_store):
        """get_known_entities returns entities character has interacted with."""
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_memory",
            char_id="npc_elena",
            name="Elena",
            char_class="Villager",
            level=1,
        )
        await graph_store.create_location(
            campaign_id="test_memory",
            location_id="loc_village",
            name="Millbrook Village",
        )

        # Create interactions
        await graph_store.create_relationship(
            from_id="pc_hero",
            to_id="npc_elena",
            rel_type="MET",
            properties={"session": "session_001"},
        )
        await graph_store.create_relationship(
            from_id="pc_hero",
            to_id="loc_village",
            rel_type="VISITED",
            properties={"session": "session_001"},
        )

        # Query
        entities = await graph_store.get_known_entities("pc_hero")

        assert len(entities) >= 2
        entity_ids = [e["entity_id"] for e in entities]
        assert "npc_elena" in entity_ids
        assert "loc_village" in entity_ids
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_neo4j_memory_queries.py -v
```

Expected: FAIL - methods don't exist

**Step 3: Implement memory query methods**

Add to `src/dndbots/storage/neo4j_store.py`:

```python
async def get_character_kills(self, char_id: str) -> list[dict]:
    """Get all kills by a character with details.

    Args:
        char_id: Character ID

    Returns:
        List of dicts with target_name, weapon, damage, narrative, session, turn
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (a:Character {char_id: $char_id})-[r:KILLED]->(t:Character)
            RETURN t.name as target_name, t.char_id as target_id,
                   r.weapon as weapon, r.damage as damage,
                   r.narrative as narrative, r.session as session, r.turn as turn
            ORDER BY r.turn DESC
            """,
            char_id=char_id,
        )
        records = await result.data()

    return records

async def add_witness(self, moment_id: str, char_id: str) -> None:
    """Mark a character as witness to a moment.

    Args:
        moment_id: Moment ID
        char_id: Character ID who witnessed
    """
    async with self._driver.session() as session:
        await session.run(
            """
            MATCH (c:Character {char_id: $char_id})
            MATCH (m:Moment {moment_id: $moment_id})
            MERGE (c)-[:WITNESSED]->(m)
            """,
            char_id=char_id,
            moment_id=moment_id,
        )

async def get_witnessed_moments(
    self,
    char_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get moments a character witnessed or performed.

    Args:
        char_id: Character ID
        limit: Max results

    Returns:
        List of moment dicts
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Character {char_id: $char_id})-[:PERFORMED|WITNESSED]->(m:Moment)
            RETURN DISTINCT m
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """,
            char_id=char_id,
            limit=limit,
        )
        records = await result.data()

    return [dict(r["m"]) for r in records]

async def get_known_entities(self, char_id: str) -> list[dict]:
    """Get all entities a character has interacted with.

    Args:
        char_id: Character ID

    Returns:
        List of dicts with entity_id, name, type (character/location/faction)
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Character {char_id: $char_id})-[r]->(e)
            WHERE (e:Character OR e:Location OR e:Faction)
            RETURN DISTINCT
                coalesce(e.char_id, e.location_id, e.faction_id) as entity_id,
                e.name as name,
                CASE
                    WHEN e:Character THEN 'character'
                    WHEN e:Location THEN 'location'
                    WHEN e:Faction THEN 'faction'
                END as entity_type,
                type(r) as relationship
            """,
            char_id=char_id,
        )
        records = await result.data()

    return records
```

**Step 4: Run tests**

```bash
pytest tests/test_neo4j_memory_queries.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/dndbots/storage/neo4j_store.py tests/test_neo4j_memory_queries.py
git commit -m "feat(neo4j): add memory-related query methods"
```

---

## Task 2: Add build_from_graph to MemoryBuilder

**Files:**
- Modify: `src/dndbots/memory.py`
- Create: `tests/test_memory_from_graph.py`

**Step 1: Write the failing test**

```python
"""Tests for MemoryBuilder graph-based memory construction."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from dndbots.memory import MemoryBuilder
from dndbots.models import Character, Stats


class TestMemoryBuilderFromGraph:
    """Test DCML memory building from Neo4j graph."""

    @pytest.mark.asyncio
    async def test_build_from_graph_returns_dcml(self):
        """build_from_graph returns valid DCML format."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[
            {"target_name": "Goblin", "target_id": "npc_goblin_01", "weapon": "sword", "damage": 8},
        ])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[
            {"moment_type": "crit_hit", "description": "Natural 20 on ogre", "session": "s001", "turn": 5},
        ])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[
            {"entity_id": "npc_elena", "name": "Elena", "entity_type": "character"},
            {"entity_id": "loc_caves", "name": "Caves of Chaos", "entity_type": "location"},
        ])
        mock_neo4j.get_character = AsyncMock(return_value={"name": "Hero", "char_class": "Fighter"})

        char = Character(
            name="Hero",
            char_class="Fighter",
            level=3,
            hp=24, hp_max=24, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["sword"],
            gold=100,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        # Check DCML structure
        assert "## LEXICON" in dcml
        assert "## MEMORY_pc_hero" in dcml
        assert "[PC:pc_hero:Hero]" in dcml

    @pytest.mark.asyncio
    async def test_build_from_graph_includes_kills(self):
        """build_from_graph includes kill relationships."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[
            {"target_name": "Grimfang", "target_id": "npc_grimfang", "weapon": "axe", "damage": 15,
             "narrative": "Cleaved in two"},
        ])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[])

        char = Character(
            name="Hero", char_class="Fighter", level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[], gold=0,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        assert "KILLED" in dcml or "killed" in dcml.lower()
        assert "Grimfang" in dcml

    @pytest.mark.asyncio
    async def test_build_from_graph_includes_known_entities_in_lexicon(self):
        """build_from_graph adds known entities to LEXICON."""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_character_kills = AsyncMock(return_value=[])
        mock_neo4j.get_witnessed_moments = AsyncMock(return_value=[])
        mock_neo4j.get_known_entities = AsyncMock(return_value=[
            {"entity_id": "npc_elena", "name": "Elena", "entity_type": "character"},
            {"entity_id": "loc_caves", "name": "Caves of Chaos", "entity_type": "location"},
        ])

        char = Character(
            name="Hero", char_class="Fighter", level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=[], gold=0,
        )

        builder = MemoryBuilder()
        dcml = await builder.build_from_graph(
            pc_id="pc_hero",
            character=char,
            neo4j=mock_neo4j,
        )

        assert "[NPC:npc_elena:Elena]" in dcml
        assert "[LOC:loc_caves:Caves of Chaos]" in dcml
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_memory_from_graph.py -v
```

Expected: FAIL - method doesn't exist

**Step 3: Implement build_from_graph**

Add to `src/dndbots/memory.py`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dndbots.storage.neo4j_store import Neo4jStore


# Add to MemoryBuilder class:

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
```

**Step 4: Add import at top of memory.py**

```python
from dndbots.dcml import DCMLCategory, render_lexicon_entry
```

**Step 5: Run tests**

```bash
pytest tests/test_memory_from_graph.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/dndbots/memory.py tests/test_memory_from_graph.py
git commit -m "feat(memory): add build_from_graph for Neo4j-based DCML"
```

---

## Task 3: Wire Graph Memory into Player Prompts

**Files:**
- Modify: `src/dndbots/game.py`

**Step 1: Update _build_player_memory to use graph**

```python
async def _build_player_memory(self, char: Character) -> str | None:
    """Build DCML memory for a player character.

    Prefers Neo4j graph if available, falls back to event-based.

    Args:
        char: The character to build memory for

    Returns:
        DCML memory document, or None if memory is disabled
    """
    if not self._memory_builder:
        return None

    char_id = getattr(char, 'char_id', None) or f"pc_{char.name.lower()}_001"

    # Use graph-based memory if Neo4j is available
    if self.campaign and self.campaign._neo4j:
        return await self._memory_builder.build_from_graph(
            pc_id=char_id,
            character=char,
            neo4j=self.campaign._neo4j,
        )

    # Fallback to event-based memory
    events = []
    if self.campaign:
        events = await self.campaign.get_session_events()

    return self._memory_builder.build_memory_document(
        pc_id=char_id,
        character=char,
        all_characters=self.characters,
        events=events,
    )
```

**Step 2: Update create_player_agent to accept async memory**

Since `_build_player_memory` is now async, we need to adjust the player creation.
Update `DnDGame.initialize()`:

```python
async def initialize(self) -> None:
    """Async initialization - inject recap, build player memories."""
    # Inject DM recap
    if self.campaign and self.campaign._neo4j:
        recap = await self.campaign.generate_session_recap()
        if recap:
            current_message = self.dm._system_message
            self.dm._system_message = f"{current_message}\n\n{recap}"

    # Build player memories from graph
    if self._memory_builder and self.campaign and self.campaign._neo4j:
        for i, player in enumerate(self.players):
            char = self.characters[i]
            memory = await self._build_player_memory(char)
            if memory:
                # Inject memory into player's system message
                current = player._system_message
                player._system_message = f"{current}\n\n{memory}"
```

**Step 3: Run tests**

```bash
pytest tests/test_game.py -v
```

Expected: All PASS

**Step 4: Commit**

```bash
git add src/dndbots/game.py
git commit -m "feat(game): wire graph-based memory into player prompts"
```

---

## Phase F Complete Checklist

- [ ] Neo4jStore has get_character_kills, get_witnessed_moments, get_known_entities
- [ ] add_witness method links characters to moments
- [ ] MemoryBuilder.build_from_graph() creates DCML from Neo4j
- [ ] LEXICON includes all known entities from graph
- [ ] MEMORY section includes kills and recent moments
- [ ] DnDGame.initialize() injects graph memory into player prompts
- [ ] Fallback to event-based memory when Neo4j unavailable
- [ ] All tests pass

---

## Full Integration Complete

After completing all phases (A-F), the Neo4j integration provides:

1. **Automatic Recording:**
   - Kills, crits, fumbles, clutch saves auto-recorded by Referee
   - Creative moments recorded at Referee discretion

2. **Narrative Management:**
   - DM can introduce NPCs, set factions, enrich moments
   - Query tools for recalling history

3. **Session Continuity:**
   - Recap injected into DM prompt at session start
   - Previous session's key moments and NPCs summarized

4. **Player Memory:**
   - DCML memory built from graph relationships
   - Characters remember their kills and witnessed moments
   - Known entities appear in LEXICON for reference

**To verify full integration:**

```bash
# Run full test suite
pytest tests/ -v

# Start a game session
source .env && dndbots

# After playing, query Neo4j:
# MATCH (m:Moment) RETURN m.moment_type, m.description LIMIT 10
# MATCH (a)-[r:KILLED]->(b) RETURN a.name, b.name, r.weapon
```
