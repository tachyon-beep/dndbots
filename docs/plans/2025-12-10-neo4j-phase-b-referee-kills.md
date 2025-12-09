# Neo4j Phase B: Referee Records Kills

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-record kills and hardcoded triggers (crits, fumbles, clutch saves) to Neo4j graph.

**Architecture:** Extend Neo4jStore with Moment node creation and relationship recording. Hook MechanicsEngine to detect triggers and call recording methods. Pass neo4j reference through to referee tools.

**Tech Stack:** Neo4j, MechanicsEngine, referee_tools.py

---

## Task 1: Add Moment Node and Recording Methods to Neo4jStore

**Files:**
- Modify: `src/dndbots/storage/neo4j_store.py`
- Create: `tests/test_neo4j_moments.py`

**Step 1: Write the failing test**

```python
"""Tests for Neo4j moment recording."""

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
    await store.clear_campaign("test_moments")

    yield store

    await store.clear_campaign("test_moments")
    await store.close()


class TestMomentRecording:
    """Test moment and relationship recording."""

    async def test_record_kill_creates_relationship_and_moment(self, graph_store):
        """record_kill should create KILLED edge and Moment node."""
        # Setup: create attacker and target
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_001",
            name="Hero",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="npc_goblin_001",
            name="Goblin",
            char_class="Goblin",
            level=1,
        )

        # Act
        moment_id = await graph_store.record_kill(
            campaign_id="test_moments",
            attacker_id="pc_hero_001",
            target_id="npc_goblin_001",
            weapon="longsword",
            damage=8,
            session="session_001",
            turn=5,
        )

        # Assert: moment exists
        assert moment_id is not None
        assert moment_id.startswith("moment_")

        # Assert: KILLED relationship exists
        kills = await graph_store.get_relationships("pc_hero_001", "KILLED")
        assert len(kills) == 1
        assert kills[0]["target_name"] == "Goblin"

    async def test_record_kill_includes_moment_reference(self, graph_store):
        """KILLED relationship should reference the Moment node."""
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_002",
            name="Hero2",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="npc_goblin_002",
            name="Goblin2",
            char_class="Goblin",
            level=1,
        )

        moment_id = await graph_store.record_kill(
            campaign_id="test_moments",
            attacker_id="pc_hero_002",
            target_id="npc_goblin_002",
            weapon="axe",
            damage=12,
            session="session_001",
            turn=10,
        )

        # Query the relationship properties
        kills = await graph_store.get_relationships("pc_hero_002", "KILLED")
        assert kills[0]["rel_props"]["moment_id"] == moment_id
        assert kills[0]["rel_props"]["weapon"] == "axe"
        assert kills[0]["rel_props"]["damage"] == 12

    async def test_record_crit_creates_moment(self, graph_store):
        """record_crit should create a Moment node."""
        await graph_store.create_character(
            campaign_id="test_moments",
            char_id="pc_hero_003",
            name="Hero3",
            char_class="Fighter",
            level=1,
        )

        moment_id = await graph_store.record_moment(
            campaign_id="test_moments",
            actor_id="pc_hero_003",
            moment_type="crit_hit",
            description="Natural 20 against the ogre",
            session="session_001",
            turn=15,
        )

        assert moment_id is not None

        # Verify moment can be retrieved
        moment = await graph_store.get_moment(moment_id)
        assert moment is not None
        assert moment["moment_type"] == "crit_hit"
        assert "Natural 20" in moment["description"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_neo4j_moments.py -v
```

Expected: FAIL - `record_kill` method doesn't exist

**Step 3: Implement recording methods in Neo4jStore**

Add to `src/dndbots/storage/neo4j_store.py`:

