"""Tests for AdminPlugin."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from dndbots.output import OutputEvent, OutputEventType
from dndbots.admin.plugin import AdminPlugin


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages = []
        self.closed = False

    async def send_json(self, data):
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.messages.append(data)


class TestAdminPlugin:
    """Tests for AdminPlugin."""

    def test_plugin_name(self):
        """Plugin has correct name."""
        plugin = AdminPlugin()
        assert plugin.name == "admin"

    def test_handles_all_event_types(self):
        """Plugin handles all event types (None means all)."""
        plugin = AdminPlugin()
        assert plugin.handled_types is None

    @pytest.mark.asyncio
    async def test_add_and_remove_client(self):
        """Add and remove WebSocket clients."""
        plugin = AdminPlugin()
        ws = MockWebSocket()

        plugin.add_client(ws)
        assert ws in plugin._clients

        plugin.remove_client(ws)
        assert ws not in plugin._clients

    @pytest.mark.asyncio
    async def test_broadcast_to_clients(self):
        """Broadcast event to all connected clients."""
        plugin = AdminPlugin()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        plugin.add_client(ws1)
        plugin.add_client(ws2)

        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The goblin attacks!",
        )

        await plugin.handle(event)

        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 1
        assert ws1.messages[0]["type"] == "narration"
        assert ws1.messages[0]["content"] == "The goblin attacks!"
        assert ws1.messages[0]["source"] == "dm"

    @pytest.mark.asyncio
    async def test_removes_dead_clients(self):
        """Dead clients are removed after send failure."""
        plugin = AdminPlugin()
        ws_good = MockWebSocket()
        ws_dead = MockWebSocket()
        ws_dead.closed = True

        plugin.add_client(ws_good)
        plugin.add_client(ws_dead)

        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        )

        await plugin.handle(event)

        assert ws_good in plugin._clients
        assert ws_dead not in plugin._clients

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Start and stop are no-ops (no errors)."""
        plugin = AdminPlugin()
        await plugin.start()
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_client_count(self):
        """Track number of connected clients."""
        plugin = AdminPlugin()
        assert plugin.client_count == 0

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        plugin.add_client(ws1)
        assert plugin.client_count == 1

        plugin.add_client(ws2)
        assert plugin.client_count == 2

        plugin.remove_client(ws1)
        assert plugin.client_count == 1
