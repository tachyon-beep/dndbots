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
