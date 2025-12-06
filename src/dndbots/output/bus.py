"""Event bus for routing output events to plugins."""

import asyncio
import logging
from dataclasses import dataclass, field

from dndbots.output.events import OutputEvent
from dndbots.output.plugin import OutputPlugin

logger = logging.getLogger(__name__)


@dataclass
class EventBus:
    """Central hub for routing output events to plugins.

    Usage:
        bus = EventBus()
        bus.register(ConsolePlugin())
        bus.register(LogPlugin("game.log"))

        await bus.start()
        await bus.emit(OutputEvent(...))
        await bus.stop()
    """

    plugins: list[OutputPlugin] = field(default_factory=list)

    def register(self, plugin: OutputPlugin) -> None:
        """Register a plugin to receive events."""
        self.plugins.append(plugin)

    def unregister(self, name: str) -> None:
        """Unregister a plugin by name."""
        self.plugins = [p for p in self.plugins if p.name != name]

    async def emit(self, event: OutputEvent) -> None:
        """Emit an event to all applicable plugins.

        Plugins are called concurrently. Errors in one plugin
        don't affect others.
        """
        tasks = []
        for plugin in self.plugins:
            if self._should_handle(plugin, event):
                tasks.append(self._safe_handle(plugin, event))

        if tasks:
            await asyncio.gather(*tasks)

    def _should_handle(self, plugin: OutputPlugin, event: OutputEvent) -> bool:
        """Check if plugin should receive this event."""
        handled = plugin.handled_types
        return handled is None or event.event_type in handled

    async def _safe_handle(self, plugin: OutputPlugin, event: OutputEvent) -> None:
        """Handle event with error protection."""
        try:
            await plugin.handle(event)
        except Exception:
            logger.exception(f"Plugin {plugin.name} failed to handle event")

    async def start(self) -> None:
        """Start all plugins."""
        for plugin in self.plugins:
            try:
                await plugin.start()
            except Exception:
                logger.exception(f"Plugin {plugin.name} failed to start")

    async def stop(self) -> None:
        """Stop all plugins, ensuring all get stop() called even if one fails."""
        for plugin in self.plugins:
            try:
                await plugin.stop()
            except Exception:
                logger.exception(f"Plugin {plugin.name} failed to stop")
