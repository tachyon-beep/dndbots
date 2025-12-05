# Phase 2: Persistence Layer

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SQLite for document storage (events, characters, sessions) and Neo4j for relationship tracking, enabling campaigns to persist across sessions.

**Architecture:** Hybrid storage - SQLite JSONB for narrative blobs and structured data, Neo4j for entity relationships and graph queries. Event-sourced design where game events are the source of truth.

**Tech Stack:** SQLite (via aiosqlite for async), Neo4j (via neo4j Python driver), Pydantic for schemas

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add persistence dependencies to pyproject.toml**

Add to the `dependencies` list:

```toml
dependencies = [
    "autogen-agentchat>=0.4.0",
    "autogen-ext[openai]>=0.4.0",
    "python-dotenv>=1.0.0",
    "aiosqlite>=0.19.0",
    "neo4j>=5.14.0",
    "pydantic>=2.5.0",
]
```

**Step 2: Reinstall package**

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

**Step 3: Verify installation**

```bash
python -c "import aiosqlite, neo4j, pydantic; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add persistence dependencies (aiosqlite, neo4j, pydantic)"
```

---

## Task 2: Event Schema

**Files:**
- Create: `src/dndbots/events.py`
- Create: `tests/test_events.py`

**Step 1: Write the failing test**

```python
"""Tests for game event schemas."""

import pytest
from datetime import datetime

from dndbots.events import GameEvent, EventType


class TestGameEvent:
    def test_create_narration_event(self):
        event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="The goblin snarls at you.",
            session_id="session_001",
        )
        assert event.event_type == EventType.DM_NARRATION
        assert event.source == "dm"
        assert event.timestamp is not None

    def test_create_player_action_event(self):
        event = GameEvent(
            event_type=EventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I attack the goblin with my sword.",
            session_id="session_001",
        )
        assert event.event_type == EventType.PLAYER_ACTION

    def test_create_dice_roll_event(self):
        event = GameEvent(
            event_type=EventType.DICE_ROLL,
            source="system",
            content="Attack roll",
            session_id="session_001",
            metadata={
                "roll": 17,
                "modifier": 3,
                "total": 20,
                "purpose": "attack",
                "target_ac": 6,
                "hit": True,
            },
        )
        assert event.metadata["hit"] is True
        assert event.metadata["total"] == 20

    def test_event_to_dict(self):
        event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="Test content",
            session_id="session_001",
        )
        d = event.to_dict()
        assert d["event_type"] == "dm_narration"
        assert d["source"] == "dm"
        assert "timestamp" in d

    def test_event_from_dict(self):
        data = {
            "event_type": "player_action",
            "source": "pc_throk_001",
            "content": "I search the room.",
            "session_id": "session_001",
            "timestamp": "2025-12-06T10:30:00",
            "metadata": {},
        }
        event = GameEvent.from_dict(data)
        assert event.event_type == EventType.PLAYER_ACTION
        assert event.source == "pc_throk_001"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_events.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dndbots.events'`

**Step 3: Write minimal implementation**

```python
"""Game event schemas for persistence."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of game events."""
    DM_NARRATION = "dm_narration"
    PLAYER_ACTION = "player_action"
    DICE_ROLL = "dice_roll"
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    DAMAGE = "damage"
    DEATH = "death"
    LOOT = "loot"
    QUEST_UPDATE = "quest_update"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class GameEvent:
    """A single game event for persistence and replay."""

    event_type: EventType
    source: str  # "dm", "system", or character UID like "pc_throk_001"
    content: str
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str | None = None  # Set by storage layer

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameEvent":
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id"),
            event_type=EventType(data["event_type"]),
            source=data["source"],
            content=data["content"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_events.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/events.py tests/test_events.py
git commit -m "feat: GameEvent schema with EventType enum"
```

---

## Task 3: SQLite Document Store

**Files:**
- Create: `src/dndbots/storage/sqlite_store.py`
- Create: `src/dndbots/storage/__init__.py`
- Create: `tests/test_sqlite_store.py`

**Step 1: Write the failing test**

