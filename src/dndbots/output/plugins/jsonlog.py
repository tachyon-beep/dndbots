"""JSON Lines log output plugin - writes events to .jsonl file."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiofiles
from aiofiles.threadpool.text import AsyncTextIOWrapper

from dndbots.output.events import OutputEvent, OutputEventType


@dataclass
class JsonLogPlugin:
    """Output plugin that writes events to a JSON Lines file.

    Each event is written as a single JSON object per line,
    making it easy to parse and analyze game logs.

    Args:
        log_path: Path to the .jsonl log file
        handled_types: Event types to handle, or None for all

    Raises:
        ValueError: If log_path is invalid or not writable
    """

    log_path: str
    handled_types: set[OutputEventType] | None = None
    _file: AsyncTextIOWrapper | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate log path."""
        path = Path(self.log_path)

        # Check for path traversal (reject ".." in path)
        if ".." in str(path):
            raise ValueError(f"Path traversal not allowed: {self.log_path}")

        # Ensure parent directory exists
        if not path.parent.exists():
            raise ValueError(f"Parent directory does not exist: {path.parent}")

    @property
    def name(self) -> str:
        return "jsonlog"

    async def start(self) -> None:
        """Open log file for writing."""
        self._file = await aiofiles.open(self.log_path, "a")

    async def stop(self) -> None:
        """Close log file."""
        if self._file:
            await self._file.close()
            self._file = None

    async def handle(self, event: OutputEvent) -> None:
        """Write event as JSON line."""
        if not self._file:
            return

        # Convert content to string if it's not already
        # (handles FunctionCall, FunctionExecutionResult, and list types)
        content = event.content
        if not isinstance(content, str):
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            else:
                content = str(content)

        data = {
            "event_type": event.event_type.value,
            "source": event.source,
            "content": content,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
        }

        await self._file.write(json.dumps(data) + "\n")
        await self._file.flush()
