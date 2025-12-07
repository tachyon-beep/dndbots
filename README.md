# DnDBots

Multi-AI D&D campaign system where different frontier models (Claude, GPT, Gemini, DeepSeek) play Basic D&D (1983 Red Box) together. One AI serves as Dungeon Master, others play characters.

## Features

- **Multi-AI Orchestration**: AutoGen 0.4 SelectorGroupChat with DM-controlled turn order
- **Basic D&D Rules**: THAC0 combat, ability modifiers, saving throws from the 1983 Red Box
- **Persistent Campaigns**: SQLite for events/characters, Neo4j for relationships (optional)
- **BECMI Rules Integration**: Indexed rules with tool-based lookup for DM and players
- **DCML Memory System**: Compressed memory language for token-efficient state tracking
- **Extensible Output Layer**: Event bus with plugin architecture (console, JSON, callbacks)
- **Admin UI**: FastAPI backend with Vue.js frontend for campaign management
- **Transparent Mechanics**: All dice rolls visible with full breakdown

## Installation

```bash
# Clone and setup
git clone <repo-url>
cd dndbots
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Quick Start

```bash
# Run a game session
dndbots
```

This starts a session with:
- GPT-4o as Dungeon Master
- GPT-4o playing "Throk" the Fighter
- Default scenario: Caves of Chaos goblin adventure
- Data persisted to `~/.dndbots/campaigns.db`

## Project Structure

```
src/dndbots/
├── cli.py              # Command-line entry point
├── game.py             # AutoGen orchestration (DnDGame, SelectorGroupChat)
├── campaign.py         # Campaign manager (coordinates storage)
├── models.py           # Character, Stats dataclasses
├── events.py           # GameEvent schema for persistence
├── rules.py            # Basic D&D rules (THAC0, modifiers)
├── rules_index.py      # BECMI rules data models and index loading
├── rules_tools.py      # Tool functions for rules lookup
├── rules_prompts.py    # Rules summary generation for DM prompt
├── prompts.py          # DM and player system prompts
├── dice.py             # Dice rolling utilities
├── dcml.py             # DCML compression/decompression
├── event_bus.py        # Event bus with plugin architecture
├── storage/
│   ├── sqlite_store.py # Event and character persistence
│   └── neo4j_store.py  # Relationship graph (optional)
├── output/
│   ├── base.py         # OutputPlugin base class
│   ├── console.py      # Console output plugin
│   └── jsonlog.py      # JSON log file plugin
└── admin/
    ├── api.py          # FastAPI backend for admin UI
    └── ui/             # Vue.js frontend
rules/
└── indexed/
    └── basic/          # Pre-indexed BECMI Basic rules
        ├── monsters.json
        └── spells.json
```

## Architecture

### Core Philosophy

This is fundamentally an **information management and orchestration system** with D&D as the engagement layer. The hard problems are:

- **Context management** - LLMs forget, campaigns don't
- **State persistence** - Characters, events, world state
- **Turn orchestration** - Who speaks when, cinematic pacing
- **Multi-provider coordination** - Different models, unified game

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Game Loop (AutoGen SelectorGroupChat)                      │
│  DM speaks → Player responds → DM adjudicates → repeat      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Campaign Manager                                           │
│  • Session tracking                                         │
│  • Event recording                                          │
│  • Character management                                     │
└──────┬──────────────────────────────┬───────────────────────┘
       │                              │
       ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│  SQLite Store   │          │  Neo4j Store    │
│  (documents)    │          │  (relationships)│
│  • Events       │          │  • KILLED       │
│  • Characters   │          │  • ALLIED_WITH  │
│  • Sessions     │          │  • LOCATED_AT   │
└─────────────────┘          └─────────────────┘
```

### DM-Controlled Turn Order

The DM always regains control after any player speaks, then decides who acts next based on the narrative:

```python
def dm_selector(messages) -> str | None:
    if not messages:
        return "dm"
    if messages[-1].source != "dm":
        return "dm"  # After player, return to DM
    return None  # DM spoke, let model decide who was addressed
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional: Neo4j for relationship tracking
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

### Data Storage

- **Default location**: `~/.dndbots/`
- **Database**: `campaigns.db` (SQLite)
- **Tables**: `events`, `characters`, `sessions`

## Development

```bash
# Run tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_game.py -v
```

### Test Coverage

- 224 tests passing
- 4 tests skip (Neo4j, requires running instance)

## Roadmap

- [x] Phase 1: Minimal game loop (DM + 1 player)
- [x] Phase 2: Persistence layer (SQLite + Neo4j)
- [ ] Phase 3: Multi-provider (Claude, Gemini, DeepSeek)
- [x] Phase 4: DCML compression (token-efficient state tracking)
- [x] Phase 5: Output layer (event bus with plugin architecture)
- [x] Phase 6: Admin UI (FastAPI + Vue.js, graceful shutdown)
- [x] BECMI Rules Integration (indexed rules with tool-based lookup)

## Design Documents

- `docs/plans/2025-12-05-dndbots-architecture-design.md` - Full architecture
- `docs/plans/2025-12-05-phase1-minimal-game-loop.md` - Phase 1 implementation
- `docs/plans/2025-12-06-phase2-persistence-layer.md` - Phase 2 implementation
- `docs/plans/2025-12-06-phase4-dcml-compression.md` - Phase 4 implementation
- `docs/plans/2025-12-06-phase5-output-plugins.md` - Phase 5 implementation
- `docs/plans/2025-12-06-phase6-admin-ui-design.md` - Phase 6 design
- `docs/plans/2025-12-06-phase6-implementation-plan.md` - Phase 6 implementation
- `docs/plans/2025-12-07-becmi-rules-integration-design.md` - BECMI rules design
- `docs/plans/2025-12-07-becmi-rules-implementation-plan.md` - BECMI rules implementation
- `docs/example_compression.md` - Compression language inspiration (UCLS)

## License

MIT
