# DnDBots Architecture Design

**Date:** 2025-12-05
**Status:** Draft
**Author:** Brainstorming session

## Overview

A multi-AI D&D campaign system where different frontier models (Claude, GPT, Gemini, DeepSeek) play Basic D&D (1983 red box) together. One AI serves as Dungeon Master, others play characters. The system runs continuously (24/7 capable) with campaigns persisting across sessions.

### Core Philosophy

This is fundamentally an **information management and orchestration system** with D&D as the engagement layer. The hard problems are:

- **Context management** - LLMs forget, campaigns don't
- **State persistence** - Characters, events, world state
- **Turn orchestration** - Who speaks when, cinematic pacing
- **Multi-provider coordination** - Different models, unified game

### Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python | Rich ecosystem, all API clients available |
| Orchestration | AutoGen 0.4 | SelectorGroupChat fits DM-controlled flow |
| Graph DB | Neo4j | Relationships (who killed whom, faction ties) |
| Document Store | SQLite/Postgres JSONB | Narrative blobs, full event details |
| Output | Discord + JSON logs | Stream-ready, shareable, persistent |
| Admin | Web UI (FastAPI) | Campaign control, monitoring |

### Key Design Insight

Inspired by [pyshorthand](https://github.com/tachyon-beep/pyshorthand): compress state into token-efficient notation in context, with deterministic lookups to deep storage when full details are needed. **No RAG** - D&D requires precision ("which goblin?"), not semantic similarity.

---

## Data Layer

### Hybrid Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Graph DB (Neo4j)                                               │
│  ─────────────────────────────────────────────────────────────  │
│  Relationships & entities:                                      │
│  • (PC:Throk)-[:KILLED]->(NPC:Grimfang)                        │
│  • (NPC:Grimfang)-[:CHIEFTAIN_OF]->(Faction:Darkwood_Goblins)  │
│  • (Location:Cave)-[:CONTAINS]->(Item:Cursed_Axe)              │
│  • (Event:42)-[:INVOLVED]->(PC:Throk, PC:Zara)                 │
│  • (Event:42)-[:OCCURRED_AT]->(Location:Cave)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Document Store (SQLite/Postgres JSONB)                         │
│  ─────────────────────────────────────────────────────────────  │
│  Full narrative blobs:                                          │
│  • event:42 → { full_narrative, mechanical_outcome, session }   │
│  • npc:grimfang → { description, dialogue_style, secrets }      │
│  • location:cave → { full_description, hidden_features }        │
└─────────────────────────────────────────────────────────────────┘
```

### Universal ID Schema

Everything gets a UID - no ambiguity, deterministic lookups:

```
Events:     evt_003_047           (session 3, turn 47)
PCs:        pc_throk_001
NPCs:       npc_grimfang_001      (named)
            npc_goblin_enc12_03   (generic: encounter 12, goblin #3)
Items:      item_cursed_axe_001   (unique)
            item_torch_enc12_02   (generic loot)
Locations:  loc_darkwood_cave_main
            loc_darkwood_cave_room_02
Beats:      beat_003_goblin_ambush
Factions:   fac_darkwood_goblins
```

DM assigns UIDs as entities enter play. All references use UIDs for precision.

---

## Memory & Compression

### Two Compression Languages

#### StoryShorthand (narrative compression)

Compress campaign events into token-efficient notation with UID references and causality:

```
SESSION_003 SUMMARY:
[beat_003_goblin_ambush] Party ambushed @loc_darkwood_entrance
  → Combat: 4 rounds, pc_throk injured (12dmg), npc_goblin_enc12_01-04 killed
  → Loot: 23gp, item_rusty_shortsword_003
[beat_003_prisoner_found] Discovered npc_prisoner_elena @loc_darkwood_cave_room_02
  → Info: Goblins serve npc_grimfang, tribute to unknown master
  → Quest hook: rescue village children
[beat_003_chieftain_confrontation] Entered throne room, npc_grimfang hostile
  → Status: combat_initiated, pending resolution
```

Compression preserves **causality and consequences**:

```
[evt_002_031] enc:bandit_ambush @loc_forest_road
  → death:npc_jim_villager_01 (pc_throk failed_to_protect)
  → consequence: rep_loss:village_millbrook, guilt:pc_throk
```

Agents can expand any UID to get full narrative context when needed.

#### RulesShorthand (mechanics compression)

Compress Basic D&D rules for system prompts:

```
COMBAT: d20+mods≥AC=hit | init:d6/side | morale:2d6≥ML=flee
SAVES: d20≥target [P:poison D:dragon B:breath S:spell W:wand]
DAMAGE: weapon_die+STR_mod | ≤0HP=dead | rest:1d3HP/day
MAGIC: slots/day by level | prep@dawn | lost@cast
THIEF: %skills [CW:87 TR:25 PP:35 MS:40 HS:25 HN:1-2]
```

### Context Window Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Always in context (compressed):                                │
│  • Character sheets (structured)                                │
│  • Recent events shorthand (last N turns)                       │
│  • Current scene state                                          │
│  • Core rules shorthand                                         │
├─────────────────────────────────────────────────────────────────┤
│  On-demand (tool calls to deep storage):                        │
│  • Full event narratives                                        │
│  • Detailed NPC info                                            │
│  • Edge-case rules                                              │
│  • Historical events beyond recent window                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture

### Configuration vs Game State Separation

**Config (infrastructure)** - who's at the table:

```yaml
campaign_id: "tomb_001"

seats:
  - seat_id: seat_dm
    role: dm
    provider: anthropic
    model: claude-opus-4
    api_key_env: ANTHROPIC_API_KEY

  - seat_id: seat_player_01
    role: player
    provider: openai
    model: gpt-4o
    api_key_env: OPENAI_API_KEY
    character_id: null  # AI creates on first run

  - seat_id: seat_player_02
    role: player
    provider: google
    model: gemini-2.0-flash
    api_key_env: GOOGLE_API_KEY
    character_id: null
```

**Game state (in DB)** - who they're playing:

```yaml
characters:
  pc_throk_001:
    name: "Throk"
    class: fighter
    level: 3
    hp: 24/24
    stats: {str: 17, dex: 12, con: 15, int: 8, wis: 10, cha: 9}
    inventory: [item_longsword_001, item_chain_armor_001]
```

Level up? Update DB, not config. Swap models? Edit config, character persists.

### AI Character Creation

New player seats without a `character_id` trigger character creation:

```
System: "You are joining a Basic D&D campaign. Create your character.
        Choose: name, class (Fighter/Cleric/Thief/Wizard), roll stats
        (4d6 drop lowest), write a brief backstory."

GPT-4o: "I am Throk, a human Fighter from the northern wastes..."

System: [validates against Basic D&D rules]
System: [DM reviews and approves]
System: [persists to DB, updates config with character_id]
```

### Agent Context by Role

**DM Agent:**
- Full rules shorthand
- Complete scenario/adventure
- All monster stats for active creatures
- Full compressed story history
- Tools: `assign_uid`, `lookup_rule`, `expand_event`, `roll_dice`

**Player Agents:**
- Player-facing rules only
- Own character sheet
- Only witnessed events (compressed)
- Tools: `expand_event`, `check_inventory`, `request_action`

---

## Orchestration & Turn Control

### DM-Controlled Flow

Using AutoGen 0.4's SelectorGroupChat with custom selector:

```python
def dm_selector(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """DM always gets control back, then decides who acts next."""
    last_speaker = messages[-1].source

    # After any player speaks, return to DM
    if last_speaker != "dm":
        return "dm"

    # DM's message contains directive for next speaker
    next_player = parse_next_directive(messages[-1].content)
    if next_player:
        return next_player

    return None  # Fallback to LLM selector
```

### Engagement Tracking

DM's context includes soft engagement metrics:

```
ENGAGEMENT_TRACKER:
  pc_throk: last_action=2_turns, spotlight_streak=0
  pc_zara:  last_action=0_turns, spotlight_streak=3  ⚠️
  pc_pip:   last_action=5_turns, spotlight_streak=0  🔴

HEURISTIC: Pip hasn't acted in 5 turns. Find natural moment to involve them.
```

Not a mandate - DM uses this for awareness, waits for moments where skills matter.

### Party Play Principles

Player agent prompts include:

```
PARTY PLAY PRINCIPLES:
• "I defer to [player]" or "I watch and wait" are VALID actions
• Only act if you have something valuable to add
• If another character is better suited, LET THEM SHINE
• Stepping back IS good roleplay
• Inter-party conflict (theft, secrets) is valid if in-character

EXAMPLES:
  ✓ "Throk stands guard while Zara picks the lock."
  ✓ "I stay quiet - Pip knows more about magic."
  ✓ Zara quietly rifles through Throk's pack while he sleeps
  ✗ "I ALSO try to pick the lock!" (why? you're a fighter)
```

DM prompt includes:

```
PACING PRINCIPLES:
• Not every turn needs all players - cinematic beats matter
• When a character is "in their element", let them run with it
• Prompt quiet players at NATURAL openings, not arbitrarily
```

---

## Output Layer

### Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Game Loop (AutoGen)                                            │
│  → Every agent message, roll, state change = GameEvent          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Event Bus                                                      │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌──────────────┐   ┌────────────────────────────┐
│ Discord Bot │   │ JSON Logger  │   │ Future Handlers            │
│ (real-time) │   │ (files)      │   │ • Webhooks                 │
└─────────────┘   └──────────────┘   │ • OBS overlay              │
                                     │ • SFX triggers             │
                                     └────────────────────────────┘
```

### Event Structure

```python
@dataclass
class GameEvent:
    type: str           # "dm_narration", "player_action", "dice_roll"
    source: str         # "dm", "pc_throk", "system"
    content: str        # The actual text
    timestamp: datetime
    metadata: dict      # Extensible for future SFX, emotions, etc.
```

### Transparent Dice Rolls

All mechanical resolution visible to audience:

```
┌─────────────────────────────────────────┐
│ 🎲 ATTACK ROLL - Throk vs Grimfang      │
│    d20 → [14] + 3 (STR) + 1 (magic) = 18│
│    Target AC: 6                         │
│    Result: ✅ HIT                        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🗡️ DAMAGE ROLL                          │
│    d8 → [6] + 2 (STR) = 8 damage        │
│    Grimfang HP: 12 → 4                  │
└─────────────────────────────────────────┘
```

Raw rolls visible, modifiers broken down, pass/fail clear. Builds audience trust and tension.

---

## Admin & Control

### Web UI Capabilities

- Start/stop/pause campaigns
- View live state (character HP, inventory, location)
- Inject hints to DM (for stuck situations)
- Force checkpoints
- Swap agent models without losing character state
- View token usage and costs
- Set graceful shutdown flag

### Graceful Shutdown Sequence

```
1. SIGNAL RECEIVED
   └─ Set pending_shutdown flag
   └─ Stop accepting new turns after current resolves

2. NARRATIVE WRAP-UP
   └─ DM guided to find natural pause point
   └─ Complete current combat/conversation
   └─ No new encounters initiated

3. TECHNICAL FLUSH
   └─ Complete all pending DB transactions
   └─ Flush event log buffers to disk
   └─ Write final checkpoint with full state
   └─ Verify graph DB consistency
   └─ Verify document store integrity

4. CLEAN EXIT
   └─ Close API connections gracefully
   └─ Post "campaign paused" to Discord
   └─ Write shutdown report
   └─ Exit with status 0
```

No dangling writes, no half-committed state. Campaign resumes cleanly.

---

## Session Structure

- **Continuous operation** with natural pause points for checkpoints
- **Graceful shutdown** via admin flag - system finds narrative pause, then cleanly exits
- **Hard kill** (Ctrl+C x2) for debugging only - may require checkpoint recovery

---

## Open Questions / Future Work

1. **Compression language design** - Formal spec for StoryShorthand and RulesShorthand
2. **Character creation validation** - How strictly to enforce Basic D&D rules
3. **Inter-party conflict limits** - Any guardrails on PvP/betrayal?
4. **Cost management** - Token budgets, model fallbacks for high-volume turns
5. **Recovery from corruption** - Checkpoint replay and state reconstruction
6. **Streaming integration** - OBS overlays, sound effects via tool calls

---

## Next Steps

1. Set up project structure and dependencies
2. Implement core data layer (Neo4j + SQLite schemas)
3. Build AutoGen 0.4 orchestration skeleton
4. Create basic DM and player agent prompts
5. Implement Discord output handler
6. Build minimal admin web UI
7. Run first test campaign