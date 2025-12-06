"""Tests for output plugin protocol."""

import pytest
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugin import OutputPlugin


class MockPlugin:
    """A mock plugin for testing."""

    def __init__(self):
        self.received_events: list[OutputEvent] = []
        self.name = "mock"

    @property
    def handled_types(self) -> set[OutputEventType] | None:
        return {OutputEventType.NARRATION, OutputEventType.PLAYER_ACTION}

    async def handle(self, event: OutputEvent) -> None:
        self.received_events.append(event)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class TestOutputPlugin:
    def test_mock_plugin_implements_protocol(self):
        """MockPlugin satisfies OutputPlugin protocol."""
        plugin = MockPlugin()
        # Protocol check - should not raise
        assert isinstance(plugin, OutputPlugin)

    def test_plugin_has_name(self):
        """Plugins have a name property."""
        plugin = MockPlugin()
        assert plugin.name == "mock"

    def test_plugin_has_handled_types(self):
        """Plugins declare which event types they handle."""
        plugin = MockPlugin()
        assert OutputEventType.NARRATION in plugin.handled_types
        assert OutputEventType.DICE_ROLL not in plugin.handled_types

    @pytest.mark.asyncio
    async def test_plugin_receives_events(self):
        """Plugins receive events via handle()."""
        plugin = MockPlugin()
        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test narration",
        )
        await plugin.handle(event)
        assert len(plugin.received_events) == 1
        assert plugin.received_events[0].content == "Test narration"