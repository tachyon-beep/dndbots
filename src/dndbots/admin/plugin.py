"""AdminPlugin - bridges EventBus to WebSocket clients."""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from dndbots.output import OutputEvent, OutputEventType


@runtime_checkable
class WebSocketLike(Protocol):
    """Protocol for WebSocket-like objects."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the client."""
        ...


@dataclass
class AdminPlugin:
    """Output plugin that streams events to WebSocket clients.

    Implements the OutputPlugin protocol to receive game events
    and broadcast them to all connected WebSocket clients.
    """

    _clients: set[WebSocketLike] = field(default_factory=set)

    @property
    def name(self) -> str:
        """Unique plugin name."""
        return "admin"

    @property
    def handled_types(self) -> set[OutputEventType] | None:
        """Handle all event types."""
        return None

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)

    def add_client(self, ws: WebSocketLike) -> None:
        """Add a WebSocket client.

        Args:
            ws: WebSocket connection to add
        """
        self._clients.add(ws)

    def remove_client(self, ws: WebSocketLike) -> None:
        """Remove a WebSocket client.

        Args:
            ws: WebSocket connection to remove
        """
        self._clients.discard(ws)

    async def handle(self, event: OutputEvent) -> None:
        """Broadcast event to all connected clients.

        Args:
            event: The event to broadcast
        """
        message = {
            "type": event.event_type.value,
            "source": event.source,
            "content": event.content,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat(),
        }

        dead_clients: list[WebSocketLike] = []

        for ws in self._clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead_clients.append(ws)

        for ws in dead_clients:
            self._clients.discard(ws)

    async def start(self) -> None:
        """Initialize the plugin."""
        pass

    async def stop(self) -> None:
        """Cleanup the plugin."""
        pass