```python
import uuid
from datetime import datetime


# Add these methods to the Neo4jStore class:

async def record_kill(
    self,
    campaign_id: str,
    attacker_id: str,
    target_id: str,
    weapon: str,
    damage: int,
    session: str,
    turn: int,
    narrative: str = "",
) -> str:
    """Record a kill with KILLED relationship and Moment node.

    Args:
        campaign_id: Campaign identifier
        attacker_id: Character ID of attacker
        target_id: Character ID of target (victim)
        weapon: Weapon used
        damage: Damage dealt
        session: Session ID
        turn: Turn number
        narrative: Optional narrative description

    Returns:
        moment_id of the created Moment node
    """
    moment_id = f"moment_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.utcnow().isoformat()

    async with self._driver.session() as db_session:
        # Create Moment node
        await db_session.run(
            """
            CREATE (m:Moment {
                moment_id: $moment_id,
                campaign_id: $campaign_id,
                moment_type: 'kill',
                session: $session,
                turn: $turn,
                description: $description,
                timestamp: $timestamp,
                narrative: $narrative
            })
            """,
            moment_id=moment_id,
            campaign_id=campaign_id,
            session=session,
            turn=turn,
            description=f"{attacker_id} killed {target_id} with {weapon} for {damage} damage",
            timestamp=timestamp,
            narrative=narrative,
        )

        # Create KILLED relationship with properties
        await db_session.run(
            """
            MATCH (a:Character {char_id: $attacker_id})
            MATCH (t:Character {char_id: $target_id})
            MERGE (a)-[r:KILLED]->(t)
            SET r.moment_id = $moment_id,
                r.weapon = $weapon,
                r.damage = $damage,
                r.session = $session,
                r.turn = $turn,
                r.timestamp = $timestamp,
                r.narrative = $narrative
            """,
            attacker_id=attacker_id,
            target_id=target_id,
            moment_id=moment_id,
            weapon=weapon,
            damage=damage,
            session=session,
            turn=turn,
            timestamp=timestamp,
            narrative=narrative,
        )

        # Link attacker to moment (PERFORMED)
        await db_session.run(
            """
            MATCH (a:Character {char_id: $attacker_id})
            MATCH (m:Moment {moment_id: $moment_id})
            MERGE (a)-[:PERFORMED]->(m)
            """,
            attacker_id=attacker_id,
            moment_id=moment_id,
        )

    return moment_id

async def record_moment(
    self,
    campaign_id: str,
    actor_id: str,
    moment_type: str,
    description: str,
    session: str,
    turn: int,
    narrative: str = "",
    target_id: str | None = None,
) -> str:
    """Record a generic noteworthy moment.

    Args:
        campaign_id: Campaign identifier
        actor_id: Character ID of the actor
        moment_type: Type (crit_hit, crit_fail, clutch_save, creative, etc.)
        description: Mechanical description
        session: Session ID
        turn: Turn number
        narrative: Optional narrative description
        target_id: Optional target character ID

    Returns:
        moment_id of the created Moment node
    """
    moment_id = f"moment_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.utcnow().isoformat()

    async with self._driver.session() as db_session:
        # Create Moment node
        await db_session.run(
            """
            CREATE (m:Moment {
                moment_id: $moment_id,
                campaign_id: $campaign_id,
                moment_type: $moment_type,
                session: $session,
                turn: $turn,
                description: $description,
                timestamp: $timestamp,
                narrative: $narrative
            })
            """,
            moment_id=moment_id,
            campaign_id=campaign_id,
            moment_type=moment_type,
            session=session,
            turn=turn,
            description=description,
            timestamp=timestamp,
            narrative=narrative,
        )

        # Link actor to moment (PERFORMED)
        await db_session.run(
            """
            MATCH (a:Character {char_id: $actor_id})
            MATCH (m:Moment {moment_id: $moment_id})
            MERGE (a)-[:PERFORMED]->(m)
            """,
            actor_id=actor_id,
            moment_id=moment_id,
        )

        # If target specified, create appropriate relationship
        if target_id and moment_type == "crit_hit":
            await db_session.run(
                """
                MATCH (a:Character {char_id: $actor_id})
                MATCH (t:Character {char_id: $target_id})
                MATCH (m:Moment {moment_id: $moment_id})
                MERGE (a)-[r:CRITTED {moment_id: $moment_id}]->(t)
                MERGE (t)-[:WITNESSED]->(m)
                """,
                actor_id=actor_id,
                target_id=target_id,
                moment_id=moment_id,
            )

    return moment_id

async def get_moment(self, moment_id: str) -> dict | None:
    """Get a Moment node by ID."""
    async with self._driver.session() as session:
        result = await session.run(
            "MATCH (m:Moment {moment_id: $moment_id}) RETURN m",
            moment_id=moment_id,
        )
        record = await result.single()

    if not record:
        return None
    return dict(record["m"])

async def get_character_moments(
    self,
    char_id: str,
    moment_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get moments performed by a character.

    Args:
        char_id: Character ID
        moment_type: Optional filter by type
        limit: Max results

    Returns:
        List of moment dicts
    """
    type_filter = "AND m.moment_type = $moment_type" if moment_type else ""

    query = f"""
        MATCH (c:Character {{char_id: $char_id}})-[:PERFORMED]->(m:Moment)
        WHERE true {type_filter}
        RETURN m
        ORDER BY m.timestamp DESC
        LIMIT $limit
    """

    async with self._driver.session() as session:
        result = await session.run(
            query,
            char_id=char_id,
            moment_type=moment_type,
            limit=limit,
        )
        records = await result.data()

    return [dict(r["m"]) for r in records]
```

