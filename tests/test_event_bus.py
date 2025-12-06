"""Tests for the event bus."""

import pytest
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.bus import EventBus


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self, name: str = "mock", handled: set[OutputEventType] | None = None):
        self._name = name
        self._handled = handled
        self.events: list[OutputEvent] = []
        self.started = False
        self.stopped = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def handled_types(self) -> set[OutputEventType] | None:
        return self._handled

    async def handle(self, event: OutputEvent) -> None:
        self.events.append(event)

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class TestEventBus:
    def test_create_event_bus(self):
        """Create an empty event bus."""
        bus = EventBus()
        assert len(bus.plugins) == 0

    def test_register_plugin(self):
        """Register a plugin with the bus."""
        bus = EventBus()
        plugin = MockPlugin()
        bus.register(plugin)
        assert len(bus.plugins) == 1
        assert bus.plugins[0].name == "mock"

    def test_unregister_plugin(self):
        """Unregister a plugin by name."""
        bus = EventBus()
        plugin = MockPlugin(name="test")
        bus.register(plugin)
        bus.unregister("test")
        assert len(bus.plugins) == 0

    @pytest.mark.asyncio
    async def test_emit_to_all_plugins(self):
        """Emit event to all registered plugins."""
        bus = EventBus()
        plugin1 = MockPlugin(name="p1")
        plugin2 = MockPlugin(name="p2")
        bus.register(plugin1)
        bus.register(plugin2)

        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        )
        await bus.emit(event)

        assert len(plugin1.events) == 1
        assert len(plugin2.events) == 1

    @pytest.mark.asyncio
    async def test_emit_filters_by_type(self):
        """Plugins only receive events they handle."""
        bus = EventBus()
        narration_only = MockPlugin(
            name="narration",
            handled={OutputEventType.NARRATION}
        )
        all_events = MockPlugin(name="all", handled=None)
        bus.register(narration_only)
        bus.register(all_events)

        # Emit narration - both receive
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Narration",
        ))

        # Emit dice roll - only "all" receives
        await bus.emit(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="d20 = 15",
        ))

        assert len(narration_only.events) == 1
        assert len(all_events.events) == 2

    @pytest.mark.asyncio
    async def test_start_stops_plugins(self):
        """Bus start/stop calls plugin start/stop."""
        bus = EventBus()
        plugin = MockPlugin()
        bus.register(plugin)

        await bus.start()
        assert plugin.started

        await bus.stop()
        assert plugin.stopped