```python
"""Tests for SQLite document store."""

import pytest
import tempfile
import os
from pathlib import Path

from dndbots.storage.sqlite_store import SQLiteStore
from dndbots.events import GameEvent, EventType
from dndbots.models import Character, Stats


@pytest.fixture
async def store():
    """Create a temporary SQLite store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SQLiteStore(str(db_path))
        await store.initialize()
        yield store
        await store.close()


class TestSQLiteStore:
    @pytest.mark.asyncio
    async def test_save_and_load_event(self, store):
        event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="The cave entrance looms before you.",
            session_id="session_001",
        )

        event_id = await store.save_event(event)
        assert event_id is not None

        loaded = await store.get_event(event_id)
        assert loaded is not None
        assert loaded.content == event.content
        assert loaded.event_type == event.event_type

    @pytest.mark.asyncio
    async def test_get_session_events(self, store):
        # Save multiple events
        for i in range(5):
            event = GameEvent(
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i}",
                session_id="session_001",
            )
            await store.save_event(event)

        # Save event to different session
        other_event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="Other session",
            session_id="session_002",
        )
        await store.save_event(other_event)

        # Get only session_001 events
        events = await store.get_session_events("session_001")
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_save_and_load_character(self, store):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword", "chain mail"],
            gold=25,
        )

        char_id = await store.save_character("campaign_001", char)
        assert char_id is not None

        loaded = await store.get_character(char_id)
        assert loaded is not None
        assert loaded.name == "Throk"
        assert loaded.stats.str == 16

    @pytest.mark.asyncio
    async def test_get_campaign_characters(self, store):
        char1 = Character(
            name="Throk", char_class="Fighter", level=1,
            hp=8, hp_max=8, ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=[], gold=0,
        )
        char2 = Character(
            name="Zara", char_class="Thief", level=1,
            hp=4, hp_max=4, ac=7,
            stats=Stats(str=10, dex=17, con=12, int=14, wis=10, cha=13),
            equipment=[], gold=0,
        )

        await store.save_character("campaign_001", char1)
        await store.save_character("campaign_001", char2)

        characters = await store.get_campaign_characters("campaign_001")
        assert len(characters) == 2
        names = {c.name for c in characters}
        assert names == {"Throk", "Zara"}
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_sqlite_store.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Create storage package init**

```python
"""Storage backends for DnDBots."""

from dndbots.storage.sqlite_store import SQLiteStore

__all__ = ["SQLiteStore"]
```

**Step 4: Write SQLite store implementation**

```python
"""SQLite document store for events and characters."""

import json
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from dndbots.events import GameEvent
from dndbots.models import Character, Stats


