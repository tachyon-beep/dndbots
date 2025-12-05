# DnDBots

Multi-AI D&D campaign system where different frontier models (Claude, GPT, Gemini, DeepSeek) play Basic D&D (1983 Red Box) together. One AI serves as Dungeon Master, others play characters.

## Features

- **Multi-AI Orchestration**: AutoGen 0.4 SelectorGroupChat with DM-controlled turn order
- **Basic D&D Rules**: THAC0 combat, ability modifiers, saving throws from the 1983 Red Box
- **Persistent Campaigns**: SQLite for events/characters, Neo4j for relationships (optional)
- **Transparent Mechanics**: All dice rolls visible with full breakdown
- **Stream-Ready Output**: Designed for Discord integration and live viewing

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
├── cli.py          # Command-line entry point
├── game.py         # AutoGen orchestration (DnDGame, SelectorGroupChat)
├── campaign.py     # Campaign manager (coordinates storage)
├── models.py       # Character, Stats dataclasses
├── events.py       # GameEvent schema for persistence
├── rules.py        # Basic D&D rules (THAC0, modifiers)
├── prompts.py      # DM and player system prompts
├── dice.py         # Dice rolling utilities
└── storage/
    ├── sqlite_store.py  # Event and character persistence
    └── neo4j_store.py   # Relationship graph (optional)
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

- 55 tests passing
- 4 tests skip (Neo4j, requires running instance)

## Roadmap

- [x] Phase 1: Minimal game loop (DM + 1 player)
- [x] Phase 2: Persistence layer (SQLite + Neo4j)
- [ ] Phase 3: Multi-provider (Claude, Gemini, DeepSeek)
- [ ] Phase 4: Compression (StoryShorthand for token efficiency)
- [ ] Phase 5: Output layer (Discord, event bus)
- [ ] Phase 6: Admin UI (web interface, graceful shutdown)

## Design Documents

- `docs/plans/2025-12-05-dndbots-architecture-design.md` - Full architecture
- `docs/plans/2025-12-05-phase1-minimal-game-loop.md` - Phase 1 implementation
- `docs/plans/2025-12-06-phase2-persistence-layer.md` - Phase 2 implementation
- `docs/example_compression.md` - Compression language inspiration (UCLS)

## License

MIT
