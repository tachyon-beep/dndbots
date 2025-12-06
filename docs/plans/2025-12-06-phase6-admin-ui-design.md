# Phase 6: Admin UI Design

**Date:** 2025-12-06
**Status:** Design Complete
**Goal:** Local monitoring dashboard for watching and controlling DnDBots campaigns

---

## Overview

A browser-based admin UI for developer/operator use. Primary focus is **monitoring** - watching the AI D&D game unfold in real-time. Secondary focus is basic **control** (start/stop) and **debugging** (entity inspection).

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary user | Developer/operator | Not a public viewer (future enhancement) |
| Deployment | Local browser (localhost:8000) | No auth needed |
| Architecture | Integrated (single process) | Simple, EventBus integration natural |
| Real-time | WebSocket streaming | Instant updates as events happen |
| Frontend | Vue 3 SPA | Simpler than React, great reactivity |
| Control | Start/stop only | Minimal scope for v1 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (localhost:8000)                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Vue SPA                                                    ││
│  │  ├── Narrative Feed (left panel)                            ││
│  │  ├── State Dashboard (right panel)                          ││
│  │  ├── Control Bar (top: start/stop)                          ││
│  │  └── Entity Inspector (tab)                                 ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Server                                                 │
│  ├── GET  /                    → Serve Vue SPA                  │
│  ├── GET  /api/campaigns       → List campaigns                 │
│  ├── POST /api/campaigns/{id}/start → Start game                │
│  ├── POST /api/campaigns/{id}/stop  → Stop game                 │
│  ├── GET  /api/state           → Current game state             │
│  ├── GET  /api/entity/{uid}    → Entity from SQLite             │
│  ├── GET  /api/entity/{uid}/relationships → Links from Neo4j   │
│  └── WS   /ws                  → Real-time event stream         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  DnDGame + EventBus                                             │
│  └── AdminPlugin → pushes OutputEvents to WebSocket clients     │
└─────────────────────────────────────────────────────────────────┘
```

The FastAPI server runs in the same process as the game. When you start a campaign via the API, it spawns the game loop as an asyncio task. The `AdminPlugin` registers with the EventBus and broadcasts all game events to connected WebSocket clients.

---

## REST API

| Method | Path | Purpose |
|--------|------|---------|
| `GET /` | Serve Vue SPA (index.html + assets) |
| `GET /api/campaigns` | List available campaigns from DB |
| `GET /api/campaigns/{id}` | Get campaign details (characters, session count) |
| `POST /api/campaigns/{id}/start` | Start game loop for campaign |
| `POST /api/campaigns/{id}/stop?mode=clean` | Graceful stop at narrative pause |
| `POST /api/campaigns/{id}/stop?mode=fast` | Stop now, checkpoint state |
| `GET /api/state` | Current game state snapshot |
| `GET /api/entity/{uid}` | Get entity document from SQLite |
| `GET /api/entity/{uid}/relationships` | Get graph links from Neo4j |
| `GET /api/search?q=throk` | Search entities by name/partial UID |

---

## WebSocket Protocol

Clients connect to `/ws` and receive JSON messages as events happen:

```json
{"type": "narration", "source": "dm", "content": "The goblin lunges...", "timestamp": "..."}
{"type": "player_action", "source": "pc_throk_001", "content": "I swing my axe!", "timestamp": "..."}
{"type": "dice_roll", "source": "system", "content": "d20+3 = 17", "metadata": {"result": 17}}
{"type": "state_update", "characters": [...], "location": "..."}
```

The `AdminPlugin` converts `OutputEvent` objects to JSON and broadcasts to all connected clients. State updates are sent periodically (every turn) or on significant changes (HP loss, location change).

---

## Frontend Layout

### Live View Tab

```
┌─────────────────────────────────────────────────────────────────┐
│  Control Bar                                                    │
│  [Campaign: Caves of Chaos ▼]  [● Running]  [Stop]              │
├─────────────────────────────────────────────────────────────────┤
│  [Live View]  [Entity Inspector]                                │
├────────────────────────────────┬────────────────────────────────┤
│  Narrative Feed                │  State Dashboard               │
│  ────────────────────────────  │  ────────────────────────────  │
│  [dm] The goblin snarls...     │  PARTY                         │
│  [Throk] I raise my shield!    │  ├─ Throk (Fighter 2)          │
│  [Roll] d20+2 = 15 (hit)       │  │  HP: 12/18  AC: 16          │
│  [dm] Your blade finds its     │  │  @ Goblin Cave Room 2       │
│       mark. 6 damage!          │  ├─ Zara (Thief 2)             │
│  [Throk] "Stay down, beast!"   │  │  HP: 8/8   AC: 13           │
│                                │  └─ Pip (Magic-User 1)         │
│  ▼ auto-scroll                 │     HP: 3/4   AC: 10           │
│                                │                                │
│                                │  CURRENT ENCOUNTER             │
│                                │  └─ 2x Goblins (1 wounded)     │
└────────────────────────────────┴────────────────────────────────┘
```

### Entity Inspector Tab

```
┌─────────────────────────────────────────────────────────────────┐
│  Control Bar                                                    │
│  [Campaign: Caves of Chaos ▼]  [● Running]  [Stop]              │
├─────────────────────────────────────────────────────────────────┤
│  [Live View]  [Entity Inspector]                                │
├─────────────────────────────────────────────────────────────────┤
│  Entity Inspector                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🔍 [pc_throk_001                    ] [Search]              ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────┬───────────────────────────────────┐│
│  │ Document (SQLite)       │ Relationships (Neo4j)             ││
│  │ ─────────────────────── │ ─────────────────────────────────  ││
│  │ {                       │ pc_throk_001                      ││
│  │   "name": "Throk",      │   ├─ KILLED → npc_goblin_003     ││
│  │   "class": "Fighter",   │   ├─ KILLED → npc_goblin_007     ││
│  │   "level": 2,           │   ├─ PARTY_MEMBER → party_001    ││
│  │   "hp": 12,             │   ├─ LOCATED_AT → loc_cave_02    ││
│  │   ...                   │   └─ OWNS → item_axe_001         ││
│  │ }                       │                                   ││
│  │                         │ [Click any UID to inspect]        ││
│  └─────────────────────────┴───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