class SQLiteStore:
    """Async SQLite store for game documents."""

    def __init__(self, db_path: str):
        """Initialize store with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize database and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id);

            CREATE TABLE IF NOT EXISTS characters (
                char_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                name TEXT NOT NULL,
                data TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_characters_campaign
                ON characters(campaign_id);

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                summary TEXT
            );
        """)
        await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # Event methods

    async def save_event(self, event: GameEvent) -> str:
        """Save a game event and return its ID."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        event_id = event.event_id or f"evt_{uuid.uuid4().hex[:12]}"

        await self._conn.execute(
            """
            INSERT INTO events (event_id, event_type, source, content,
                               session_id, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event.event_type.value,
                event.source,
                event.content,
                event.session_id,
                event.timestamp.isoformat(),
                json.dumps(event.metadata),
            ),
        )
        await self._conn.commit()
        return event_id

    async def get_event(self, event_id: str) -> GameEvent | None:
        """Get an event by ID."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        async with self._conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        return GameEvent.from_dict({
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "source": row["source"],
            "content": row["content"],
            "session_id": row["session_id"],
            "timestamp": row["timestamp"],
            "metadata": json.loads(row["metadata"]),
        })

    async def get_session_events(
        self, session_id: str, limit: int | None = None
    ) -> list[GameEvent]:
        """Get all events for a session, ordered by timestamp."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        query = """
            SELECT * FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"

        async with self._conn.execute(query, (session_id,)) as cursor:
            rows = await cursor.fetchall()

        return [
            GameEvent.from_dict({
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "source": row["source"],
                "content": row["content"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "metadata": json.loads(row["metadata"]),
            })
            for row in rows
        ]

    # Character methods

    async def save_character(self, campaign_id: str, char: Character) -> str:
        """Save a character and return its ID."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        char_id = f"pc_{char.name.lower()}_{uuid.uuid4().hex[:4]}"

        # Serialize character to JSON
        char_data = {
            "name": char.name,
            "char_class": char.char_class,
            "level": char.level,
            "hp": char.hp,
            "hp_max": char.hp_max,
            "ac": char.ac,
            "stats": {
                "str": char.stats.str,
                "dex": char.stats.dex,
                "con": char.stats.con,
                "int": char.stats.int,
                "wis": char.stats.wis,
                "cha": char.stats.cha,
            },
            "equipment": char.equipment,
            "gold": char.gold,
        }

        await self._conn.execute(
            """
            INSERT INTO characters (char_id, campaign_id, name, data)
            VALUES (?, ?, ?, ?)
            """,
            (char_id, campaign_id, char.name, json.dumps(char_data)),
        )
        await self._conn.commit()
        return char_id

    async def get_character(self, char_id: str) -> Character | None:
        """Get a character by ID."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        async with self._conn.execute(
            "SELECT * FROM characters WHERE char_id = ?", (char_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        data = json.loads(row["data"])
        return Character(
            name=data["name"],
            char_class=data["char_class"],
            level=data["level"],
            hp=data["hp"],
            hp_max=data["hp_max"],
            ac=data["ac"],
            stats=Stats(**data["stats"]),
            equipment=data["equipment"],
            gold=data["gold"],
        )

    async def get_campaign_characters(self, campaign_id: str) -> list[Character]:
        """Get all characters for a campaign."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        async with self._conn.execute(
            "SELECT * FROM characters WHERE campaign_id = ?", (campaign_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        characters = []
        for row in rows:
            data = json.loads(row["data"])
            characters.append(Character(
                name=data["name"],
                char_class=data["char_class"],
                level=data["level"],
                hp=data["hp"],
                hp_max=data["hp_max"],
                ac=data["ac"],
                stats=Stats(**data["stats"]),
                equipment=data["equipment"],
                gold=data["gold"],
            ))
        return characters

    async def update_character(self, char_id: str, char: Character) -> None:
        """Update an existing character."""
        if not self._conn:
            raise RuntimeError("Store not initialized")

        char_data = {
            "name": char.name,
            "char_class": char.char_class,
            "level": char.level,
            "hp": char.hp,
            "hp_max": char.hp_max,
            "ac": char.ac,
            "stats": {
                "str": char.stats.str,
                "dex": char.stats.dex,
                "con": char.stats.con,
                "int": char.stats.int,
                "wis": char.stats.wis,
                "cha": char.stats.cha,
            },
            "equipment": char.equipment,
            "gold": char.gold,
        }

        await self._conn.execute(
            "UPDATE characters SET name = ?, data = ? WHERE char_id = ?",
            (char.name, json.dumps(char_data), char_id),
        )
        await self._conn.commit()
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_sqlite_store.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/dndbots/storage/ tests/test_sqlite_store.py
git commit -m "feat: SQLite store for events and characters"
```

---

## Task 4: Neo4j Graph Store

**Files:**
- Create: `src/dndbots/storage/neo4j_store.py`
- Modify: `src/dndbots/storage/__init__.py`
- Create: `tests/test_neo4j_store.py`

**Note:** These tests require a running Neo4j instance. Tests will be skipped if Neo4j is not available.

**Step 1: Write the failing test**

```python
"""Tests for Neo4j graph store."""

import pytest
import os

# Skip all tests if NEO4J_URI not set
pytestmark = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set - skipping Neo4j tests"
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

    # Clean test data
    await store.clear_campaign("test_campaign")

    yield store

    # Cleanup
    await store.clear_campaign("test_campaign")
    await store.close()


class TestNeo4jStore:
    @pytest.mark.asyncio
    async def test_create_character_node(self, graph_store):
        char_id = await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        assert char_id == "pc_throk_001"

        # Verify node exists
        char = await graph_store.get_character("pc_throk_001")
        assert char is not None
        assert char["name"] == "Throk"

    @pytest.mark.asyncio
    async def test_create_location_node(self, graph_store):
        loc_id = await graph_store.create_location(
            campaign_id="test_campaign",
            location_id="loc_caves_001",
            name="Caves of Chaos",
            description="A dark cave entrance",
        )
        assert loc_id == "loc_caves_001"

    @pytest.mark.asyncio
    async def test_create_relationship(self, graph_store):
        # Create nodes
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="npc_goblin_001",
            name="Grimfang",
            char_class="Goblin",
            level=2,
        )

        # Create relationship
        await graph_store.create_relationship(
            from_id="pc_throk_001",
            to_id="npc_goblin_001",
            rel_type="KILLED",
            properties={"session": "session_001", "weapon": "longsword"},
        )

        # Query relationships
        killed = await graph_store.get_relationships(
            char_id="pc_throk_001",
            rel_type="KILLED",
        )
        assert len(killed) == 1
        assert killed[0]["target_name"] == "Grimfang"

    @pytest.mark.asyncio
    async def test_character_at_location(self, graph_store):
        await graph_store.create_character(
            campaign_id="test_campaign",
            char_id="pc_throk_001",
            name="Throk",
            char_class="Fighter",
            level=1,
        )
        await graph_store.create_location(
            campaign_id="test_campaign",
            location_id="loc_caves_001",
            name="Caves of Chaos",
        )

        await graph_store.set_character_location(
            char_id="pc_throk_001",
            location_id="loc_caves_001",
        )

        location = await graph_store.get_character_location("pc_throk_001")
        assert location is not None
        assert location["name"] == "Caves of Chaos"
```

**Step 2: Run test to verify it fails (or skips)**

```bash
pytest tests/test_neo4j_store.py -v
```

Expected: Either SKIP (no Neo4j) or FAIL (module not found)

**Step 3: Write Neo4j store implementation**

```python
"""Neo4j graph store for entity relationships."""

from typing import Any

from neo4j import AsyncGraphDatabase


class Neo4jStore:
    """Async Neo4j store for game entity relationships."""

    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI (e.g., bolt://localhost:7687)
            username: Neo4j username
            password: Neo4j password
        """
        self._driver = AsyncGraphDatabase.driver(
            uri, auth=(username, password)
        )

    async def initialize(self) -> None:
        """Verify connection and create indexes."""
        async with self._driver.session() as session:
            # Create indexes for common lookups
            await session.run("""
                CREATE INDEX char_id IF NOT EXISTS
                FOR (c:Character) ON (c.char_id)
            """)
            await session.run("""
                CREATE INDEX loc_id IF NOT EXISTS
                FOR (l:Location) ON (l.location_id)
            """)
            await session.run("""
                CREATE INDEX campaign_id IF NOT EXISTS
                FOR (n) ON (n.campaign_id)
            """)

    async def close(self) -> None:
        """Close the driver connection."""
        await self._driver.close()

    async def clear_campaign(self, campaign_id: str) -> None:
        """Delete all nodes and relationships for a campaign (for testing)."""
        async with self._driver.session() as session:
            await session.run(
                "MATCH (n {campaign_id: $campaign_id}) DETACH DELETE n",
                campaign_id=campaign_id,
            )

    # Character nodes

    async def create_character(
        self,
        campaign_id: str,
        char_id: str,
        name: str,
        char_class: str,
        level: int,
        **properties,
    ) -> str:
        """Create a character node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (c:Character {char_id: $char_id})
                SET c.campaign_id = $campaign_id,
                    c.name = $name,
                    c.char_class = $char_class,
                    c.level = $level,
                    c += $properties
                """,
                char_id=char_id,
                campaign_id=campaign_id,
                name=name,
                char_class=char_class,
                level=level,
                properties=properties,
            )
        return char_id

    async def get_character(self, char_id: str) -> dict[str, Any] | None:
        """Get character node by ID."""
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (c:Character {char_id: $char_id}) RETURN c",
                char_id=char_id,
            )
            record = await result.single()

        if not record:
            return None
        return dict(record["c"])

    # Location nodes

    async def create_location(
        self,
        campaign_id: str,
        location_id: str,
        name: str,
        description: str = "",
        **properties,
    ) -> str:
        """Create a location node."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (l:Location {location_id: $location_id})
                SET l.campaign_id = $campaign_id,
                    l.name = $name,
                    l.description = $description,
                    l += $properties
                """,
                location_id=location_id,
                campaign_id=campaign_id,
                name=name,
                description=description,
                properties=properties,
            )
        return location_id

    # Relationships

    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a relationship between two nodes.

        Args:
            from_id: Source node ID (char_id or location_id)
            to_id: Target node ID
            rel_type: Relationship type (e.g., KILLED, ALLIED_WITH, LOCATED_AT)
            properties: Optional relationship properties
        """
        props = properties or {}
        async with self._driver.session() as session:
            # Find nodes by any ID type
            await session.run(
                f"""
                MATCH (a), (b)
                WHERE (a.char_id = $from_id OR a.location_id = $from_id)
                  AND (b.char_id = $to_id OR b.location_id = $to_id)
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $properties
                """,
                from_id=from_id,
                to_id=to_id,
                properties=props,
            )

    async def get_relationships(
        self,
        char_id: str,
        rel_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Get relationships for a character.

        Args:
            char_id: Character ID
            rel_type: Optional relationship type filter
            direction: "outgoing", "incoming", or "both"
        """
        if direction == "outgoing":
            pattern = "(c)-[r]->(target)"
        elif direction == "incoming":
            pattern = "(c)<-[r]-(target)"
        else:
            pattern = "(c)-[r]-(target)"

        type_filter = f":{rel_type}" if rel_type else ""

        query = f"""
            MATCH (c:Character {{char_id: $char_id}}){pattern.replace('[r]', f'[r{type_filter}]')}
            RETURN type(r) as rel_type, properties(r) as rel_props,
                   target.name as target_name,
                   coalesce(target.char_id, target.location_id) as target_id
        """

        async with self._driver.session() as session:
            result = await session.run(query, char_id=char_id)
            records = await result.data()

        return records

    async def set_character_location(
        self, char_id: str, location_id: str
    ) -> None:
        """Set a character's current location (replaces existing)."""
        async with self._driver.session() as session:
            # Remove existing LOCATED_AT relationship
            await session.run(
                """
                MATCH (c:Character {char_id: $char_id})-[r:LOCATED_AT]->()
                DELETE r
                """,
                char_id=char_id,
            )
            # Create new relationship
            await session.run(
                """
                MATCH (c:Character {char_id: $char_id})
                MATCH (l:Location {location_id: $location_id})
                MERGE (c)-[:LOCATED_AT]->(l)
                """,
                char_id=char_id,
                location_id=location_id,
            )

    async def get_character_location(
        self, char_id: str
    ) -> dict[str, Any] | None:
        """Get a character's current location."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Character {char_id: $char_id})-[:LOCATED_AT]->(l:Location)
                RETURN l
                """,
                char_id=char_id,
            )
            record = await result.single()

        if not record:
            return None
        return dict(record["l"])
