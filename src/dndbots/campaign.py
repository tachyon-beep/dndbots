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
