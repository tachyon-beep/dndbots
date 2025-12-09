"""Console output plugin - prints game events to stdout."""

from dataclasses import dataclass, field

from dndbots.output.events import OutputEvent, OutputEventType


def _format_source(source: str) -> str:
    """Format source ID for display."""
    if source == "dm":
        return "dm"
    if source == "system":
        return "System"
    if source.startswith("pc_"):
        # Extract name from pc_throk_001 -> Throk
        parts = source.split("_")
        if len(parts) >= 2:
            return parts[1].capitalize()
    if source.startswith("npc_"):
        parts = source.split("_")
        if len(parts) >= 2:
            return parts[1].capitalize()
    return source


@dataclass
class ConsolePlugin:
    """Output plugin that prints events to console.

    Formats output for readability with source prefixes
    and optional color support.

    Args:
        handled_types: Event types to handle, or None for all
        show_timestamps: Whether to include timestamps
    """

    handled_types: set[OutputEventType] | None = None
    show_timestamps: bool = False

    @property
    def name(self) -> str:
        return "console"

    async def handle(self, event: OutputEvent) -> None:
        """Print event to console."""
        prefix = self._get_prefix(event)
        content = event.content

        if self.show_timestamps:
            ts = event.timestamp.strftime("%H:%M:%S")
            print(f"[{ts}] {prefix} {content}")
        else:
            print(f"{prefix} {content}")

    def _get_prefix(self, event: OutputEvent) -> str:
        """Get display prefix for event."""
        source = _format_source(event.source)

        if event.event_type == OutputEventType.SYSTEM:
            return "[System]"
        if event.event_type == OutputEventType.REFEREE:
            return "[Referee]"
        if event.event_type == OutputEventType.DICE_ROLL:
            return "[Roll]"
        if event.event_type == OutputEventType.ERROR:
            return "[Error]"

        return f"[{source}]"

    async def start(self) -> None:
        """No initialization needed."""
        pass

    async def stop(self) -> None:
        """No cleanup needed."""
        pass
