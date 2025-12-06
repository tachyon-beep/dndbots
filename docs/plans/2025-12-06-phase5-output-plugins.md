# Phase 5: Extensible Output Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an extensible event bus with plugin architecture for routing game output to multiple destinations (console, logs, Discord, TTS, etc.).

**Architecture:** Pub/sub pattern where game events flow through a central EventBus to registered OutputPlugins. Each plugin implements a simple protocol and can filter which event types it handles. Built-in plugins for console and logging; external plugins (Discord, TTS) can be added without modifying core code.

**Tech Stack:** Python Protocol (structural typing), asyncio, dataclasses, logging module

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Game Loop (DnDGame)                                            │
│  DM speaks → Player responds → DM adjudicates                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ emit(OutputEvent)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  EventBus                                                       │
│  • Receives OutputEvents from game                              │
│  • Routes to registered plugins                                 │
│  • Handles async plugin calls                                   │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Console  │ │ JsonLog  │ │ Discord  │ │   TTS    │
│ Plugin   │ │ Plugin   │ │ Plugin   │ │ Plugin   │
│ (builtin)│ │ (builtin)│ │ (external│ │ (external│
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## Task 1: OutputEvent Types

**Files:**
- Create: `src/dndbots/output/events.py`
- Test: `tests/test_output_events.py`

**Step 1: Write the failing test**

```python
"""Tests for output event types."""

import pytest
from dndbots.output.events import OutputEvent, OutputEventType


class TestOutputEvent:
    def test_create_narration_event(self):
        """Create a DM narration output event."""
        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The goblin lunges at you with its rusty dagger!",
            metadata={"session_id": "session_001"},
        )
        assert event.event_type == OutputEventType.NARRATION
        assert event.source == "dm"
        assert "goblin" in event.content

    def test_create_player_action_event(self):
        """Create a player action output event."""
        event = OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I swing my sword at the goblin!",
        )
        assert event.event_type == OutputEventType.PLAYER_ACTION
        assert event.source == "pc_throk_001"

    def test_create_dice_roll_event(self):
        """Create a dice roll output event."""
        event = OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Throk attacks: d20+2 = 18 (hit!)",
            metadata={"roll": "d20+2", "result": 18, "success": True},
        )
        assert event.event_type == OutputEventType.DICE_ROLL
        assert event.metadata["result"] == 18

    def test_create_system_message_event(self):
        """Create a system message event."""
        event = OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="Session started.",
        )
        assert event.event_type == OutputEventType.SYSTEM

    def test_event_has_timestamp(self):
        """Events get automatic timestamp."""
        event = OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        )
        assert event.timestamp is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_events.py -v`
Expected: FAIL with "No module named 'dndbots.output'"

**Step 3: Write minimal implementation**

First create the package directory, then:

```python
"""Output event types for the event bus."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OutputEventType(Enum):
    """Types of events that flow through the output system."""

    # Game content
    NARRATION = "narration"         # DM narrative text
    PLAYER_ACTION = "player_action" # Player character actions
    DIALOGUE = "dialogue"           # Character speech

    # Mechanics
    DICE_ROLL = "dice_roll"         # Dice roll results
    COMBAT = "combat"               # Combat updates (damage, status)

    # System
    SYSTEM = "system"               # System messages
    SESSION_START = "session_start" # Session began
    SESSION_END = "session_end"     # Session ended
    ERROR = "error"                 # Error messages


@dataclass
class OutputEvent:
    """An event to be sent to output plugins.

    This is the unit of communication between the game loop
    and output destinations (console, logs, Discord, etc.).
    """

    event_type: OutputEventType
    source: str  # Who generated this: "dm", "pc_throk_001", "system"
    content: str  # The text content to display
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

Also create `src/dndbots/output/__init__.py`:

```python
"""Output layer - extensible event bus with plugin architecture."""

from dndbots.output.events import OutputEvent, OutputEventType

__all__ = ["OutputEvent", "OutputEventType"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/ tests/test_output_events.py
git commit -m "feat: OutputEvent types for event bus"
```

---

## Task 2: OutputPlugin Protocol

**Files:**
- Create: `src/dndbots/output/plugin.py`
- Test: `tests/test_output_plugin.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_plugin.py -v`
Expected: FAIL with "cannot import name 'OutputPlugin'"

**Step 3: Write minimal implementation**

```python
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
```

Update `src/dndbots/output/__init__.py`:

```python
"""Output layer - extensible event bus with plugin architecture."""

from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugin import OutputPlugin

__all__ = ["OutputEvent", "OutputEventType", "OutputPlugin"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/plugin.py tests/test_output_plugin.py
git commit -m "feat: OutputPlugin protocol for extensible output"
```

---

## Task 3: EventBus Core

**Files:**
- Create: `src/dndbots/output/bus.py`
- Test: `tests/test_event_bus.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_bus.py -v`
Expected: FAIL with "cannot import name 'EventBus'"

**Step 3: Write minimal implementation**

```python
"""Event bus for routing output events to plugins."""

import asyncio
from dataclasses import dataclass, field

from dndbots.output.events import OutputEvent
from dndbots.output.plugin import OutputPlugin


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
        except Exception as e:
            # Log but don't propagate - one plugin shouldn't break others
            print(f"Plugin {plugin.name} error: {e}")

    async def start(self) -> None:
        """Start all plugins."""
        for plugin in self.plugins:
            await plugin.start()

    async def stop(self) -> None:
        """Stop all plugins."""
        for plugin in self.plugins:
            await plugin.stop()
```

Update `src/dndbots/output/__init__.py`:

```python
"""Output layer - extensible event bus with plugin architecture."""

from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugin import OutputPlugin
from dndbots.output.bus import EventBus

__all__ = ["OutputEvent", "OutputEventType", "OutputPlugin", "EventBus"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_bus.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/bus.py tests/test_event_bus.py
git commit -m "feat: EventBus for routing events to plugins"
```

---

## Task 4: ConsolePlugin (Built-in)

**Files:**
- Create: `src/dndbots/output/plugins/console.py`
- Test: `tests/test_console_plugin.py`

**Step 1: Write the failing test**

```python
"""Tests for console output plugin."""

import pytest
from io import StringIO
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugins.console import ConsolePlugin


class TestConsolePlugin:
    def test_plugin_name(self):
        """Console plugin has correct name."""
        plugin = ConsolePlugin()
        assert plugin.name == "console"

    def test_handles_all_types(self):
        """Console plugin handles all event types by default."""
        plugin = ConsolePlugin()
        assert plugin.handled_types is None

    def test_can_filter_types(self):
        """Console plugin can be configured to filter types."""
        plugin = ConsolePlugin(
            handled_types={OutputEventType.NARRATION, OutputEventType.DIALOGUE}
        )
        assert OutputEventType.NARRATION in plugin.handled_types
        assert OutputEventType.DICE_ROLL not in plugin.handled_types

    @pytest.mark.asyncio
    async def test_prints_narration(self, capsys):
        """Narration events print with [dm] prefix."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The cave entrance looms before you.",
        ))
        captured = capsys.readouterr()
        assert "[dm]" in captured.out
        assert "cave entrance" in captured.out

    @pytest.mark.asyncio
    async def test_prints_player_action(self, capsys):
        """Player actions print with character name."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I draw my sword!",
        ))
        captured = capsys.readouterr()
        assert "[Throk]" in captured.out or "[pc_throk_001]" in captured.out
        assert "sword" in captured.out

    @pytest.mark.asyncio
    async def test_prints_dice_roll(self, capsys):
        """Dice rolls print with special formatting."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Attack roll: d20+2 = 18",
            metadata={"roll": "d20+2", "result": 18},
        ))
        captured = capsys.readouterr()
        assert "18" in captured.out

    @pytest.mark.asyncio
    async def test_prints_system_message(self, capsys):
        """System messages print with [System] prefix."""
        plugin = ConsolePlugin()
        await plugin.handle(OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="Session started.",
        ))
        captured = capsys.readouterr()
        assert "[System]" in captured.out
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_console_plugin.py -v`
Expected: FAIL with "No module named 'dndbots.output.plugins'"

**Step 3: Write minimal implementation**

Create `src/dndbots/output/plugins/__init__.py`:

```python
"""Built-in output plugins."""

from dndbots.output.plugins.console import ConsolePlugin

__all__ = ["ConsolePlugin"]
```

Create `src/dndbots/output/plugins/console.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_console_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/plugins/ tests/test_console_plugin.py
git commit -m "feat: ConsolePlugin for terminal output"
```

---

## Task 5: JsonLogPlugin (Built-in)

**Files:**
- Create: `src/dndbots/output/plugins/jsonlog.py`
- Test: `tests/test_jsonlog_plugin.py`

**Step 1: Write the failing test**

```python
"""Tests for JSON log output plugin."""

import json
import pytest
import tempfile
from pathlib import Path
from dndbots.output.events import OutputEvent, OutputEventType
from dndbots.output.plugins.jsonlog import JsonLogPlugin


class TestJsonLogPlugin:
    def test_plugin_name(self):
        """JsonLog plugin has correct name."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            plugin = JsonLogPlugin(log_path=f.name)
            assert plugin.name == "jsonlog"

    def test_handles_all_types_by_default(self):
        """JsonLog plugin handles all event types by default."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            plugin = JsonLogPlugin(log_path=f.name)
            assert plugin.handled_types is None

    @pytest.mark.asyncio
    async def test_writes_jsonl_format(self):
        """Events are written as JSON lines."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name

        plugin = JsonLogPlugin(log_path=log_path)
        await plugin.start()

        await plugin.handle(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="The cave is dark.",
        ))

        await plugin.stop()

        # Read and parse
        with open(log_path) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["event_type"] == "narration"
        assert data["source"] == "dm"
        assert data["content"] == "The cave is dark."
        assert "timestamp" in data

        # Cleanup
        Path(log_path).unlink()

    @pytest.mark.asyncio
    async def test_writes_multiple_events(self):
        """Multiple events create multiple lines."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name

        plugin = JsonLogPlugin(log_path=log_path)
        await plugin.start()

        for i in range(3):
            await plugin.handle(OutputEvent(
                event_type=OutputEventType.NARRATION,
                source="dm",
                content=f"Event {i}",
            ))

        await plugin.stop()

        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 3

        Path(log_path).unlink()

    @pytest.mark.asyncio
    async def test_includes_metadata(self):
        """Metadata is included in JSON output."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name

        plugin = JsonLogPlugin(log_path=log_path)
        await plugin.start()

        await plugin.handle(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="d20 = 15",
            metadata={"roll": "d20", "result": 15, "modifier": 2},
        ))

        await plugin.stop()

        with open(log_path) as f:
            data = json.loads(f.readline())

        assert data["metadata"]["result"] == 15
        assert data["metadata"]["roll"] == "d20"

        Path(log_path).unlink()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_jsonlog_plugin.py -v`
Expected: FAIL with "cannot import name 'JsonLogPlugin'"

**Step 3: Write minimal implementation**

```python
"""JSON Lines log output plugin - writes events to .jsonl file."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from dndbots.output.events import OutputEvent, OutputEventType


@dataclass
class JsonLogPlugin:
    """Output plugin that writes events to a JSON Lines file.

    Each event is written as a single JSON object per line,
    making it easy to parse and analyze game logs.

    Args:
        log_path: Path to the .jsonl log file
        handled_types: Event types to handle, or None for all
    """

    log_path: str
    handled_types: set[OutputEventType] | None = None
    _file: TextIO | None = field(default=None, repr=False)

    @property
    def name(self) -> str:
        return "jsonlog"

    async def start(self) -> None:
        """Open log file for writing."""
        self._file = open(self.log_path, "a")

    async def stop(self) -> None:
        """Close log file."""
        if self._file:
            self._file.close()
            self._file = None

    async def handle(self, event: OutputEvent) -> None:
        """Write event as JSON line."""
        if not self._file:
            return

        data = {
            "event_type": event.event_type.value,
            "source": event.source,
            "content": event.content,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
        }

        self._file.write(json.dumps(data) + "\n")
        self._file.flush()
```

Update `src/dndbots/output/plugins/__init__.py`:

```python
"""Built-in output plugins."""

from dndbots.output.plugins.console import ConsolePlugin
from dndbots.output.plugins.jsonlog import JsonLogPlugin

__all__ = ["ConsolePlugin", "JsonLogPlugin"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_jsonlog_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/plugins/jsonlog.py tests/test_jsonlog_plugin.py
git commit -m "feat: JsonLogPlugin for structured logging"
```

---

## Task 6: CallbackPlugin (For Custom Handlers)

**Files:**
- Create: `src/dndbots/output/plugins/callback.py`
- Test: `tests/test_callback_plugin.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_callback_plugin.py -v`
Expected: FAIL with "cannot import name 'CallbackPlugin'"

**Step 3: Write minimal implementation**

```python
"""Callback output plugin - wraps custom functions as plugins."""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Callable, Awaitable

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
```

Update `src/dndbots/output/plugins/__init__.py`:

```python
"""Built-in output plugins."""

from dndbots.output.plugins.console import ConsolePlugin
from dndbots.output.plugins.jsonlog import JsonLogPlugin
from dndbots.output.plugins.callback import CallbackPlugin

__all__ = ["ConsolePlugin", "JsonLogPlugin", "CallbackPlugin"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_callback_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/dndbots/output/plugins/callback.py tests/test_callback_plugin.py
git commit -m "feat: CallbackPlugin for custom handlers"
```

---

## Task 7: Integration Test - Full Pipeline

**Files:**
- Create: `tests/test_output_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for the output system."""

import json
import pytest
import tempfile
from pathlib import Path

from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin, CallbackPlugin


class TestOutputIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, capsys):
        """Test complete flow: events -> bus -> multiple plugins."""
        # Setup log file
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            log_path = f.name

        # Track callback invocations
        callback_events = []

        # Create bus with multiple plugins
        bus = EventBus()
        bus.register(ConsolePlugin())
        bus.register(JsonLogPlugin(log_path=log_path))
        bus.register(CallbackPlugin(
            name="tracker",
            callback=lambda e: callback_events.append(e),
        ))

        await bus.start()

        # Emit various events
        await bus.emit(OutputEvent(
            event_type=OutputEventType.SESSION_START,
            source="system",
            content="Campaign: Caves of Chaos",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="You stand at the entrance to the goblin caves.",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.PLAYER_ACTION,
            source="pc_throk_001",
            content="I draw my sword and peer into the darkness.",
        ))

        await bus.emit(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="Perception check: d20+1 = 14",
            metadata={"roll": "d20+1", "result": 14, "skill": "perception"},
        ))

        await bus.stop()

        # Verify console output
        captured = capsys.readouterr()
        assert "goblin caves" in captured.out
        assert "sword" in captured.out

        # Verify JSON log
        with open(log_path) as f:
            lines = f.readlines()
        assert len(lines) == 4

        first_event = json.loads(lines[0])
        assert first_event["event_type"] == "session_start"

        dice_event = json.loads(lines[3])
        assert dice_event["metadata"]["result"] == 14

        # Verify callback received all events
        assert len(callback_events) == 4

        # Cleanup
        Path(log_path).unlink()

    @pytest.mark.asyncio
    async def test_filtered_plugins(self):
        """Plugins only receive events they're configured for."""
        narration_only = []
        dice_only = []

        bus = EventBus()
        bus.register(CallbackPlugin(
            name="narration",
            callback=lambda e: narration_only.append(e),
            handled_types={OutputEventType.NARRATION, OutputEventType.DIALOGUE},
        ))
        bus.register(CallbackPlugin(
            name="dice",
            callback=lambda e: dice_only.append(e),
            handled_types={OutputEventType.DICE_ROLL},
        ))

        await bus.start()

        # Emit mixed events
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Narration 1",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.DICE_ROLL,
            source="system",
            content="d20 = 15",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Narration 2",
        ))
        await bus.emit(OutputEvent(
            event_type=OutputEventType.SYSTEM,
            source="system",
            content="System message",
        ))

        await bus.stop()

        # Verify filtering
        assert len(narration_only) == 2
        assert len(dice_only) == 1

    @pytest.mark.asyncio
    async def test_plugin_error_isolation(self, capsys):
        """Errors in one plugin don't affect others."""
        good_events = []

        def bad_callback(event):
            raise ValueError("Plugin error!")

        bus = EventBus()
        bus.register(CallbackPlugin(
            name="bad",
            callback=bad_callback,
        ))
        bus.register(CallbackPlugin(
            name="good",
            callback=lambda e: good_events.append(e),
        ))

        await bus.start()

        # Should not raise, despite bad plugin
        await bus.emit(OutputEvent(
            event_type=OutputEventType.NARRATION,
            source="dm",
            content="Test",
        ))

        await bus.stop()

        # Good plugin still received the event
        assert len(good_events) == 1

        # Error was logged
        captured = capsys.readouterr()
        assert "bad" in captured.out or "error" in captured.out.lower()
