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

    def test_rejects_path_traversal(self):
        """Path traversal attempts are rejected."""
        with pytest.raises(ValueError, match="Path traversal"):
            JsonLogPlugin(log_path="../../../etc/passwd.jsonl")

    def test_rejects_nonexistent_parent(self):
        """Paths with nonexistent parent directories are rejected."""
        with pytest.raises(ValueError, match="Parent directory does not exist"):
            JsonLogPlugin(log_path="/nonexistent/path/game.jsonl")
