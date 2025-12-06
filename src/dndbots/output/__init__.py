"""Output layer - extensible event bus with plugin architecture.

The output system uses a pub/sub pattern where game events flow through
a central EventBus to registered OutputPlugins.

Quick Start:
    from dndbots.output import EventBus, OutputEvent, OutputEventType
    from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin

    bus = EventBus()
    bus.register(ConsolePlugin())
    bus.register(JsonLogPlugin("game.jsonl"))

    await bus.start()
    await bus.emit(OutputEvent(
        event_type=OutputEventType.NARRATION,
        source="dm",
        content="The adventure begins...",
    ))
    await bus.stop()

Built-in Plugins:
    - ConsolePlugin: Prints to stdout with formatting
    - JsonLogPlugin: Writes to .jsonl file for analysis
    - CallbackPlugin: Wraps custom functions

Custom Plugins:
    Implement the OutputPlugin protocol:

        class MyPlugin:
            name = "my_plugin"

            @property
            def handled_types(self):
                return {OutputEventType.NARRATION}  # or None for all

            async def handle(self, event: OutputEvent) -> None:
                # Send to Discord, TTS, etc.
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass
"""

from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugin import OutputPlugin
from dndbots.output.bus import EventBus

__all__ = [
    "OutputEvent",
    "OutputEventType",
    "OutputPlugin",
    "EventBus",
]
