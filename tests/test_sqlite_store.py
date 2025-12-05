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
