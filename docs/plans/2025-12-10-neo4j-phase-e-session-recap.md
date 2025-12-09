# Neo4j Phase E: Session Start Recap

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-generate "Previously on..." recap at session start and inject into DM prompt.

**Architecture:** Add generate_session_recap() to Campaign that queries Neo4j for last session's moments and active threads. Inject into DM prompt during game initialization.

**Tech Stack:** Campaign, Neo4jStore, game.py

---

## Task 1: Add Session Tracking to Neo4j

**Files:**
- Modify: `src/dndbots/storage/neo4j_store.py`
- Create: `tests/test_neo4j_recap.py`

**Step 1: Write the failing test**

```python
"""Tests for Neo4j session recap functionality."""

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
    await store.clear_campaign("test_recap")

    yield store

    await store.clear_campaign("test_recap")
    await store.close()


class TestSessionRecap:
    """Test session recap queries."""

    async def test_get_session_moments(self, graph_store):
        """get_session_moments returns moments from a specific session."""
        # Setup: create character and moments in session_001
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )

        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="kill",
            description="Hero killed a goblin",
            session="session_001",
            turn=5,
        )

        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="crit_hit",
            description="Natural 20 against ogre",
            session="session_001",
            turn=10,
        )

        # Create moment in different session
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="creative",
            description="Something in session 2",
            session="session_002",
            turn=1,
        )

        # Query session_001 only
        moments = await graph_store.get_session_moments("test_recap", "session_001")

        assert len(moments) == 2
        assert all(m["session"] == "session_001" for m in moments)

    async def test_get_last_session_id(self, graph_store):
        """get_last_session_id returns most recent session."""
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="pc_hero",
            name="Hero",
            char_class="Fighter",
            level=1,
        )

        # Create moments in multiple sessions
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="test",
            description="Session 1",
            session="session_001",
            turn=1,
        )
        await graph_store.record_moment(
            campaign_id="test_recap",
            actor_id="pc_hero",
            moment_type="test",
            description="Session 2",
            session="session_002",
            turn=1,
        )

        last_session = await graph_store.get_last_session_id("test_recap")

        assert last_session == "session_002"

    async def test_get_active_npcs(self, graph_store):
        """get_active_npcs returns NPCs encountered in session."""
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="npc_grimfang",
            name="Grimfang",
            char_class="Goblin",
            level=2,
        )
        await graph_store.create_character(
            campaign_id="test_recap",
            char_id="npc_elena",
            name="Elena",
            char_class="Villager",
            level=1,
        )

        # Mark NPCs as encountered in session
        await graph_store.mark_npc_encountered(
            "npc_grimfang",
            "session_001",
            status="hostile",
        )
        await graph_store.mark_npc_encountered(
            "npc_elena",
            "session_001",
            status="friendly",
        )

        npcs = await graph_store.get_active_npcs("test_recap", "session_001")

        assert len(npcs) == 2
        names = [n["name"] for n in npcs]
        assert "Grimfang" in names
        assert "Elena" in names
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_neo4j_recap.py -v
```

Expected: FAIL - methods don't exist

**Step 3: Implement session query methods**

Add to `src/dndbots/storage/neo4j_store.py`:

```python
async def get_session_moments(
    self,
    campaign_id: str,
    session_id: str,
) -> list[dict]:
    """Get all moments from a specific session.

    Args:
        campaign_id: Campaign ID
        session_id: Session ID

    Returns:
        List of moment dicts, ordered by turn
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (m:Moment {campaign_id: $campaign_id, session: $session_id})
            RETURN m
            ORDER BY m.turn ASC
            """,
            campaign_id=campaign_id,
            session_id=session_id,
        )
        records = await result.data()

    return [dict(r["m"]) for r in records]

async def get_last_session_id(self, campaign_id: str) -> str | None:
    """Get the most recent session ID for a campaign.

    Args:
        campaign_id: Campaign ID

    Returns:
        Session ID or None if no sessions
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (m:Moment {campaign_id: $campaign_id})
            RETURN DISTINCT m.session as session
            ORDER BY m.session DESC
            LIMIT 1
            """,
            campaign_id=campaign_id,
        )
        record = await result.single()

    return record["session"] if record else None

async def mark_npc_encountered(
    self,
    npc_id: str,
    session_id: str,
    status: str = "neutral",
) -> None:
    """Mark an NPC as encountered in a session.

    Args:
        npc_id: NPC character ID
        session_id: Session ID
        status: Relationship status (friendly, hostile, neutral)
    """
    async with self._driver.session() as session:
        await session.run(
            """
            MATCH (c:Character {char_id: $npc_id})
            SET c.last_encountered = $session_id,
                c.encounter_status = $status
            """,
            npc_id=npc_id,
            session_id=session_id,
            status=status,
        )

async def get_active_npcs(
    self,
    campaign_id: str,
    session_id: str,
) -> list[dict]:
    """Get NPCs encountered in a session.

    Args:
        campaign_id: Campaign ID
        session_id: Session ID

    Returns:
        List of NPC dicts with name, class, status
    """
    async with self._driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Character {campaign_id: $campaign_id})
            WHERE c.last_encountered = $session_id
              AND c.char_id STARTS WITH 'npc_'
            RETURN c.char_id as char_id, c.name as name,
                   c.char_class as char_class, c.encounter_status as status
            """,
            campaign_id=campaign_id,
            session_id=session_id,
        )
        records = await result.data()

    return records
```