```

**Step 4: Update storage __init__.py**

```python
"""Storage backends for DnDBots."""

from dndbots.storage.sqlite_store import SQLiteStore
from dndbots.storage.neo4j_store import Neo4jStore

__all__ = ["SQLiteStore", "Neo4jStore"]
```

**Step 5: Run test (will skip without Neo4j)**

```bash
pytest tests/test_neo4j_store.py -v
```

Expected: All tests SKIP (unless Neo4j is running)

**Step 6: Commit**

```bash
git add src/dndbots/storage/ tests/test_neo4j_store.py
git commit -m "feat: Neo4j store for entity relationships"
```

---

## Task 5: Campaign Manager

**Files:**
- Create: `src/dndbots/campaign.py`
- Create: `tests/test_campaign.py`

**Step 1: Write the failing test**

```python
"""Tests for campaign manager."""

import pytest
import tempfile
from pathlib import Path

from dndbots.campaign import Campaign
from dndbots.models import Character, Stats
from dndbots.events import GameEvent, EventType


@pytest.fixture
async def campaign():
    """Create a test campaign with temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "campaign.db"
        campaign = Campaign(
            campaign_id="test_campaign_001",
            name="Test Campaign",
            db_path=str(db_path),
        )
        await campaign.initialize()
        yield campaign
        await campaign.close()


class TestCampaign:
    @pytest.mark.asyncio
    async def test_campaign_creation(self, campaign):
        assert campaign.campaign_id == "test_campaign_001"
        assert campaign.name == "Test Campaign"

    @pytest.mark.asyncio
    async def test_add_character(self, campaign):
        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )

        char_id = await campaign.add_character(char)
        assert char_id is not None
        assert "throk" in char_id.lower()

        # Should be retrievable
        characters = await campaign.get_characters()
        assert len(characters) == 1
        assert characters[0].name == "Throk"

    @pytest.mark.asyncio
    async def test_start_session(self, campaign):
        session_id = await campaign.start_session()
        assert session_id is not None
        assert campaign.current_session_id == session_id

    @pytest.mark.asyncio
    async def test_record_event(self, campaign):
        await campaign.start_session()

        event = GameEvent(
            event_type=EventType.DM_NARRATION,
            source="dm",
            content="The adventure begins!",
            session_id=campaign.current_session_id,
        )

        event_id = await campaign.record_event(event)
        assert event_id is not None

        # Should be in session events
        events = await campaign.get_session_events()
        assert len(events) == 1
        assert events[0].content == "The adventure begins!"

    @pytest.mark.asyncio
    async def test_get_recent_events(self, campaign):
        await campaign.start_session()

        # Record several events
        for i in range(10):
            event = GameEvent(
                event_type=EventType.PLAYER_ACTION,
                source="pc_throk_001",
                content=f"Action {i}",
                session_id=campaign.current_session_id,
            )
            await campaign.record_event(event)

        # Get last 5
        recent = await campaign.get_recent_events(limit=5)
        assert len(recent) == 5
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_campaign.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write Campaign manager implementation**

```python
"""Campaign manager for coordinating storage and game state."""

import uuid
from datetime import datetime
from typing import Any

from dndbots.events import GameEvent, EventType
from dndbots.models import Character
from dndbots.storage.sqlite_store import SQLiteStore


class Campaign:
    """Manages a D&D campaign's persistent state."""

    def __init__(
        self,
        campaign_id: str,
        name: str,
        db_path: str,
        neo4j_config: dict[str, str] | None = None,
    ):
        """Initialize a campaign.

        Args:
            campaign_id: Unique campaign identifier
            name: Human-readable campaign name
            db_path: Path to SQLite database
            neo4j_config: Optional Neo4j connection config
                         {"uri": "...", "username": "...", "password": "..."}
        """
        self.campaign_id = campaign_id
        self.name = name
        self._db_path = db_path
        self._neo4j_config = neo4j_config

        self._sqlite: SQLiteStore | None = None
        self._neo4j = None  # Optional, for when Neo4j is configured

        self.current_session_id: str | None = None

    async def initialize(self) -> None:
        """Initialize storage backends."""
        self._sqlite = SQLiteStore(self._db_path)
        await self._sqlite.initialize()

        if self._neo4j_config:
            from dndbots.storage.neo4j_store import Neo4jStore
            self._neo4j = Neo4jStore(**self._neo4j_config)
            await self._neo4j.initialize()

    async def close(self) -> None:
        """Close all storage connections."""
        if self._sqlite:
            await self._sqlite.close()
        if self._neo4j:
            await self._neo4j.close()

    # Session management

    async def start_session(self) -> str:
        """Start a new game session."""
        session_num = 1  # TODO: Track session count
        self.current_session_id = f"session_{self.campaign_id}_{session_num:03d}"

        # Record session start event
        event = GameEvent(
            event_type=EventType.SESSION_START,
            source="system",
            content=f"Session started for campaign {self.name}",
            session_id=self.current_session_id,
        )
        await self.record_event(event)

        return self.current_session_id

    async def end_session(self, summary: str = "") -> None:
        """End the current session."""
        if not self.current_session_id:
            return

        event = GameEvent(
            event_type=EventType.SESSION_END,
            source="system",
            content=summary or "Session ended",
            session_id=self.current_session_id,
        )
        await self.record_event(event)
        self.current_session_id = None

    # Character management

    async def add_character(self, char: Character) -> str:
        """Add a character to the campaign."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")

        char_id = await self._sqlite.save_character(self.campaign_id, char)

        # Also add to graph if Neo4j is configured
        if self._neo4j:
            await self._neo4j.create_character(
                campaign_id=self.campaign_id,
                char_id=char_id,
                name=char.name,
                char_class=char.char_class,
                level=char.level,
            )

        return char_id

    async def get_characters(self) -> list[Character]:
        """Get all characters in the campaign."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")
        return await self._sqlite.get_campaign_characters(self.campaign_id)

    async def update_character(self, char_id: str, char: Character) -> None:
        """Update a character's state."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")
        await self._sqlite.update_character(char_id, char)

    # Event management

    async def record_event(self, event: GameEvent) -> str:
        """Record a game event."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")

        # Ensure session_id is set
        if not event.session_id and self.current_session_id:
            event.session_id = self.current_session_id

        return await self._sqlite.save_event(event)

    async def get_session_events(
        self, session_id: str | None = None
    ) -> list[GameEvent]:
        """Get all events for a session."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")

        sid = session_id or self.current_session_id
        if not sid:
            return []

        return await self._sqlite.get_session_events(sid)

    async def get_recent_events(self, limit: int = 10) -> list[GameEvent]:
        """Get the most recent events from current session."""
        if not self._sqlite:
            raise RuntimeError("Campaign not initialized")

        if not self.current_session_id:
            return []

        events = await self._sqlite.get_session_events(
            self.current_session_id, limit=None
        )
        return events[-limit:] if len(events) > limit else events
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_campaign.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/campaign.py tests/test_campaign.py
git commit -m "feat: Campaign manager for coordinating storage"
```

---

## Task 6: Integrate Persistence with Game Loop

**Files:**
- Modify: `src/dndbots/game.py`
- Modify: `src/dndbots/cli.py`
- Create: `tests/test_game_persistence.py`

**Step 1: Write the failing test**

```python
"""Tests for game loop with persistence integration."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from dndbots.game import DnDGame
from dndbots.campaign import Campaign
from dndbots.models import Character, Stats