**Step 4: Add uuid import at top of file**

Ensure the file has:
```python
import uuid
from datetime import datetime
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_neo4j_moments.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/dndbots/storage/neo4j_store.py tests/test_neo4j_moments.py
git commit -m "feat(neo4j): add moment recording (kills, crits)"
```

---

## Task 2: Add Hardcoded Trigger Detection

**Files:**
- Modify: `src/dndbots/mechanics.py`
- Create: `tests/test_mechanics_triggers.py`

**Step 1: Write the failing test**

```python
"""Tests for mechanics trigger detection."""

import pytest
from dndbots.mechanics import MechanicsEngine, CombatTrigger


class TestCombatTriggers:
    """Test detection of noteworthy combat events."""

    def test_detect_kill_trigger(self):
        """Damage reducing HP to 0 or below triggers kill."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant("pc_hero", "Hero", hp=10, ac=5, thac0=19)
        engine.add_combatant("npc_goblin", "Goblin", hp=4, ac=6, thac0=19)

        # Deal lethal damage
        triggers = engine.apply_damage("npc_goblin", 5, source="pc_hero")

        assert CombatTrigger.KILL in triggers
        assert triggers[CombatTrigger.KILL]["attacker"] == "pc_hero"
        assert triggers[CombatTrigger.KILL]["target"] == "npc_goblin"

    def test_detect_overkill_trigger(self):
        """Damage >= 2x remaining HP triggers overkill."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant("pc_hero", "Hero", hp=10, ac=5, thac0=19)
        engine.add_combatant("npc_goblin", "Goblin", hp=4, ac=6, thac0=19)

        # Deal massive damage (10 vs 4 HP = 2.5x)
        triggers = engine.apply_damage("npc_goblin", 10, source="pc_hero")

        assert CombatTrigger.KILL in triggers
        assert CombatTrigger.OVERKILL in triggers

    def test_detect_crit_hit(self):
        """Natural 20 on attack triggers crit_hit."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant("pc_hero", "Hero", hp=10, ac=5, thac0=19)
        engine.add_combatant("npc_goblin", "Goblin", hp=4, ac=6, thac0=19)

        # Check if roll was a natural 20
        triggers = engine.check_attack_triggers(roll=20, attacker="pc_hero", target="npc_goblin")

        assert CombatTrigger.CRIT_HIT in triggers

    def test_detect_crit_fail(self):
        """Natural 1 on attack triggers crit_fail."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant("pc_hero", "Hero", hp=10, ac=5, thac0=19)

        triggers = engine.check_attack_triggers(roll=1, attacker="pc_hero", target="npc_goblin")

        assert CombatTrigger.CRIT_FAIL in triggers

    def test_detect_clutch_save(self):
        """Save made by 1-2 points triggers clutch_save."""
        engine = MechanicsEngine()

        # Needed 14, rolled 15 = margin of 1
        triggers = engine.check_save_triggers(
            roll=15,
            needed=14,
            character="pc_hero",
            save_type="death",
        )

        assert CombatTrigger.CLUTCH_SAVE in triggers

    def test_no_trigger_on_normal_save(self):
        """Normal save (margin > 2) doesn't trigger clutch_save."""
        engine = MechanicsEngine()

        # Needed 14, rolled 18 = margin of 4
        triggers = engine.check_save_triggers(
            roll=18,
            needed=14,
            character="pc_hero",
            save_type="death",
        )

        assert CombatTrigger.CLUTCH_SAVE not in triggers
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_mechanics_triggers.py -v
```

Expected: FAIL - `CombatTrigger` doesn't exist

**Step 3: Add CombatTrigger enum and detection methods**

Add to `src/dndbots/mechanics.py`:

