"""Tests for callback output plugin."""

import pytest
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugins.callback import CallbackPlugin


class TestCallbackPlugin:
    def test_plugin_name(self):
        """Callback plugin uses provided name."""
        plugin = CallbackPlugin(
            name="my_callback",
            callback=lambda e: None,
        )
        assert plugin.name == "my_callback"

    @pytest.mark.asyncio
    async def test_calls_sync_callback(self):
        """Synchronous callbacks are called."""
        received = []

        def on_event(event: OutputEvent):
            received.append(event)

        plugin = CallbackPlugin(name="test", callback=on_event)

        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        )
        await plugin.handle(event)

        assert len(received) == 1
        assert received[0].content == "Test"

    @pytest.mark.asyncio
    async def test_calls_async_callback(self):
        """Async callbacks are awaited."""
        received = []

        async def on_event(event: OutputEvent):
            received.append(event)

        plugin = CallbackPlugin(name="test", callback=on_event)

        await plugin.handle(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Async test",
        ))

        assert len(received) == 1

    def test_can_filter_types(self):
        """Callback plugin can filter event types."""
        plugin = CallbackPlugin(
            name="test",
            callback=lambda e: None,
            handled_types={OutputEventType.DICE_ROLL},
        )
        assert plugin.handled_types == {OutputEventType.DICE_ROLL}

    @pytest.mark.asyncio
    async def test_on_start_callback(self):
        """on_start callback is called during start."""
        started = []

        plugin = CallbackPlugin(
            name="test",
            callback=lambda e: None,
            on_start=lambda: started.append(True),
        )
        await plugin.start()

        assert len(started) == 1

    @pytest.mark.asyncio
    async def test_on_stop_callback(self):
        """on_stop callback is called during stop."""
        stopped = []

        plugin = CallbackPlugin(
            name="test",
            callback=lambda e: None,
            on_stop=lambda: stopped.append(True),
        )
        await plugin.stop()

        assert len(stopped) == 1