@pytest.fixture
def mock_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


@pytest.fixture
async def campaign_with_char():
    """Create a campaign with a character."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        campaign = Campaign(
            campaign_id="test_001",
            name="Test Campaign",
            db_path=str(db_path),
        )
        await campaign.initialize()

        char = Character(
            name="Throk",
            char_class="Fighter",
            level=1,
            hp=8,
            hp_max=8,
            ac=5,
            stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
            equipment=["longsword"],
            gold=25,
        )
        await campaign.add_character(char)

        yield campaign
        await campaign.close()


class TestGameWithPersistence:
    def test_game_accepts_campaign(self, mock_openai_key, campaign_with_char):
        """Game should accept optional campaign parameter."""
        import asyncio
        campaign = asyncio.get_event_loop().run_until_complete(
            campaign_with_char.__anext__() if hasattr(campaign_with_char, '__anext__')
            else campaign_with_char
        )
        # This test just verifies the interface exists
        # Full integration would require mocking AutoGen
```

**Step 2: Update game.py to accept campaign**

Add campaign parameter to DnDGame:

```python
# In DnDGame.__init__, add:
from dndbots.campaign import Campaign

def __init__(
    self,
    scenario: str,
    characters: list[Character],
    dm_model: str = "gpt-4o",
    player_model: str = "gpt-4o",
    campaign: Campaign | None = None,  # NEW
):
    self.campaign = campaign
    # ... rest of init
```

**Step 3: Update cli.py to use persistence**

```python
# Update cli.py to optionally use persistence
# Add data directory creation and campaign setup
```

For now, keep persistence optional in the CLI. Full integration in Task 7.

**Step 4: Run tests**

```bash
pytest tests/test_game_persistence.py -v
```

**Step 5: Commit**

```bash
git add src/dndbots/game.py tests/test_game_persistence.py
git commit -m "feat: integrate campaign persistence with game loop"
```

---

## Task 7: CLI with Persistence

**Files:**
- Modify: `src/dndbots/cli.py`
- Update: `.env.example`

**Step 1: Update .env.example**

```bash
# .env.example
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Neo4j connection (for relationship tracking)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your-password
```

**Step 2: Update CLI to use Campaign**

Update `cli.py` to:
1. Create a data directory (~/.dndbots or ./data)
2. Initialize Campaign with SQLite
3. Load or create characters
4. Record events during gameplay

```python
"""Command-line interface for running DnDBots."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from dndbots.campaign import Campaign
from dndbots.game import DnDGame
from dndbots.models import Character, Stats


