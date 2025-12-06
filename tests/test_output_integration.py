"""Integration tests for the output system."""

import json
import logging
import pytest
import tempfile
from pathlib import Path

from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin, CallbackPlugin


class TestOutputIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, capsys):
        """Test complete flow: events -> bus -> multiple plugins."""
        # Setup log file
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name

        # Track callback invocations
        callback_events = []

        # Create bus with multiple plugins
        bus = EventBus()
        bus.register(ConsolePlugin())
        bus.register(JsonLogPlugin(log_path=log_path))
        bus.register(CallbackPlugin(
            name="tracker",
            callback=lambda e: callback_events.append(e),
        ))

        await bus.start()

        # Emit various events
        await bus.emit(OutputEvent(
            event_type=OutputEventType.SESSION_START,
            source="system",
            content="Campaign: Caves of Chaos",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="You stand at the entrance to the goblin caves.",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I draw my sword and peer into the darkness.",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Perception check: d20+1 = 14",
            metadata={"roll": "d20+1", "result": 14, "skill": "perception"},
        ))

        await bus.stop()

        # Verify console output
        captured = capsys.readouterr()
        assert "goblin caves" in captured.out
        assert "sword" in captured.out

        # Verify JSON log
        with open(log_path) as f:
            lines = f.readlines()
        assert len(lines) == 4

        first_event = json.loads(lines[0])
        assert first_event["event_type"] == "session_start"

        dice_event = json.loads(lines[3])
        assert dice_event["metadata"]["result"] == 14

        # Verify callback received all events
        assert len(callback_events) == 4

        # Cleanup
        Path(log_path).unlink()

    @pytest.mark.asyncio
    async def test_filtered_plugins(self):
        """Plugins only receive events they're configured for."""
        narration_only = []
        dice_only = []

        bus = EventBus()
        bus.register(CallbackPlugin(
            name="narration",
            callback=lambda e: narration_only.append(e),
            handled_types={OutputEventType.NARRATION, OutputEventType.DIALOGUE},
        ))
        bus.register(CallbackPlugin(
            name="dice",
            callback=lambda e: dice_only.append(e),
            handled_types={OutputEventType.DICE_ROLL},
        ))

        await bus.start()

        # Emit mixed events
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Narration 1",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="d20 = 15",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Narration 2",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="System message",
        ))

        await bus.stop()

        # Verify filtering
        assert len(narration_only) == 2
        assert len(dice_only) == 1

    @pytest.mark.asyncio
    async def test_plugin_error_isolation(self, caplog):
        """Errors in one plugin don't affect others."""
        good_events = []

        def bad_callback(event):
            raise ValueError("Plugin error!")

        bus = EventBus()
        bus.register(CallbackPlugin(
            name="bad",
            callback=bad_callback,
        ))
        bus.register(CallbackPlugin(
            name="good",
            callback=lambda e: good_events.append(e),
        ))

        await bus.start()

        # Should not raise, despite bad plugin
        with caplog.at_level(logging.ERROR):
            await bus.emit(OutputEvent(
                event_type=OutputEventType.NARRATION,
                source="dm",
                content="Test",
            ))

        await bus.stop()

        # Good plugin still received the event
        assert len(good_events) == 1

        # Error was logged
        assert "bad" in caplog.text
        assert "failed to handle" in caplog.text
