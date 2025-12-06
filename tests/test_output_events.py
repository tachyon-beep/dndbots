"""Tests for output event types."""

import pytest
from dndbots.output.events import OutputEvent, OutputEventType


class TestOutputEvent:
    def test_create_narration_event(self):
        """Create a DM narration output event."""
        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The goblin lunges at you with its rusty dagger!",
            metadata={"session_id": "session_001"},
        )
        assert event.event_type == OutputEventType.NARRATION
        assert event.source == "dm"
        assert "goblin" in event.content

    def test_create_player_action_event(self):
        """Create a player action output event."""
        event = OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I swing my sword at the goblin!",
        )
        assert event.event_type == OutputEventType.PLAYER_ACTION
        assert event.source == "pc_throk_001"

    def test_create_dice_roll_event(self):
        """Create a dice roll output event."""
        event = OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Throk attacks: d20+2 = 18 (hit!)",
            metadata={"roll": "d20+2", "result": 18, "success": True},
        )
        assert event.event_type == OutputEventType.DICE_ROLL
        assert event.metadata["result"] == 18

    def test_create_system_message_event(self):
        """Create a system message event."""
        event = OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="Session started.",
        )
        assert event.event_type == OutputEventType.SYSTEM

    def test_event_has_timestamp(self):
        """Events get automatic timestamp."""
        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        )
        assert event.timestamp is not None