```

**Step 2: Run integration test**

Run: `pytest tests/test_output_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_output_integration.py
git commit -m "test: output system integration tests"
```

---

## Task 8: Update Package Exports

**Files:**
- Modify: `src/dndbots/output/__init__.py`

**Step 1: Update exports**

```python
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
```

**Step 2: Verify all tests still pass**

Run: `pytest tests/test_output*.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/dndbots/output/__init__.py
git commit -m "docs: comprehensive output module documentation"
```

---

## Summary

Phase 5 implements an extensible output layer:

| Task | Component | Purpose |
|------|-----------|---------|
| 1 | OutputEvent | Event data structure |
| 2 | OutputPlugin | Protocol for plugins |
| 3 | EventBus | Central routing hub |
| 4 | ConsolePlugin | Terminal output |
| 5 | JsonLogPlugin | Structured logging |
| 6 | CallbackPlugin | Custom handlers |
| 7 | Integration test | End-to-end verification |
| 8 | Package exports | Clean public API |

### Example Usage

```python
from dndbots.output import EventBus, OutputEvent, OutputEventType
from dndbots.output.plugins import ConsolePlugin, JsonLogPlugin, CallbackPlugin

# Create bus with multiple outputs
bus = EventBus()
bus.register(ConsolePlugin())
bus.register(JsonLogPlugin("session.jsonl"))

# Add custom Discord output
async def send_to_discord(event):
    if event.event_type == OutputEventType.NARRATION:
        await channel.send(f"**DM:** {event.content}")

bus.register(CallbackPlugin(
    name="discord",
    callback=send_to_discord,
    handled_types={OutputEventType.NARRATION},
))

# Use in game loop
await bus.start()
await bus.emit(OutputEvent(...))
await bus.stop()
```

### Future Plugins (Not Implemented)

- **DiscordPlugin**: Send to Discord channels
- **TTSPlugin**: Text-to-speech output
- **WebSocketPlugin**: Real-time web streaming
- **DatabasePlugin**: Store in SQLite/Postgres
