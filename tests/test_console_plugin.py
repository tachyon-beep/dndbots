"""Tests for console output plugin."""

import pytest
from io import StringIO
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugins.console import ConsolePlugin


class TestConsolePlugin:
    def test_plugin_name(self):
        """Console plugin has correct name."""
        plugin = ConsolePlugin()
        assert plugin.name == "console"

    def test_handles_all_types(self):
        """Console plugin handles all event types by default."""
        plugin = ConsolePlugin()
        assert plugin.handled_types is None

    def test_can_filter_types(self):
        """Console plugin can be configured to filter types."""
        plugin = ConsolePlugin(
            handled_types={OutputEventType.NARRATION, OutputEventType.DIALOGUE}
        )
        assert OutputEventType.NARRATION in plugin.handled_types
        assert OutputEventType.DICE_ROLL not in plugin.handled_types

    @pytest.mark.asyncio
    async def test_prints_narration(self, capsys):
        """Narration events print with [dm] prefix."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The cave entrance looms before you.",
        ))
        captured = capsys.readouterr()
        assert "[dm]" in captured.out
        assert "cave entrance" in captured.out

    @pytest.mark.asyncio
    async def test_prints_player_action(self, capsys):
        """Player actions print with character name."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I draw my sword!",
        ))
        captured = capsys.readouterr()
        assert "[Throk]" in captured.out or "[pc_throk_001]" in captured.out
        assert "sword" in captured.out

    @pytest.mark.asyncio
    async def test_prints_dice_roll(self, capsys):
        """Dice rolls print with special formatting."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Attack roll: d20+2 = 18",
            metadata={"roll": "d20+2", "result": 18},
        ))
        captured = capsys.readouterr()
        assert "18" in captured.out

    @pytest.mark.asyncio
    async def test_prints_system_message(self, capsys):
        """System messages print with [System] prefix."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="Session started.",
        ))
        captured = capsys.readouterr()
        assert "[System]" in captured.out