```python
from enum import Enum, auto


class CombatTrigger(Enum):
    """Noteworthy combat events that should be recorded."""
    KILL = auto()
    OVERKILL = auto()
    CRIT_HIT = auto()
    CRIT_FAIL = auto()
    CLUTCH_SAVE = auto()


# Add these methods to MechanicsEngine class:

def apply_damage(
    self,
    target_id: str,
    damage: int,
    source: str | None = None,
) -> dict[CombatTrigger, dict]:
    """Apply damage to a combatant and detect triggers.

    Args:
        target_id: ID of target taking damage
        damage: Amount of damage
        source: ID of damage source (attacker)

    Returns:
        Dict of triggered events with details
    """
    if not self._combat_active:
        return {}

    combatant = self._combatants.get(target_id)
    if not combatant:
        return {}

    triggers = {}
    hp_before = combatant["hp"]

    # Apply damage
    combatant["hp"] = max(0, combatant["hp"] - damage)

    # Check for kill
    if combatant["hp"] <= 0 and hp_before > 0:
        triggers[CombatTrigger.KILL] = {
            "attacker": source,
            "target": target_id,
            "damage": damage,
        }

        # Check for overkill (damage >= 2x remaining HP)
        if damage >= 2 * hp_before:
            triggers[CombatTrigger.OVERKILL] = {
                "attacker": source,
                "target": target_id,
                "damage": damage,
                "hp_was": hp_before,
            }

    return triggers

def check_attack_triggers(
    self,
    roll: int,
    attacker: str,
    target: str,
) -> dict[CombatTrigger, dict]:
    """Check for attack roll triggers.

    Args:
        roll: Natural d20 roll (before modifiers)
        attacker: Attacker ID
        target: Target ID

    Returns:
        Dict of triggered events
    """
    triggers = {}

    if roll == 20:
        triggers[CombatTrigger.CRIT_HIT] = {
            "attacker": attacker,
            "target": target,
            "roll": roll,
        }
    elif roll == 1:
        triggers[CombatTrigger.CRIT_FAIL] = {
            "attacker": attacker,
            "roll": roll,
        }

    return triggers

def check_save_triggers(
    self,
    roll: int,
    needed: int,
    character: str,
    save_type: str,
) -> dict[CombatTrigger, dict]:
    """Check for saving throw triggers.

    Args:
        roll: The d20 roll result
        needed: Target number needed
        character: Character ID
        save_type: Type of save (death, wands, etc.)

    Returns:
        Dict of triggered events
    """
    triggers = {}

    # Clutch save: made it by 1-2 points
    if roll >= needed and (roll - needed) <= 2:
        triggers[CombatTrigger.CLUTCH_SAVE] = {
            "character": character,
            "save_type": save_type,
            "roll": roll,
            "needed": needed,
            "margin": roll - needed,
        }

    return triggers
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mechanics_triggers.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/mechanics.py tests/test_mechanics_triggers.py
git commit -m "feat(mechanics): add combat trigger detection (kill, crit, clutch)"
```

---

## Task 3: Connect Triggers to Neo4j Recording

**Files:**
- Modify: `src/dndbots/referee_tools.py`
- Modify: `src/dndbots/game.py`

**Step 1: Add neo4j parameter to referee tools factory**

Modify `create_referee_tools` in `src/dndbots/referee_tools.py`:

```python
def create_referee_tools(
    engine: MechanicsEngine,
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> list[FunctionTool]:
    """Create referee tools with optional Neo4j recording.

    Args:
        engine: MechanicsEngine instance
        neo4j: Optional Neo4jStore for recording moments
        campaign_id: Campaign ID for recording
        session_id: Session ID for recording

    Returns:
        List of FunctionTool instances
    """
```

**Step 2: Modify roll_damage_tool to record kills**

Inside `create_referee_tools`, update the damage tool:

```python
async def roll_damage_tool(attacker_id: str, target_id: str, weapon: str = "weapon") -> str:
    """Roll damage for a successful attack.

    ... existing docstring ...
    """
    # ... existing damage calculation ...

    # Apply damage and check triggers
    triggers = engine.apply_damage(target_id, total_damage, source=attacker_id)

    # Record to Neo4j if configured
    if neo4j and campaign_id and CombatTrigger.KILL in triggers:
        turn = engine._turn_count if hasattr(engine, '_turn_count') else 0
        await neo4j.record_kill(
            campaign_id=campaign_id,
            attacker_id=attacker_id,
            target_id=target_id,
            weapon=weapon,
            damage=total_damage,
            session=session_id or "unknown",
            turn=turn,
        )

    # ... rest of existing code ...
```