**Step 4: Run tests**

```bash
pytest tests/test_neo4j_recap.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/dndbots/storage/neo4j_store.py tests/test_neo4j_recap.py
git commit -m "feat(neo4j): add session query methods for recap"
```

---

## Task 2: Add generate_session_recap to Campaign

**Files:**
- Modify: `src/dndbots/campaign.py`
- Create: `tests/test_campaign_recap.py`

**Step 1: Write the failing test**

```python
"""Tests for Campaign session recap generation."""

import os
import pytest
import tempfile

from dndbots.campaign import Campaign
from dndbots.models import Character, Stats


# Skip if Neo4j not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set"
)


@pytest.fixture
def neo4j_config():
    return {
        "uri": os.getenv("NEO4J_URI"),
        "username": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", ""),
    }


@pytest.fixture
async def campaign_with_history(neo4j_config):
    """Create campaign with some session history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        campaign = Campaign(
            campaign_id="test_recap_campaign",
            name="Test Campaign",
            db_path=f"{tmpdir}/test.db",
            neo4j_config=neo4j_config,
        )
        await campaign.initialize()

        # Add a character
        char = Character(
            name="TestHero",
            char_class="Fighter",
            level=1,
            hp=10, hp_max=10, ac=5,
            stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
            equipment=["sword"],
            gold=50,
        )
        await campaign.add_character(char)

        # Simulate session 001 with some moments
        if campaign._neo4j:
            await campaign._neo4j.record_kill(
                campaign_id="test_recap_campaign",
                attacker_id="pc_testhero_001",
                target_id="npc_goblin_001",
                weapon="sword",
                damage=8,
                session="session_test_recap_campaign_001",
                turn=5,
            )
            await campaign._neo4j.record_moment(
                campaign_id="test_recap_campaign",
                actor_id="pc_testhero_001",
                moment_type="crit_hit",
                description="Natural 20 against the ogre",
                session="session_test_recap_campaign_001",
                turn=10,
            )

        yield campaign

        # Cleanup
        if campaign._neo4j:
            await campaign._neo4j.clear_campaign("test_recap_campaign")
        await campaign.close()


class TestCampaignRecap:
    """Test Campaign session recap generation."""

    async def test_has_previous_session(self, campaign_with_history):
        """has_previous_session returns True when history exists."""
        has_history = await campaign_with_history.has_previous_session()
        assert has_history is True

    async def test_generate_session_recap(self, campaign_with_history):
        """generate_session_recap returns formatted recap."""
        recap = await campaign_with_history.generate_session_recap()

        assert recap is not None
        assert "PREVIOUSLY" in recap or "Previously" in recap
        # Should mention the kill
        assert "kill" in recap.lower() or "killed" in recap.lower()

    async def test_generate_session_recap_empty_campaign(self, neo4j_config):
        """generate_session_recap returns None for empty campaign."""
        with tempfile.TemporaryDirectory() as tmpdir:
            campaign = Campaign(
                campaign_id="test_empty_recap",
                name="Empty Campaign",
                db_path=f"{tmpdir}/test.db",
                neo4j_config=neo4j_config,
            )
            await campaign.initialize()

            recap = await campaign.generate_session_recap()

            assert recap is None

            if campaign._neo4j:
                await campaign._neo4j.clear_campaign("test_empty_recap")
            await campaign.close()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_campaign_recap.py -v
```

Expected: FAIL - methods don't exist

**Step 3: Implement recap methods in Campaign**

Add to `src/dndbots/campaign.py`:

```python
async def has_previous_session(self) -> bool:
    """Check if campaign has any previous session history.

    Returns:
        True if there are recorded moments/events
    """
    if not self._neo4j:
        return False

    last_session = await self._neo4j.get_last_session_id(self.campaign_id)
    return last_session is not None

async def generate_session_recap(self) -> str | None:
    """Generate a recap of the previous session for DM context.

    Returns:
        Formatted recap string, or None if no history
    """
    if not self._neo4j:
        return None

    last_session = await self._neo4j.get_last_session_id(self.campaign_id)
    if not last_session:
        return None

    # Get moments from last session
    moments = await self._neo4j.get_session_moments(self.campaign_id, last_session)
    if not moments:
        return None

    # Get active NPCs
    npcs = await self._neo4j.get_active_npcs(self.campaign_id, last_session)

    # Build recap
    lines = [f"=== PREVIOUSLY ({last_session}) ==="]
    lines.append("")

    # Key moments
    if moments:
        lines.append("Key moments:")
        for m in moments[:10]:  # Limit to 10 most important
            moment_type = m.get("moment_type", "event")
            description = m.get("description", "")
            narrative = m.get("narrative", "")

            if narrative:
                lines.append(f"- [{moment_type}] {narrative}")
            else:
                lines.append(f"- [{moment_type}] {description}")
        lines.append("")

    # Active threads (NPCs)
    if npcs:
        lines.append("Active NPCs:")
        for npc in npcs:
            status = npc.get("status", "unknown")
            name = npc.get("name", "Unknown")
            lines.append(f"- {name} ({status})")
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests**

```bash
pytest tests/test_campaign_recap.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/dndbots/campaign.py tests/test_campaign_recap.py
git commit -m "feat(campaign): add session recap generation"
```

---

## Task 3: Inject Recap into DM Prompt

**Files:**
- Modify: `src/dndbots/game.py`

**Step 1: Update DnDGame to inject recap**

In `DnDGame.__init__`, after creating the DM agent:

```python
# Inject session recap if available
if campaign:
    import asyncio
    # Note: We need to handle this carefully since __init__ is sync
    # Option 1: Make initialization async
    # Option 2: Store for later injection
    self._pending_recap = True
else:
    self._pending_recap = False
```

Better approach - add an async `initialize` method:

```python
async def initialize(self) -> None:
    """Async initialization - inject recap into DM context."""
    if self.campaign and self.campaign._neo4j:
        recap = await self.campaign.generate_session_recap()
        if recap:
            # Update DM's system message
            current_message = self.dm._system_message
            self.dm._system_message = f"{current_message}\n\n{recap}"
```

**Step 2: Update run() to call initialize**

In `DnDGame.run()`:

```python
async def run(self) -> None:
    """Run the game session."""
    # Initialize (inject recap, etc.)
    await self.initialize()

    # Start the event bus
    await self._event_bus.start()
    # ... rest unchanged ...
```

**Step 3: Add test**

Add to `tests/test_game.py`:

```python
@pytest.mark.asyncio
async def test_game_injects_recap_into_dm(self, monkeypatch):
    """DnDGame injects session recap into DM prompt."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # Mock campaign with recap
    mock_campaign = AsyncMock()
    mock_campaign._neo4j = MagicMock()
    mock_campaign.campaign_id = "test"
    mock_campaign.current_session_id = "session_001"
    mock_campaign.generate_session_recap = AsyncMock(
        return_value="=== PREVIOUSLY ===\n- Hero killed a goblin"
    )

    char = Character(
        name="Hero", char_class="Fighter", level=1,
        hp=10, hp_max=10, ac=5,
        stats=Stats(str=14, dex=12, con=13, int=10, wis=11, cha=9),
        equipment=["sword"], gold=50,
    )

    game = DnDGame(
        scenario="Test scenario",
        characters=[char],
        campaign=mock_campaign,
    )

    await game.initialize()

    # Verify recap was injected
    assert "PREVIOUSLY" in game.dm._system_message
    assert "goblin" in game.dm._system_message
```

**Step 4: Run tests**

```bash
pytest tests/test_game.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/dndbots/game.py tests/test_game.py
git commit -m "feat(game): inject session recap into DM prompt"
```

---

## Phase E Complete Checklist

- [ ] Neo4jStore has get_session_moments, get_last_session_id, get_active_npcs
- [ ] Campaign.has_previous_session() checks for history
- [ ] Campaign.generate_session_recap() formats recap
- [ ] DnDGame.initialize() injects recap into DM prompt
- [ ] Recap includes key moments and active NPCs
- [ ] All tests pass

**Next Phase:** F - DCML From Graph