Clicking any UID in the relationships panel loads that entity - navigate the graph visually.

### Vue Components

| Component | Purpose |
|-----------|---------|
| `App.vue` | Main layout, WebSocket connection, tab routing |
| `ControlBar.vue` | Campaign selector, status indicator, start/stop buttons |
| `NarrativeFeed.vue` | Scrolling event log with auto-scroll |
| `StateDashboard.vue` | Party status, location, current encounter |
| `CharacterCard.vue` | Individual character HP/AC/status |
| `EntityInspector.vue` | UID search, document view, relationship graph |

---

## AdminPlugin

Bridges the EventBus to WebSocket clients:

```python
@dataclass
class AdminPlugin:
    """Output plugin that streams events to WebSocket clients."""

    name: str = "admin"
    handled_types: set[OutputEventType] | None = None  # Handle all
    _clients: set[WebSocket] = field(default_factory=set)

    def add_client(self, ws: WebSocket) -> None:
        self._clients.add(ws)

    def remove_client(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def handle(self, event: OutputEvent) -> None:
        """Broadcast event to all connected clients."""
        message = {
            "type": event.event_type.value,
            "source": event.source,
            "content": event.content,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat(),
        }
        dead_clients = []
        for ws in self._clients:
            try:
                await ws.send_json(message)
            except:
                dead_clients.append(ws)
        for ws in dead_clients:
            self._clients.discard(ws)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
```

---

## Shutdown Modes

Two stop modes for different situations:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `clean` | Wait for narrative pause (end of combat, scene break) | Normal shutdown |
| `fast` | Stop after current message, checkpoint full state | Need to stop now, will resume |

### Checkpoint Models

**Narrative checkpoint (minimal):**

```python
@dataclass
class NarrativeCheckpoint:
    """Enough for DM to resume narrative."""
    campaign_id: str
    session_id: str
    party_location: str              # Current location UID
    current_beat: str | None         # What's happening
    recent_events: list[str]         # Last 10 event IDs
    dm_notes: str                    # DM's own summary (from DCML)
```

**Combat checkpoint (full state):**

```python
@dataclass
class CombatCheckpoint:
    """Everything needed to resume mid-combat."""
    narrative: NarrativeCheckpoint   # Base state

    # Initiative
    initiative_order: list[str]      # UIDs in turn order
    current_turn: int                # Whose turn
    round_number: int

    # Combatant state
    combatants: dict[str, dict]      # {uid: {hp, conditions, position}}

    # Combat log
    rounds: list[dict]               # Every action, roll, result
```

### Stop Behavior

| Mode | In Combat | Not In Combat |
|------|-----------|---------------|
| `clean` | Finish combat, then stop | Find narrative pause, then stop |
| `fast` | Save `CombatCheckpoint`, stop now | Save `NarrativeCheckpoint`, stop now |

On resume, if combat checkpoint exists, reload the full combat state and continue from `current_turn`. Otherwise, feed the DM the recent events and let them pick up naturally.

---

## File Structure

```
src/dndbots/
├── admin/
│   ├── __init__.py
│   ├── server.py           # FastAPI app, routes, WebSocket
│   ├── plugin.py           # AdminPlugin for EventBus
│   ├── checkpoint.py       # NarrativeCheckpoint, CombatCheckpoint
│   └── static/             # Built Vue app (generated)
│       ├── index.html
│       ├── assets/
│       └── ...
│
├── admin-ui/               # Vue source (separate from Python)
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   │   ├── ControlBar.vue
│   │   │   ├── NarrativeFeed.vue
│   │   │   ├── StateDashboard.vue
│   │   │   ├── CharacterCard.vue
│   │   │   └── EntityInspector.vue
│   │   └── composables/
│   │       └── useWebSocket.js
│   └── ...
```

---

## Dependencies

**Python (backend):**

```toml
# Add to pyproject.toml
dependencies = [
    # ... existing ...
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",   # ASGI server with WebSocket support
    "websockets>=12.0",            # WebSocket library
]
```

**Node/Vue (frontend):**

```json
{
  "dependencies": {
    "vue": "^3.4",
    "vue-router": "^4.2"
  },
  "devDependencies": {
    "vite": "^5.0",
    "@vitejs/plugin-vue": "^5.0"
  }
}
```

---

## CLI Entry Point

```bash
dndbots serve              # Start admin server on localhost:8000
dndbots serve --port 9000  # Custom port
```

---

## Build Process

```bash
# Development: run Vue dev server + FastAPI separately
cd admin-ui && npm run dev    # localhost:5173 (with hot reload)
uvicorn dndbots.admin:app     # localhost:8000 (API only)

# Production: build Vue into static/, serve from FastAPI
cd admin-ui && npm run build  # outputs to ../src/dndbots/admin/static/
dndbots serve                 # Serves everything from one process
```

---

## Future Enhancements

- **Viewer page** - Human-friendly read-only view for audience
- **Authentication** - Token-based auth for remote access
- **Multiple campaigns** - Run several games simultaneously
- **Metrics** - Token usage, API costs, response times
- **Log viewer** - Browse historical sessions
