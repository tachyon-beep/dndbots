# CLAUDE.md - Guidelines for Claude Code

This file provides context and guidelines for Claude Code when working on the DnDBots project.

## Project Overview

DnDBots is a multi-AI D&D campaign system where frontier models play Basic D&D (1983 Red Box) together. One AI is the Dungeon Master, others play characters. The system handles orchestration, persistence, and context management.

## Tech Stack

- **Python 3.11+** - Primary language
- **AutoGen 0.4+** - Multi-agent orchestration (SelectorGroupChat)
- **SQLite** (aiosqlite) - Document storage for events, characters, sessions
- **Neo4j** (optional) - Relationship graph for entity connections
- **pytest** + **pytest-asyncio** - Testing framework

## Architecture Principles

### 1. Information Management First

This is fundamentally an information management system with D&D as the engagement layer. Key challenges:
- LLMs forget, campaigns don't - persistence is critical
- Context windows are limited - compression matters
- Deterministic lookups, not RAG - D&D requires precision ("which goblin?")

### 2. DM-Controlled Turn Order

The DM always gets control back after any player speaks. Don't change the `dm_selector` pattern in `game.py` without understanding why it exists - it prevents agents from talking over each other.

### 3. Hybrid Storage

- **SQLite** for documents (events, characters, full narrative blobs)
- **Neo4j** for relationships (who killed whom, faction ties, location hierarchy)
- Everything gets a UID for deterministic lookup

### 4. Event-Sourced Design

Game state is derived from events. The `events` table is the source of truth. This enables:
- Replay and debugging
- State reconstruction
- Audit trails

## Code Patterns

### Async Throughout

All storage operations are async. Use `async/await` consistently:

```python
# Good
async def run_game():
    await campaign.initialize()
    characters = await campaign.get_characters()

# Bad - mixing sync/async
def run_game():
    asyncio.run(campaign.initialize())  # Don't do this inside async code
```

### Dataclasses for Models

Use `@dataclass` for data structures, not Pydantic (keep it simple):

```python
@dataclass
class Character:
    name: str
    char_class: str
    level: int
    # ...
```

### TDD for New Features

Follow test-driven development:
1. Write failing test first
2. Run test, verify it fails
3. Write minimal implementation
4. Run test, verify it passes
5. Commit

### UID Conventions

```
Events:     evt_{uuid12}              (e.g., evt_a1b2c3d4e5f6)
PCs:        pc_{name}_{uuid4}         (e.g., pc_throk_c471)
NPCs:       npc_{name}_{uuid4}        (e.g., npc_grimfang_001)
Locations:  loc_{name}_{detail}       (e.g., loc_caves_room_02)
Sessions:   session_{campaign}_{num}  (e.g., session_default_campaign_001)
```

## File Organization

```
src/dndbots/
├── cli.py          # Entry point - keep thin
├── game.py         # Orchestration - AutoGen setup
├── campaign.py     # Campaign manager - coordinates storage
├── models.py       # Data structures - Character, Stats
├── events.py       # Event schema - GameEvent, EventType
├── rules.py        # D&D rules - THAC0, modifiers
├── prompts.py      # System prompts - DM and player
├── dice.py         # Utilities - roll(), parse_roll()
└── storage/
    ├── sqlite_store.py  # Document persistence
    └── neo4j_store.py   # Graph persistence (optional)
```

## Testing

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_game.py -v

# Run with coverage
pytest --cov=dndbots
```

### Test Fixtures

- Use `tempfile.TemporaryDirectory()` for database tests
- Use `monkeypatch.setenv("OPENAI_API_KEY", "sk-test")` for API key mocking
- Neo4j tests auto-skip if `NEO4J_URI` not set

## Common Tasks

### Adding a New Event Type

1. Add to `EventType` enum in `events.py`
2. Handle in `game.py` if it needs special recording logic
3. Add tests

### Adding a New Storage Method

1. Add method to `SQLiteStore` (and/or `Neo4jStore`)
2. Expose through `Campaign` if needed
3. Write async tests with temp database

### Modifying Prompts

Prompts are in `prompts.py`. Key sections:
- `RULES_SHORTHAND` in `rules.py` - compressed D&D rules
- `build_dm_prompt()` - DM system message
- `build_player_prompt()` - Player system message

## Don't

- **Don't use RAG** - Use deterministic UID lookups instead
- **Don't hardcode API keys** - Use environment variables
- **Don't skip TDD** - Write tests first
- **Don't modify dm_selector without understanding it** - Turn order is intentional
- **Don't use sync database calls** - Everything is async

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Minimal game loop | ✅ Complete |
| 2 | Persistence (SQLite + Neo4j) | ✅ Complete |
| 3 | Multi-provider (Claude, Gemini, DeepSeek) | ⏸️ Deferred |
| 4 | DCML compression | ✅ Complete |
| 5 | Extensible output layer | ✅ Complete |
| 6 | Admin UI + graceful shutdown | 📋 Designed |

See `docs/plans/` for detailed implementation plans.

## Useful Commands

```bash
# Check database contents
sqlite3 ~/.dndbots/campaigns.db "SELECT * FROM events LIMIT 5;"
sqlite3 ~/.dndbots/campaigns.db "SELECT * FROM characters;"

# Reset database (for testing)
rm ~/.dndbots/campaigns.db

# Run game
dndbots
```

## Design Documents

- `docs/plans/2025-12-05-dndbots-architecture-design.md` - Full architecture
- `docs/example_compression.md` - UCLS compression language (inspiration for StoryShorthand)