**Step 3: Modify roll_attack_tool to record crits**

```python
async def roll_attack_tool(attacker_id: str, target_id: str, modifier: int = 0) -> str:
    """Roll an attack.

    ... existing docstring ...
    """
    # ... existing roll logic ...

    # Check for crit triggers
    triggers = engine.check_attack_triggers(roll, attacker_id, target_id)

    # Record crits to Neo4j
    if neo4j and campaign_id and CombatTrigger.CRIT_HIT in triggers:
        turn = engine._turn_count if hasattr(engine, '_turn_count') else 0
        await neo4j.record_moment(
            campaign_id=campaign_id,
            actor_id=attacker_id,
            moment_type="crit_hit",
            description=f"Natural 20 against {target_id}",
            session=session_id or "unknown",
            turn=turn,
            target_id=target_id,
        )

    if neo4j and campaign_id and CombatTrigger.CRIT_FAIL in triggers:
        turn = engine._turn_count if hasattr(engine, '_turn_count') else 0
        await neo4j.record_moment(
            campaign_id=campaign_id,
            actor_id=attacker_id,
            moment_type="crit_fail",
            description=f"Natural 1 - fumble!",
            session=session_id or "unknown",
            turn=turn,
        )

    # ... rest of existing code ...
```

**Step 4: Update game.py to pass neo4j to referee tools**

In `src/dndbots/game.py`, modify `create_referee_agent`:

```python
def create_referee_agent(
    engine: MechanicsEngine,
    model: str = "gpt-4o",
    neo4j: "Neo4jStore | None" = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> AssistantAgent:
    """Create the Rules Referee agent.

    Args:
        engine: MechanicsEngine instance for mechanics resolution
        model: OpenAI model to use
        neo4j: Optional Neo4jStore for recording moments
        campaign_id: Campaign ID for recording
        session_id: Session ID for recording
    """
    model_client = OpenAIChatCompletionClient(model=model)
    tools = create_referee_tools(
        engine,
        neo4j=neo4j,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    # ... rest unchanged ...
```

**Step 5: Update DnDGame to pass neo4j to referee**

In `DnDGame.__init__`:

```python
# Create Referee agent if enabled
self.referee = None
if enable_referee:
    neo4j_store = campaign._neo4j if campaign else None
    self.referee = create_referee_agent(
        self.mechanics_engine,
        dm_model,
        neo4j=neo4j_store,
        campaign_id=campaign.campaign_id if campaign else None,
        session_id=campaign.current_session_id if campaign else None,
    )
```

**Step 6: Run all tests**

```bash
pytest tests/test_referee_tools.py tests/test_game.py -v
```

Expected: All tests PASS

**Step 7: Commit**

```bash
git add src/dndbots/referee_tools.py src/dndbots/game.py
git commit -m "feat(referee): auto-record kills and crits to Neo4j"
```

---

## Task 4: Add Turn Counter to MechanicsEngine

**Files:**
- Modify: `src/dndbots/mechanics.py`

**Step 1: Add turn tracking**

In `MechanicsEngine.__init__`:
```python
self._turn_count = 0
```

In `start_combat`:
```python
self._turn_count = 0
```

Add method:
```python
def advance_turn(self) -> int:
    """Advance to next turn and return turn number."""
    self._turn_count += 1
    return self._turn_count

@property
def current_turn(self) -> int:
    """Get current turn number."""
    return self._turn_count
```

**Step 2: Commit**

```bash
git add src/dndbots/mechanics.py
git commit -m "feat(mechanics): add turn counter"
```

---

## Phase B Complete Checklist

- [ ] Neo4jStore has record_kill() and record_moment() methods
- [ ] Moment nodes created with proper schema
- [ ] KILLED relationships include moment_id reference
- [ ] CombatTrigger enum defines all hardcoded triggers
- [ ] MechanicsEngine detects kill, overkill, crit_hit, crit_fail, clutch_save
- [ ] Referee tools auto-record triggers to Neo4j
- [ ] Turn counter tracks combat progression
- [ ] All tests pass

**Next Phase:** C - Referee Prompted Moments