# Default paths
DATA_DIR = Path.home() / ".dndbots"
DEFAULT_DB = DATA_DIR / "campaigns.db"

# Default scenario
DEFAULT_SCENARIO = """
The party stands at the entrance to the Caves of Chaos...
[same as before]
"""


def create_default_character() -> Character:
    """Create a default fighter character for testing."""
    return Character(
        name="Throk",
        char_class="Fighter",
        level=1,
        hp=8,
        hp_max=8,
        ac=5,
        stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
        equipment=["longsword", "chain mail", "shield", "backpack", "torch x3", "rope 50ft"],
        gold=25,
    )


async def run_game() -> None:
    """Run the game with persistence."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize campaign
    campaign = Campaign(
        campaign_id="default_campaign",
        name="Caves of Chaos",
        db_path=str(DEFAULT_DB),
    )
    await campaign.initialize()

    try:
        # Get or create character
        characters = await campaign.get_characters()
        if not characters:
            char = create_default_character()
            await campaign.add_character(char)
            characters = [char]

        # Start session
        await campaign.start_session()

        print(f"Campaign: {campaign.name}")
        print(f"Session: {campaign.current_session_id}")
        print(f"Characters: {', '.join(c.name for c in characters)}")
        print()

        # Create and run game
        game = DnDGame(
            scenario=DEFAULT_SCENARIO,
            characters=characters,
            dm_model="gpt-4o",
            player_model="gpt-4o",
            campaign=campaign,
        )

        await game.run()

    finally:
        await campaign.end_session("Session interrupted")
        await campaign.close()


def main() -> None:
    """Run a game session."""
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        return

    print("=" * 60)
    print("DnDBots - Basic D&D AI Campaign")
    print("=" * 60)
    print(f"\nData directory: {DATA_DIR}")
    print("Type Ctrl+C to stop\n")

    try:
        asyncio.run(run_game())
    except KeyboardInterrupt:
        print("\n\n[System] Session interrupted by user.")

    print("\n" + "=" * 60)
    print("Session ended")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 3: Reinstall and test**

```bash
pip install -e ".[dev]"
dndbots
```

**Step 4: Commit**

```bash
git add src/dndbots/cli.py .env.example
git commit -m "feat: CLI with campaign persistence"
```

---

## Task 8: Integration Test

**Step 1: Run the game with persistence**

```bash
dndbots
```

Verify:
- Data directory is created at ~/.dndbots
- Campaign database is created
- Events are recorded
- Ctrl+C ends session cleanly

**Step 2: Check database contents**

```bash
sqlite3 ~/.dndbots/campaigns.db "SELECT * FROM events LIMIT 5;"
sqlite3 ~/.dndbots/campaigns.db "SELECT * FROM characters;"
```

**Step 3: Run game again - character should persist**

```bash
dndbots
```

Should see "Characters: Throk" without recreating.

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: phase 2 complete - persistence layer working"
```

---

## Phase 2 Complete Checklist

- [ ] Dependencies added (aiosqlite, neo4j, pydantic)
- [ ] GameEvent schema with EventType enum
- [ ] SQLite store for events and characters
- [ ] Neo4j store for relationships (optional)
- [ ] Campaign manager coordinating storage
- [ ] Game loop integration with campaign
- [ ] CLI using persistence
- [ ] Integration test passed

## Next Phase Preview

**Phase 3: Multi-Provider** will add:
- Multiple AI providers (Claude, Gemini, DeepSeek)
- Multiple player characters
- AI character creation flow
- Provider configuration in campaign

---

**End of Phase 2 Plan**
