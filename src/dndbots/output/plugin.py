"""Output plugin protocol definition."""

from typing import Protocol, runtime_checkable

from dndbots.output.events import OutputEvent, OutputEventType


@runtime_checkable
class OutputPlugin(Protocol):
    """Protocol for output plugins.

    Plugins receive OutputEvents and send them to their destination
    (console, file, Discord, TTS, etc.).

    Example implementation:

        class ConsolePlugin:
            name = "console"

            @property
            def handled_types(self) -> set[OutputEventType] | None:
                return None  # Handle all types

            async def handle(self, event: OutputEvent) -> None:
                print(f"[{event.source}] {event.content}")

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass
    """

    @property
    def name(self) -> str:
        """Unique name for this plugin."""
        ...

    @property
    def handled_types(self) -> set[OutputEventType] | None:
        """Event types this plugin handles.

        Returns:
            Set of event types to handle, or None to handle all types.
        """
        ...

    async def handle(self, event: OutputEvent) -> None:
        """Process an output event.

        Args:
            event: The event to process
        """
        ...

    async def start(self) -> None:
        """Initialize the plugin (called when EventBus starts)."""
        ...

    async def stop(self) -> None:
        """Cleanup the plugin (called when EventBus stops)."""
        ...