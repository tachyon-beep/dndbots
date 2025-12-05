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
