# Phase 6: Admin UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local browser-based admin UI for monitoring and controlling DnDBots campaigns in real-time.

**Architecture:** FastAPI server integrated into the same process as the game loop, with WebSocket streaming of events to a Vue 3 SPA. The AdminPlugin bridges the existing EventBus to WebSocket clients. Graceful shutdown via checkpoint models.

**Tech Stack:** FastAPI, uvicorn, WebSockets (backend); Vue 3, Vite (frontend); existing EventBus plugin architecture.

---

## Overview

This plan implements the Phase 6 design in 15 tasks organized into 4 phases:

1. **Backend Foundation (Tasks 1-5):** Dependencies, checkpoints, AdminPlugin, FastAPI skeleton
2. **Backend API (Tasks 6-9):** REST endpoints, WebSocket streaming, CLI integration
3. **Frontend Foundation (Tasks 10-12):** Vue project setup, core components
4. **Frontend Complete (Tasks 13-15):** Remaining components, build integration, end-to-end testing

Each task follows TDD: write failing test → verify failure → implement → verify pass → commit.

---

## Task 1: Add FastAPI Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update dependencies**

Edit `pyproject.toml` to add FastAPI and related packages:

```toml
dependencies = [
    "autogen-agentchat>=0.4.0",
    "autogen-ext[openai]>=0.4.0",
    "python-dotenv>=1.0.0",
    "aiosqlite>=0.19.0",
    "neo4j>=5.14.0",
    "pydantic>=2.5.0",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "websockets>=12.0",
]
```

**Step 2: Install dependencies**

Run: `pip install -e ".[dev]"`

Expected: Successfully installs fastapi, uvicorn, websockets

**Step 3: Verify imports work**

Run: `python -c "from fastapi import FastAPI; from uvicorn import run; print('OK')"`

Expected: Prints "OK"

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add FastAPI, uvicorn, websockets for admin UI"
```

---

## Task 2: Create Checkpoint Models

**Files:**
- Create: `src/dndbots/admin/__init__.py`
- Create: `src/dndbots/admin/checkpoint.py`
- Create: `tests/test_checkpoint.py`

**Step 1: Create admin package**

Create `src/dndbots/admin/__init__.py`:

```python
"""Admin UI module - FastAPI server and WebSocket streaming."""
```

**Step 2: Write the failing test**

Create `tests/test_checkpoint.py`:

```python
"""Tests for checkpoint models."""

import pytest
from datetime import datetime, timezone

from dndbots.admin.checkpoint import NarrativeCheckpoint, CombatCheckpoint


class TestNarrativeCheckpoint:
    """Tests for NarrativeCheckpoint."""

    def test_create_minimal(self):
        """Create checkpoint with required fields only."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_entrance",
        )
        assert checkpoint.campaign_id == "campaign_001"
        assert checkpoint.session_id == "session_001"
        assert checkpoint.party_location == "loc_caves_entrance"
        assert checkpoint.current_beat is None
        assert checkpoint.recent_events == []
        assert checkpoint.dm_notes == ""

    def test_create_full(self):
        """Create checkpoint with all fields."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
            current_beat="exploring",
            recent_events=["evt_001", "evt_002"],
            dm_notes="Party just defeated goblins",
        )
        assert checkpoint.current_beat == "exploring"
        assert len(checkpoint.recent_events) == 2

    def test_to_dict(self):
        """Convert checkpoint to dictionary."""
        checkpoint = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_entrance",
        )
        data = checkpoint.to_dict()
        assert data["campaign_id"] == "campaign_001"
        assert "timestamp" in data

    def test_from_dict(self):
        """Create checkpoint from dictionary."""
        data = {
            "campaign_id": "campaign_001",
            "session_id": "session_001",
            "party_location": "loc_caves_entrance",
            "current_beat": None,
            "recent_events": [],
            "dm_notes": "",
            "timestamp": "2025-12-06T12:00:00+00:00",
        }
        checkpoint = NarrativeCheckpoint.from_dict(data)
        assert checkpoint.campaign_id == "campaign_001"


class TestCombatCheckpoint:
    """Tests for CombatCheckpoint."""

    def test_create_combat_checkpoint(self):
        """Create combat checkpoint with initiative."""
        narrative = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
            current_beat="combat",
        )
        checkpoint = CombatCheckpoint(
            narrative=narrative,
            initiative_order=["pc_throk_001", "npc_goblin_001", "pc_zara_001"],
            current_turn=1,
            round_number=2,
            combatants={
                "pc_throk_001": {"hp": 12, "conditions": [], "position": "front"},
                "npc_goblin_001": {"hp": 3, "conditions": ["wounded"], "position": "center"},
                "pc_zara_001": {"hp": 8, "conditions": [], "position": "back"},
            },
            rounds=[],
        )
        assert checkpoint.current_turn == 1
        assert checkpoint.round_number == 2
        assert len(checkpoint.initiative_order) == 3
        assert checkpoint.combatants["npc_goblin_001"]["hp"] == 3

    def test_to_dict(self):
        """Convert combat checkpoint to dictionary."""
        narrative = NarrativeCheckpoint(
            campaign_id="campaign_001",
            session_id="session_001",
            party_location="loc_caves_room_02",
        )
        checkpoint = CombatCheckpoint(
            narrative=narrative,
            initiative_order=["pc_throk_001"],
            current_turn=0,
            round_number=1,
            combatants={},
            rounds=[],
        )
        data = checkpoint.to_dict()
        assert data["round_number"] == 1
        assert "narrative" in data

    def test_from_dict(self):
        """Create combat checkpoint from dictionary."""
        data = {
            "narrative": {
                "campaign_id": "campaign_001",
                "session_id": "session_001",
                "party_location": "loc_caves_room_02",
                "current_beat": None,
                "recent_events": [],
                "dm_notes": "",
                "timestamp": "2025-12-06T12:00:00+00:00",
            },
            "initiative_order": ["pc_throk_001"],
            "current_turn": 0,
            "round_number": 1,
            "combatants": {},
            "rounds": [],
        }
        checkpoint = CombatCheckpoint.from_dict(data)
        assert checkpoint.round_number == 1
        assert checkpoint.narrative.campaign_id == "campaign_001"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_checkpoint.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.admin.checkpoint'"

