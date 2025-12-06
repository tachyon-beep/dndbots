"""Callback output plugin - wraps custom functions as plugins."""

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable

from dndbots.output.events import OutputEvent, OutputEventType


# Type for callback - can be sync or async
EventCallback = Callable[[OutputEvent], None] | Callable[[OutputEvent], Awaitable[None]]
LifecycleCallback = Callable[[], None] | Callable[[], Awaitable[None]] | None


@dataclass
class CallbackPlugin:
    """Output plugin that wraps a callback function.

    Useful for quick integrations without creating a full plugin class.
    Supports both sync and async callbacks.

    Args:
        name: Unique name for this plugin
        callback: Function to call for each event
        handled_types: Event types to handle, or None for all
        on_start: Optional callback when plugin starts
        on_stop: Optional callback when plugin stops

    Example:
        # Simple logging
        plugin = CallbackPlugin(
            name="my_logger",
            callback=lambda e: print(f"Got: {e.content}"),
        )

        # Async Discord integration
        async def send_to_discord(event):
            await discord_channel.send(event.content)

        plugin = CallbackPlugin(
            name="discord",
            callback=send_to_discord,
            handled_types={OutputEventType.NARRATION},
        )
    """

    name: str
    callback: EventCallback
    handled_types: set[OutputEventType] | None = None
    on_start: LifecycleCallback = None
    on_stop: LifecycleCallback = None

    async def handle(self, event: OutputEvent) -> None:
        """Call the callback with the event."""
        result = self.callback(event)
        if inspect.isawaitable(result):
            await result

    async def start(self) -> None:
        """Call on_start callback if provided."""
        if self.on_start:
            result = self.on_start()
            if inspect.isawaitable(result):
                await result

    async def stop(self) -> None:
        """Call on_stop callback if provided."""
        if self.on_stop:
            result = self.on_stop()
            if inspect.isawaitable(result):
                await result