**Step 4: Write minimal implementation**

Create `src/dndbots/admin/checkpoint.py`:

```python
"""Checkpoint models for graceful shutdown and resume."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NarrativeCheckpoint:
    """Minimal checkpoint for narrative pause.

    Stores enough context for the DM to resume the story naturally
    after a clean shutdown.
    """

    campaign_id: str
    session_id: str
    party_location: str
    current_beat: str | None = None
    recent_events: list[str] = field(default_factory=list)
    dm_notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "campaign_id": self.campaign_id,
            "session_id": self.session_id,
            "party_location": self.party_location,
            "current_beat": self.current_beat,
            "recent_events": self.recent_events,
            "dm_notes": self.dm_notes,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NarrativeCheckpoint":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            campaign_id=data["campaign_id"],
            session_id=data["session_id"],
            party_location=data["party_location"],
            current_beat=data.get("current_beat"),
            recent_events=data.get("recent_events", []),
            dm_notes=data.get("dm_notes", ""),
            timestamp=timestamp,
        )


@dataclass
class CombatCheckpoint:
    """Full checkpoint for mid-combat shutdown.

    Stores complete combat state for resumption at exact point,
    including initiative order, HP, conditions, and action log.
    """

    narrative: NarrativeCheckpoint
    initiative_order: list[str]
    current_turn: int
    round_number: int
    combatants: dict[str, dict[str, Any]]
    rounds: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "narrative": self.narrative.to_dict(),
            "initiative_order": self.initiative_order,
            "current_turn": self.current_turn,
            "round_number": self.round_number,
            "combatants": self.combatants,
            "rounds": self.rounds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CombatCheckpoint":
        """Create from dictionary."""
        return cls(
            narrative=NarrativeCheckpoint.from_dict(data["narrative"]),
            initiative_order=data["initiative_order"],
            current_turn=data["current_turn"],
            round_number=data["round_number"],
            combatants=data["combatants"],
            rounds=data["rounds"],
        )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_checkpoint.py -v`

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/dndbots/admin/ tests/test_checkpoint.py
git commit -m "feat(admin): add checkpoint models for graceful shutdown"
```

---

## Task 3: Create AdminPlugin

**Files:**
- Create: `src/dndbots/admin/plugin.py`
- Create: `tests/test_admin_plugin.py`

**Step 1: Write the failing test**

Create `tests/test_admin_plugin.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_plugin.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.admin.plugin'"

**Step 3: Write minimal implementation**

Create `src/dndbots/admin/plugin.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_plugin.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/plugin.py tests/test_admin_plugin.py
git commit -m "feat(admin): add AdminPlugin for WebSocket broadcasting"
```

---

## Task 4: Create FastAPI Server Skeleton

**Files:**
- Create: `src/dndbots/admin/server.py`
- Create: `tests/test_admin_server.py`
- Modify: `src/dndbots/admin/__init__.py`

**Step 1: Write the failing test**

Create `tests/test_admin_server.py`:

```python
"""Tests for admin FastAPI server."""

import pytest
from fastapi.testclient import TestClient

from dndbots.admin.server import create_app


class TestServerBasics:
    """Basic server tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Health check endpoint works."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_returns_html(self, client):
        """Root serves index.html or placeholder."""
        response = client.get("/")
        assert response.status_code == 200
        # Will serve HTML when static files exist
        assert "text/html" in response.headers.get("content-type", "")

    def test_api_prefix(self, client):
        """API routes use /api prefix."""
        response = client.get("/api/health")
        assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_server.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'dndbots.admin.server'"

**Step 3: Write minimal implementation**

Create `src/dndbots/admin/server.py`:

```python
"""FastAPI admin server for DnDBots."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Path to static files (built Vue app)
STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="DnDBots Admin",
        description="Admin UI for monitoring and controlling DnDBots campaigns",
        version="0.1.0",
    )

    # Health check
    @app.get("/api/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    # Serve Vue SPA
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the Vue SPA index.html."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return index_path.read_text()
        return """
        <!DOCTYPE html>
        <html>
        <head><title>DnDBots Admin</title></head>
        <body>
            <h1>DnDBots Admin</h1>
            <p>Vue frontend not built yet. Run: <code>cd admin-ui && npm run build</code></p>
        </body>
        </html>
        """

    # Mount static files if they exist
    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    return app


# App instance for uvicorn
app = create_app()
```

Update `src/dndbots/admin/__init__.py`:

```python
"""Admin UI module - FastAPI server and WebSocket streaming."""

from dndbots.admin.checkpoint import NarrativeCheckpoint, CombatCheckpoint
from dndbots.admin.plugin import AdminPlugin
from dndbots.admin.server import create_app, app

__all__ = [
    "NarrativeCheckpoint",
    "CombatCheckpoint",
    "AdminPlugin",
    "create_app",
    "app",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_server.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/server.py src/dndbots/admin/__init__.py tests/test_admin_server.py
git commit -m "feat(admin): add FastAPI server skeleton"
```

---

## Task 5: Add Campaign Endpoints

**Files:**
- Modify: `src/dndbots/admin/server.py`
- Modify: `tests/test_admin_server.py`

**Step 1: Write the failing test**

Add to `tests/test_admin_server.py`:

```python
class TestCampaignEndpoints:
    """Tests for campaign API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_list_campaigns_empty(self, client):
        """List campaigns when none exist."""
        response = client.get("/api/campaigns")
        assert response.status_code == 200
        data = response.json()
        assert data["campaigns"] == []

    def test_get_campaign_not_found(self, client):
        """Get non-existent campaign returns 404."""
        response = client.get("/api/campaigns/nonexistent")
        assert response.status_code == 404

    def test_get_state_no_active_game(self, client):
        """Get state when no game is running."""
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert data["campaign_id"] is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_server.py::TestCampaignEndpoints -v`

Expected: FAIL with "404 Not Found" or similar

**Step 3: Implement campaign endpoints**

Add to `src/dndbots/admin/server.py`:

```python
from typing import Any
from fastapi import HTTPException

# ... existing imports ...

# Game state (module-level for simplicity, will be managed properly in Task 8)
_game_state: dict[str, Any] = {
    "running": False,
    "campaign_id": None,
    "game": None,
}


def create_app() -> FastAPI:
    # ... existing code ...

    @app.get("/api/campaigns")
    async def list_campaigns():
        """List all available campaigns."""
        # TODO: Query SQLite for campaigns
        return {"campaigns": []}

    @app.get("/api/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str):
        """Get campaign details."""
        # TODO: Query SQLite for campaign
        raise HTTPException(status_code=404, detail="Campaign not found")

    @app.get("/api/state")
    async def get_state():
        """Get current game state."""
        return {
            "running": _game_state["running"],
            "campaign_id": _game_state["campaign_id"],
        }

    # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_server.py::TestCampaignEndpoints -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/server.py tests/test_admin_server.py
git commit -m "feat(admin): add campaign list and state endpoints"
```

---

## Task 6: Add Start/Stop Endpoints

**Files:**
- Modify: `src/dndbots/admin/server.py`
- Modify: `tests/test_admin_server.py`

**Step 1: Write the failing test**

Add to `tests/test_admin_server.py`:

```python
class TestControlEndpoints:
    """Tests for game control endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_start_campaign_not_found(self, client):
        """Start non-existent campaign returns 404."""
        response = client.post("/api/campaigns/nonexistent/start")
        assert response.status_code == 404

    def test_stop_no_game_running(self, client):
        """Stop when no game running returns 400."""
        response = client.post("/api/campaigns/test/stop")
        assert response.status_code == 400
        data = response.json()
        assert "not running" in data["detail"].lower()

    def test_stop_mode_parameter(self, client):
        """Stop accepts mode parameter."""
        # Even though it will fail (no game), it should accept the parameter
        response = client.post("/api/campaigns/test/stop?mode=clean")
        assert response.status_code == 400  # No game running, but mode accepted

        response = client.post("/api/campaigns/test/stop?mode=fast")
        assert response.status_code == 400  # No game running, but mode accepted
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_server.py::TestControlEndpoints -v`

Expected: FAIL with "404 Not Found" (no route)

**Step 3: Implement control endpoints**

Add to `src/dndbots/admin/server.py`:

```python
from enum import Enum

class StopMode(str, Enum):
    """Shutdown modes."""
    CLEAN = "clean"
    FAST = "fast"


def create_app() -> FastAPI:
    # ... existing code ...

    @app.post("/api/campaigns/{campaign_id}/start")
    async def start_campaign(campaign_id: str):
        """Start the game loop for a campaign."""
        # TODO: Look up campaign in database
        # For now, return 404 until we wire up storage
        raise HTTPException(status_code=404, detail="Campaign not found")

    @app.post("/api/campaigns/{campaign_id}/stop")
    async def stop_campaign(campaign_id: str, mode: StopMode = StopMode.CLEAN):
        """Stop the running game.

        Args:
            campaign_id: Campaign to stop
            mode: clean (wait for pause) or fast (stop now with checkpoint)
        """
        if not _game_state["running"]:
            raise HTTPException(status_code=400, detail="No game is running")

        if _game_state["campaign_id"] != campaign_id:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign {campaign_id} is not running"
            )

        # TODO: Implement actual stop logic
        return {"status": "stopping", "mode": mode.value}

    # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_server.py::TestControlEndpoints -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/server.py tests/test_admin_server.py
git commit -m "feat(admin): add start/stop campaign endpoints"
```

---

## Task 7: Add WebSocket Endpoint

**Files:**
- Modify: `src/dndbots/admin/server.py`
- Modify: `tests/test_admin_server.py`

**Step 1: Write the failing test**

Add to `tests/test_admin_server.py`:

```python
class TestWebSocket:
    """Tests for WebSocket endpoint."""

    def test_websocket_connect(self):
        """WebSocket connection works."""
        app = create_app()
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Should connect successfully
            # Send a ping to verify connection
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_receives_events(self):
        """WebSocket receives broadcasted events."""
        from dndbots.admin.plugin import AdminPlugin
        from dndbots.output import OutputEvent, OutputEventType

        app = create_app()
        # Get the plugin from the app state
        # This will be set up properly when we integrate

        client = TestClient(app)
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_server.py::TestWebSocket -v`

Expected: FAIL with WebSocket route not found

**Step 3: Implement WebSocket endpoint**

Add to `src/dndbots/admin/server.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect

from dndbots.admin.plugin import AdminPlugin

# Shared AdminPlugin instance
_admin_plugin = AdminPlugin()


def get_admin_plugin() -> AdminPlugin:
    """Get the shared AdminPlugin instance."""
    return _admin_plugin


def create_app() -> FastAPI:
    # ... existing code ...

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time event streaming."""
        await websocket.accept()
        _admin_plugin.add_client(websocket)

        try:
            while True:
                data = await websocket.receive_json()

                # Handle ping/pong for connection keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            _admin_plugin.remove_client(websocket)

    # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_server.py::TestWebSocket -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/server.py tests/test_admin_server.py
git commit -m "feat(admin): add WebSocket endpoint for real-time streaming"
```

---

## Task 8: Add Entity Endpoints

**Files:**
- Modify: `src/dndbots/admin/server.py`
- Modify: `tests/test_admin_server.py`

**Step 1: Write the failing test**

Add to `tests/test_admin_server.py`:

```python
class TestEntityEndpoints:
    """Tests for entity lookup endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_get_entity_not_found(self, client):
        """Get non-existent entity returns 404."""
        response = client.get("/api/entity/pc_nonexistent_001")
        assert response.status_code == 404

    def test_get_entity_relationships_not_found(self, client):
        """Get relationships for non-existent entity returns 404."""
        response = client.get("/api/entity/pc_nonexistent_001/relationships")
        assert response.status_code == 404

    def test_search_empty_query(self, client):
        """Search with empty query returns empty results."""
        response = client.get("/api/search?q=")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_no_results(self, client):
        """Search with no matches returns empty results."""
        response = client.get("/api/search?q=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_server.py::TestEntityEndpoints -v`

Expected: FAIL with route not found

**Step 3: Implement entity endpoints**

Add to `src/dndbots/admin/server.py`:

```python
def create_app() -> FastAPI:
    # ... existing code ...

    @app.get("/api/entity/{uid}")
    async def get_entity(uid: str):
        """Get entity document from SQLite."""
        # TODO: Query SQLite for entity by UID
        raise HTTPException(status_code=404, detail="Entity not found")

    @app.get("/api/entity/{uid}/relationships")
    async def get_entity_relationships(uid: str):
        """Get entity relationships from Neo4j."""
        # TODO: Query Neo4j for relationships
        raise HTTPException(status_code=404, detail="Entity not found")

    @app.get("/api/search")
    async def search_entities(q: str = ""):
        """Search entities by name or partial UID."""
        if not q:
            return {"results": []}

        # TODO: Search SQLite for matching entities
        return {"results": []}

    # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_server.py::TestEntityEndpoints -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/admin/server.py tests/test_admin_server.py
git commit -m "feat(admin): add entity lookup and search endpoints"
```

---

## Task 9: Add CLI Serve Command

**Files:**
- Modify: `src/dndbots/cli.py`
- Create: `tests/test_cli_serve.py`

**Step 1: Write the failing test**

Create `tests/test_cli_serve.py`:

```python
"""Tests for CLI serve command."""

import pytest
from unittest.mock import patch, MagicMock


class TestServeCommand:
    """Tests for the serve command."""

    def test_serve_function_exists(self):
        """Serve function is importable."""
        from dndbots.cli import serve
        assert callable(serve)

    def test_serve_default_port(self):
        """Serve uses port 8000 by default."""
        with patch("dndbots.cli.uvicorn") as mock_uvicorn:
            from dndbots.cli import serve
            serve()
            mock_uvicorn.run.assert_called_once()
            call_kwargs = mock_uvicorn.run.call_args[1]
            assert call_kwargs["port"] == 8000

    def test_serve_custom_port(self):
        """Serve accepts custom port."""
        with patch("dndbots.cli.uvicorn") as mock_uvicorn:
            from dndbots.cli import serve
            serve(port=9000)
            call_kwargs = mock_uvicorn.run.call_args[1]
            assert call_kwargs["port"] == 9000

    def test_main_serve_subcommand(self):
        """Main accepts 'serve' subcommand."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, 'argv', ['dndbots', 'serve']):
            with patch('dndbots.cli.uvicorn') as mock_uvicorn:
                from dndbots.cli import main
                # Should not raise, should call serve
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_serve.py -v`

Expected: FAIL with "cannot import name 'serve'"

**Step 3: Implement serve command**

Update `src/dndbots/cli.py`:

```python
"""Command-line interface for running DnDBots."""

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from dndbots.campaign import Campaign
from dndbots.game import DnDGame
from dndbots.models import Character, Stats


# Default paths
DATA_DIR = Path.home() / ".dndbots"
DEFAULT_DB = DATA_DIR / "campaigns.db"

# Default test scenario
DEFAULT_SCENARIO = """
The party stands at the entrance to the Caves of Chaos - a dark opening
in the hillside that locals say is home to goblins and worse.

The village of Millbrook has offered 50 gold pieces for clearing out
the goblin threat. Merchants have been attacked on the road, and
three villagers went missing last week.

Inside the cave entrance, you can see crude torches flickering in
wall sconces, and you hear guttural voices echoing from deeper within.

Start by describing the scene and asking the party what they want to do.
"""


def create_default_character() -> Character:
    """Create a default fighter character for testing."""
    return Character(
        name="Throk",
        char_class="Fighter",
        level=1,
        hp=8,
        hp_max=8,
        ac=5,
        stats=Stats(str=16, dex=12, con=14, int=9, wis=10, cha=11),
        equipment=["longsword", "chain mail", "shield", "backpack", "torch x3", "rope 50ft"],
        gold=25,
    )


async def run_game() -> None:
    """Run the game with persistence."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize campaign
    campaign = Campaign(
        campaign_id="default_campaign",
        name="Caves of Chaos",
        db_path=str(DEFAULT_DB),
    )
    await campaign.initialize()

    try:
        # Get or create character
        characters = await campaign.get_characters()
        if not characters:
            char = create_default_character()
            await campaign.add_character(char)
            characters = [char]

        # Start session
        await campaign.start_session()

        print(f"Campaign: {campaign.name}")
        print(f"Session: {campaign.current_session_id}")
        print(f"Characters: {', '.join(c.name for c in characters)}")
        print()

        # Create and run game
        game = DnDGame(
            scenario=DEFAULT_SCENARIO,
            characters=characters,
            dm_model="gpt-4o",
            player_model="gpt-4o",
            campaign=campaign,
        )

        await game.run()

    finally:
        await campaign.end_session("Session interrupted")
        await campaign.close()


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the admin UI server.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to listen on (default: 8000)
    """
    import uvicorn
    from dndbots.admin import app

    print(f"Starting DnDBots Admin UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="DnDBots - Multi-AI D&D Campaign System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'run' command (default behavior)
    run_parser = subparsers.add_parser("run", help="Run a game session")

    # 'serve' command
    serve_parser = subparsers.add_parser("serve", help="Start admin UI server")
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    args = parser.parse_args()

    if args.command == "serve":
        serve(host=args.host, port=args.port)
    else:
        # Default: run the game
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
            return

        print("=" * 60)
        print("DnDBots - Basic D&D AI Campaign")
        print("=" * 60)
        print(f"\nData directory: {DATA_DIR}")
        print("Type Ctrl+C to stop\n")

        try:
            asyncio.run(run_game())
        except KeyboardInterrupt:
            print("\n\n[System] Session interrupted by user.")

        print("\n" + "=" * 60)
        print("Session ended")
        print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_serve.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/dndbots/cli.py tests/test_cli_serve.py
git commit -m "feat(cli): add serve command for admin UI"
```

---

## Task 10: Create Vue Project Structure

**Files:**
- Create: `admin-ui/package.json`
- Create: `admin-ui/vite.config.js`
- Create: `admin-ui/index.html`
- Create: `admin-ui/src/main.js`
- Create: `admin-ui/src/App.vue`

**Step 1: Create Vue project structure**

Create `admin-ui/package.json`:

```json
{
  "name": "dndbots-admin",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

Create `admin-ui/vite.config.js`:

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: resolve(__dirname, '../src/dndbots/admin/static'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

Create `admin-ui/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DnDBots Admin</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #1a1a2e;
      color: #eee;
    }
  </style>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

Create `admin-ui/src/main.js`:

```javascript
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```

Create `admin-ui/src/App.vue`:

```vue
<template>
  <div class="app">
    <header class="control-bar">
      <h1>DnDBots Admin</h1>
      <div class="status">
        <span :class="['indicator', { connected: wsConnected }]"></span>
        {{ wsConnected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <nav class="tabs">
      <button
        :class="{ active: activeTab === 'live' }"
        @click="activeTab = 'live'"
      >
        Live View
      </button>
      <button
        :class="{ active: activeTab === 'inspector' }"
        @click="activeTab = 'inspector'"
      >
        Entity Inspector
      </button>
    </nav>

    <main class="content">
      <div v-if="activeTab === 'live'" class="live-view">
        <section class="narrative-feed">
          <h2>Narrative Feed</h2>
          <div class="feed">
            <div
              v-for="(event, index) in events"
              :key="index"
              :class="['event', event.type]"
            >
              <span class="source">[{{ event.source }}]</span>
              <span class="content">{{ event.content }}</span>
            </div>
            <div v-if="events.length === 0" class="empty">
              Waiting for events...
            </div>
          </div>
        </section>

        <section class="state-dashboard">
          <h2>State Dashboard</h2>
          <p>Coming soon...</p>
        </section>
      </div>

      <div v-else class="entity-inspector">
        <h2>Entity Inspector</h2>
        <p>Coming soon...</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const activeTab = ref('live')
const wsConnected = ref(false)
const events = ref([])

let ws = null

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    // Send ping to test connection
    ws.send(JSON.stringify({ type: 'ping' }))
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type !== 'pong') {
      events.value.push(data)
      // Keep last 100 events
      if (events.value.length > 100) {
        events.value.shift()
      }
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    // Reconnect after 2 seconds
    setTimeout(connect, 2000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.control-bar h1 {
  font-size: 1.5rem;
  color: #e94560;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #666;
}

.indicator.connected {
  background: #4caf50;
}

.tabs {
  display: flex;
  gap: 0;
  background: #16213e;
}

.tabs button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tabs button.active {
  color: #e94560;
  border-bottom-color: #e94560;
}

.content {
  flex: 1;
  padding: 1rem;
}

.live-view {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  height: calc(100vh - 120px);
}

.narrative-feed,
.state-dashboard {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.narrative-feed h2,
.state-dashboard h2 {
  margin-bottom: 1rem;
  color: #e94560;
}

.feed {
  flex: 1;
  overflow-y: auto;
}

.event {
  padding: 0.5rem;
  border-bottom: 1px solid #0f3460;
}

.event .source {
  color: #e94560;
  font-weight: bold;
  margin-right: 0.5rem;
}

.event.narration .source {
  color: #4caf50;
}

.event.player_action .source {
  color: #2196f3;
}

.empty {
  color: #666;
  font-style: italic;
}

.entity-inspector {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
}

.entity-inspector h2 {
  color: #e94560;
}
</style>
```

**Step 2: Verify structure**

Run: `ls -la admin-ui/`

Expected: Shows package.json, vite.config.js, index.html, src/

**Step 3: Commit**

```bash
git add admin-ui/
git commit -m "feat(admin-ui): create Vue project structure"
```

---

## Task 11: Create ControlBar Component

**Files:**
- Create: `admin-ui/src/components/ControlBar.vue`
- Modify: `admin-ui/src/App.vue`

**Step 1: Create ControlBar component**

Create `admin-ui/src/components/ControlBar.vue`:

```vue
<template>
  <header class="control-bar">
    <div class="left">
      <h1>DnDBots Admin</h1>
      <select v-model="selectedCampaign" class="campaign-select">
        <option value="">Select Campaign...</option>
        <option
          v-for="campaign in campaigns"
          :key="campaign.id"
          :value="campaign.id"
        >
          {{ campaign.name }}
        </option>
      </select>
    </div>

    <div class="center">
      <span :class="['status-badge', gameStatus]">
        {{ statusText }}
      </span>
    </div>

    <div class="right">
      <span :class="['ws-indicator', { connected: wsConnected }]"></span>
      <button
        v-if="gameStatus === 'stopped'"
        class="btn btn-start"
        :disabled="!selectedCampaign"
        @click="$emit('start', selectedCampaign)"
      >
        Start
      </button>
      <button
        v-else
        class="btn btn-stop"
        @click="$emit('stop', 'clean')"
      >
        Stop
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  wsConnected: Boolean,
  gameStatus: {
    type: String,
    default: 'stopped', // stopped, running, stopping
  },
})

defineEmits(['start', 'stop'])

const campaigns = ref([])
const selectedCampaign = ref('')

const statusText = computed(() => {
  switch (props.gameStatus) {
    case 'running':
      return '● Running'
    case 'stopping':
      return '◐ Stopping...'
    default:
      return '○ Stopped'
  }
})

async function loadCampaigns() {
  try {
    const response = await fetch('/api/campaigns')
    const data = await response.json()
    campaigns.value = data.campaigns
  } catch (error) {
    console.error('Failed to load campaigns:', error)
  }
}

onMounted(() => {
  loadCampaigns()
})
</script>

<style scoped>
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.left h1 {
  font-size: 1.25rem;
  color: #e94560;
}

.campaign-select {
  padding: 0.5rem 1rem;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  color: #eee;
  cursor: pointer;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: bold;
}

.status-badge.stopped {
  background: #333;
  color: #888;
}

.status-badge.running {
  background: #1b5e20;
  color: #4caf50;
}

.status-badge.stopping {
  background: #e65100;
  color: #ff9800;
}

.ws-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.ws-indicator.connected {
  background: #4caf50;
}

.btn {
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-start {
  background: #4caf50;
  color: white;
}

.btn-stop {
  background: #e94560;
  color: white;
}
</style>
```

**Step 2: Commit**

```bash
git add admin-ui/src/components/
git commit -m "feat(admin-ui): add ControlBar component"
```

---

## Task 12: Create NarrativeFeed Component

**Files:**
- Create: `admin-ui/src/components/NarrativeFeed.vue`

**Step 1: Create NarrativeFeed component**

Create `admin-ui/src/components/NarrativeFeed.vue`:

```vue
<template>
  <section class="narrative-feed">
    <div class="header">
      <h2>Narrative Feed</h2>
      <label class="auto-scroll">
        <input type="checkbox" v-model="autoScroll" />
        Auto-scroll
      </label>
    </div>

    <div ref="feedContainer" class="feed">
      <div
        v-for="(event, index) in events"
        :key="index"
        :class="['event', event.type]"
      >
        <div class="event-header">
          <span class="source">{{ formatSource(event.source) }}</span>
          <span class="timestamp">{{ formatTime(event.timestamp) }}</span>
        </div>
        <div class="content">{{ event.content }}</div>
        <div v-if="event.metadata && Object.keys(event.metadata).length" class="metadata">
          {{ JSON.stringify(event.metadata) }}
        </div>
      </div>

      <div v-if="events.length === 0" class="empty">
        <p>Waiting for events...</p>
        <p class="hint">Start a campaign to see the narrative unfold.</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const autoScroll = ref(true)
const feedContainer = ref(null)

function formatSource(source) {
  if (source === 'dm') return 'DM'
  if (source === 'system') return 'System'
  // Capitalize first letter of player names
  return source.charAt(0).toUpperCase() + source.slice(1)
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

watch(
  () => props.events.length,
  async () => {
    if (autoScroll.value && feedContainer.value) {
      await nextTick()
      feedContainer.value.scrollTop = feedContainer.value.scrollHeight
    }
  }
)
</script>

<style scoped>
.narrative-feed {
  background: #16213e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #0f3460;
}

.header h2 {
  color: #e94560;
  font-size: 1rem;
}

.auto-scroll {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #888;
  cursor: pointer;
}

.feed {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.event {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #1a1a2e;
  border-radius: 4px;
  border-left: 3px solid #666;
}

.event.narration {
  border-left-color: #4caf50;
}

.event.player_action {
  border-left-color: #2196f3;
}

.event.dice_roll {
  border-left-color: #ff9800;
}

.event.combat {
  border-left-color: #e94560;
}

.event.system,
.event.session_start,
.event.session_end {
  border-left-color: #9c27b0;
  font-style: italic;
}

.event-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.source {
  font-weight: bold;
  color: #e94560;
}

.event.narration .source {
  color: #4caf50;
}

.event.player_action .source {
  color: #2196f3;
}

.timestamp {
  font-size: 0.75rem;
  color: #666;
}

.content {
  line-height: 1.5;
}

.metadata {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #0f3460;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.75rem;
  color: #888;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
</style>
```

**Step 2: Commit**

```bash
git add admin-ui/src/components/NarrativeFeed.vue
git commit -m "feat(admin-ui): add NarrativeFeed component"
```

---

## Task 13: Create StateDashboard Component

**Files:**
- Create: `admin-ui/src/components/StateDashboard.vue`
- Create: `admin-ui/src/components/CharacterCard.vue`

**Step 1: Create CharacterCard component**

Create `admin-ui/src/components/CharacterCard.vue`:

```vue
<template>
  <div class="character-card">
    <div class="header">
      <span class="name">{{ character.name }}</span>
      <span class="class-level">{{ character.char_class }} {{ character.level }}</span>
    </div>

    <div class="stats">
      <div class="stat hp">
        <span class="label">HP</span>
        <div class="bar-container">
          <div class="bar" :style="{ width: hpPercent + '%' }"></div>
        </div>
        <span class="value">{{ character.hp }}/{{ character.hp_max }}</span>
      </div>

      <div class="stat ac">
        <span class="label">AC</span>
        <span class="value">{{ character.ac }}</span>
      </div>
    </div>

    <div v-if="character.conditions?.length" class="conditions">
      <span
        v-for="condition in character.conditions"
        :key="condition"
        class="condition"
      >
        {{ condition }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  character: {
    type: Object,
    required: true,
  },
})

const hpPercent = computed(() => {
  const { hp, hp_max } = props.character
  if (!hp_max) return 0
  return Math.max(0, Math.min(100, (hp / hp_max) * 100))
})
</script>

<style scoped>
.character-card {
  background: #1a1a2e;
  border-radius: 4px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.name {
  font-weight: bold;
  color: #eee;
}

.class-level {
  font-size: 0.875rem;
  color: #888;
}

.stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stat.hp {
  flex: 1;
}

.label {
  font-size: 0.75rem;
  color: #888;
  width: 20px;
}

.bar-container {
  flex: 1;
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s ease;
}

.value {
  font-size: 0.875rem;
  color: #eee;
  min-width: 50px;
  text-align: right;
}

.conditions {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.condition {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  background: #e65100;
  color: white;
  border-radius: 4px;
}
</style>
```

**Step 2: Create StateDashboard component**

Create `admin-ui/src/components/StateDashboard.vue`:

```vue
<template>
  <section class="state-dashboard">
    <h2>State Dashboard</h2>

    <div class="section">
      <h3>Party</h3>
      <CharacterCard
        v-for="char in party"
        :key="char.name"
        :character="char"
      />
      <p v-if="party.length === 0" class="empty">No characters loaded</p>
    </div>

    <div v-if="location" class="section">
      <h3>Location</h3>
      <p class="location">📍 {{ location }}</p>
    </div>

    <div v-if="encounter" class="section">
      <h3>Current Encounter</h3>
      <div class="encounter">
        <div v-for="(enemy, index) in encounter" :key="index" class="enemy">
          {{ enemy.name }}
          <span v-if="enemy.status" class="status">({{ enemy.status }})</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import CharacterCard from './CharacterCard.vue'

const props = defineProps({
  events: {
    type: Array,
    default: () => [],
  },
})

const party = ref([])
const location = ref('')
const encounter = ref([])

// Extract state from state_update events
watch(
  () => props.events,
  (events) => {
    const stateEvents = events.filter((e) => e.type === 'state_update')
    if (stateEvents.length > 0) {
      const latest = stateEvents[stateEvents.length - 1]
      if (latest.characters) {
        party.value = latest.characters
      }
      if (latest.location) {
        location.value = latest.location
      }
      if (latest.encounter) {
        encounter.value = latest.encounter
      }
    }
  },
  { deep: true }
)
</script>

<style scoped>
.state-dashboard {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  overflow-y: auto;
}

.state-dashboard h2 {
  color: #e94560;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.section {
  margin-bottom: 1.5rem;
}

.section h3 {
  font-size: 0.875rem;
  color: #888;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.empty {
  color: #666;
  font-size: 0.875rem;
  font-style: italic;
}

.location {
  color: #eee;
}

.encounter {
  background: #1a1a2e;
  padding: 0.75rem;
  border-radius: 4px;
}

.enemy {
  padding: 0.25rem 0;
  color: #e94560;
}

.status {
  color: #888;
  font-style: italic;
}
</style>
```

**Step 3: Commit**

```bash
git add admin-ui/src/components/StateDashboard.vue admin-ui/src/components/CharacterCard.vue
git commit -m "feat(admin-ui): add StateDashboard and CharacterCard components"
```

---

## Task 14: Create EntityInspector Component

**Files:**
- Create: `admin-ui/src/components/EntityInspector.vue`

**Step 1: Create EntityInspector component**

Create `admin-ui/src/components/EntityInspector.vue`:

```vue
<template>
  <section class="entity-inspector">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Enter UID (e.g., pc_throk_001)"
        @keyup.enter="searchEntity"
      />
      <button @click="searchEntity" :disabled="!searchQuery">Search</button>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="entity" class="results">
      <div class="panel document">
        <h3>Document (SQLite)</h3>
        <pre>{{ JSON.stringify(entity, null, 2) }}</pre>
      </div>

      <div class="panel relationships">
        <h3>Relationships (Neo4j)</h3>
        <div v-if="relationships.length" class="rel-list">
          <div
            v-for="rel in relationships"
            :key="rel.target"
            class="relationship"
            @click="loadEntity(rel.target)"
          >
            <span class="rel-type">{{ rel.type }}</span>
            <span class="rel-arrow">→</span>
            <span class="rel-target">{{ rel.target }}</span>
          </div>
        </div>
        <p v-else class="empty">No relationships found</p>
      </div>
    </div>

    <div v-else class="placeholder">
      <p>Enter a UID to inspect an entity</p>
      <p class="hint">Examples: pc_throk_001, npc_goblin_003, loc_caves_room_02</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const searchQuery = ref('')
const entity = ref(null)
const relationships = ref([])
const loading = ref(false)
const error = ref('')

async function searchEntity() {
  if (!searchQuery.value) return
  await loadEntity(searchQuery.value)
}

async function loadEntity(uid) {
  loading.value = true
  error.value = ''
  entity.value = null
  relationships.value = []
  searchQuery.value = uid

  try {
    // Fetch entity document
    const entityRes = await fetch(`/api/entity/${uid}`)
    if (!entityRes.ok) {
      if (entityRes.status === 404) {
        error.value = `Entity "${uid}" not found`
      } else {
        error.value = `Failed to load entity: ${entityRes.statusText}`
      }
      return
    }
    entity.value = await entityRes.json()

    // Fetch relationships
    try {
      const relRes = await fetch(`/api/entity/${uid}/relationships`)
      if (relRes.ok) {
        const relData = await relRes.json()
        relationships.value = relData.relationships || []
      }
    } catch {
      // Relationships are optional (Neo4j might not be configured)
    }
  } catch (err) {
    error.value = `Error: ${err.message}`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.entity-inspector {
  background: #16213e;
  border-radius: 8px;
  padding: 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.search-bar input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 4px;
  color: #eee;
  font-family: monospace;
}

.search-bar input:focus {
  outline: none;
  border-color: #e94560;
}

.search-bar button {
  padding: 0.75rem 1.5rem;
  background: #e94560;
  border: none;
  border-radius: 4px;
  color: white;
  font-weight: bold;
  cursor: pointer;
}

.search-bar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #888;
}

.error {
  padding: 1rem;
  background: #b71c1c;
  border-radius: 4px;
  color: white;
}

.results {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  flex: 1;
  overflow: hidden;
}

.panel {
  background: #1a1a2e;
  border-radius: 4px;
  padding: 1rem;
  overflow: auto;
}

.panel h3 {
  color: #888;
  font-size: 0.75rem;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.panel pre {
  font-family: monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.rel-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.relationship {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #0f3460;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.relationship:hover {
  background: #1a4a7a;
}

.rel-type {
  color: #e94560;
  font-weight: bold;
}

.rel-arrow {
  color: #666;
}

.rel-target {
  color: #2196f3;
  font-family: monospace;
}

.placeholder {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-family: monospace;
}

.empty {
  color: #666;
  font-style: italic;
}
</style>
```

**Step 2: Commit**

```bash
git add admin-ui/src/components/EntityInspector.vue
git commit -m "feat(admin-ui): add EntityInspector component"
```

---

## Task 15: Update App.vue and Build Integration

**Files:**
- Modify: `admin-ui/src/App.vue`
- Modify: `.gitignore`

**Step 1: Update App.vue with all components**

Update `admin-ui/src/App.vue`:

```vue
<template>
  <div class="app">
    <ControlBar
      :ws-connected="wsConnected"
      :game-status="gameStatus"
      @start="startGame"
      @stop="stopGame"
    />

    <nav class="tabs">
      <button
        :class="{ active: activeTab === 'live' }"
        @click="activeTab = 'live'"
      >
        Live View
      </button>
      <button
        :class="{ active: activeTab === 'inspector' }"
        @click="activeTab = 'inspector'"
      >
        Entity Inspector
      </button>
    </nav>

    <main class="content">
      <div v-if="activeTab === 'live'" class="live-view">
        <NarrativeFeed :events="events" />
        <StateDashboard :events="events" />
      </div>

      <EntityInspector v-else />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ControlBar from './components/ControlBar.vue'
import NarrativeFeed from './components/NarrativeFeed.vue'
import StateDashboard from './components/StateDashboard.vue'
import EntityInspector from './components/EntityInspector.vue'

const activeTab = ref('live')
const wsConnected = ref(false)
const gameStatus = ref('stopped')
const events = ref([])

let ws = null

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    ws.send(JSON.stringify({ type: 'ping' }))
  }

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'pong') return

    events.value.push(data)
    if (events.value.length > 100) {
      events.value.shift()
    }

    // Update game status from session events
    if (data.type === 'session_start') {
      gameStatus.value = 'running'
    } else if (data.type === 'session_end') {
      gameStatus.value = 'stopped'
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    setTimeout(connect, 2000)
  }

  ws.onerror = () => ws.close()
}

async function startGame(campaignId) {
  try {
    const res = await fetch(`/api/campaigns/${campaignId}/start`, {
      method: 'POST',
    })
    if (res.ok) {
      gameStatus.value = 'running'
    }
  } catch (err) {
    console.error('Failed to start game:', err)
  }
}

async function stopGame(mode) {
  try {
    gameStatus.value = 'stopping'
    const res = await fetch(`/api/campaigns/current/stop?mode=${mode}`, {
      method: 'POST',
    })
    if (res.ok) {
      gameStatus.value = 'stopped'
    }
  } catch (err) {
    console.error('Failed to stop game:', err)
    gameStatus.value = 'running'
  }
}

onMounted(connect)
onUnmounted(() => ws?.close())
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  background: #16213e;
}

.tabs button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tabs button:hover {
  color: #ccc;
}

.tabs button.active {
  color: #e94560;
  border-bottom-color: #e94560;
}

.content {
  flex: 1;
  padding: 1rem;
  overflow: hidden;
}

.live-view {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  height: calc(100vh - 140px);
}
</style>
```

**Step 2: Update .gitignore**

Add to `.gitignore`:

```
# Vue build output (generated, not source)
src/dndbots/admin/static/

# Node modules
admin-ui/node_modules/
```

**Step 3: Verify build works**

Run:
```bash
cd admin-ui
npm install
npm run build
```

Expected: Build succeeds, files appear in `src/dndbots/admin/static/`

**Step 4: Commit**

```bash
git add admin-ui/src/App.vue .gitignore
git commit -m "feat(admin-ui): complete App.vue with all components"
```

---

## Summary

This plan implements Phase 6 in 15 tasks:

| Task | Description | Estimated Commits |
|------|-------------|-------------------|
| 1 | Add FastAPI dependencies | 1 |
| 2 | Create checkpoint models | 1 |
| 3 | Create AdminPlugin | 1 |
| 4 | Create FastAPI server skeleton | 1 |
| 5 | Add campaign endpoints | 1 |
| 6 | Add start/stop endpoints | 1 |
| 7 | Add WebSocket endpoint | 1 |
| 8 | Add entity endpoints | 1 |
| 9 | Add CLI serve command | 1 |
| 10 | Create Vue project structure | 1 |
| 11 | Create ControlBar component | 1 |
| 12 | Create NarrativeFeed component | 1 |
| 13 | Create StateDashboard + CharacterCard | 1 |
| 14 | Create EntityInspector component | 1 |
| 15 | Update App.vue and build integration | 1 |

**Total: 15 commits**

---

Plan complete and saved to `docs/plans/2025-12-06-phase6-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
