# Neo4j Integration Design

**Date:** 2025-12-10
**Status:** Approved
**Goal:** Wire up Neo4j graph database to record and query game relationships, enabling recaps, memory, and narrative continuity.

---

## Overview

Neo4j is already implemented (`Neo4jStore`) but not wired up. This design covers:
1. Recording combat and narrative relationships during play
2. Querying the graph for recaps and context
3. Integrating with DCML memory system

### Key Principle: Clean Separation

| Agent | Records | Examples |
|-------|---------|----------|
| **Referee** | Combat mechanics | kills, crits, fumbles, clutch saves |
| **DM** | Narrative facts | NPC introductions, factions, moment enrichment |

Referee owns the numbers. DM owns the story. No overlap.

---

## Recording Layer

### Hardcoded Triggers (Automatic)

These fire automatically when mechanics resolve:

```python
HARDCODED_TRIGGERS = {
    "kill":        # HP → 0
    "crit_hit":    # Natural 20
    "crit_fail":   # Natural 1
    "clutch_save": # Made save by ≤2
    "overkill":    # Damage ≥ 2× remaining HP
}
```

Each creates:
- Graph relationship (e.g., `KILLED` edge)
- `Moment` node with mechanical details
- Empty `narrative` field for DM enrichment

### Prompted Recording (Referee Judgment)

Referee prompt includes guidance to call `record_moment()` for:
- Creative/environmental actions ("shoot the lantern")
- Dramatic reversals
- "Crazy plan that just might work" moments

Accepts some noise - missing cool moments is worse than recording mediocre ones.

### DM Tools

Explicit tools for narrative relationships:
- `introduce_npc(name, description, faction?)` - Create NPC node
- `set_faction_relation(entity, faction, role)` - Link entity to faction
- `enrich_moment(moment_id, narrative)` - Add flavor to Referee's mechanical records

The `enrich_moment()` pattern keeps Referee fast ("Throk killed goblin_03") and lets DM add color later ("...by kicking it into the lava").

---

## Graph Schema

### Node Types

```
:Character    - PCs and NPCs
                (char_id, name, class, level, campaign_id)

:Location     - Places
                (location_id, name, description, campaign_id)

:Moment       - Noteworthy events
                (moment_id, session, turn, type, narrative)

:Faction      - Groups
                (faction_id, name, description)
```

### Relationship Types

**Combat:**
```
(Character)-[:KILLED {moment_id, weapon, damage, narrative}]->(Character)
(Character)-[:CRITTED {moment_id, roll, target}]->(Character)
(Character)-[:FUMBLED {moment_id, consequence}]->(Moment)
```

**Location:**
```
(Character)-[:LOCATED_AT]->(Location)              # Current position
(Character)-[:VISITED {session, first_visit}]->(Location)
(Location)-[:CONTAINS]->(Location)                 # Hierarchy
```

**Social:**
```
(Character)-[:MEMBER_OF {role}]->(Faction)
(Character)-[:ALLIED_WITH]->(Character)
(Character)-[:HOSTILE_TO]->(Character)
```

**Moments:**
```
(Character)-[:PERFORMED]->(Moment)    # Who did the cool thing
(Character)-[:WITNESSED]->(Moment)    # Who was there
(Moment)-[:OCCURRED_AT]->(Location)
```

### Key Insight

`:Moment` nodes are the "cool thing" records. Kills create both a `KILLED` edge *and* a `Moment` node, enabling two query patterns:
- "Who has Throk killed?" → follow `KILLED` edges
- "What memorable things happened at the caves?" → query `Moment` nodes by location

---

## Query & Consumption

### DM Tools (During Play)

```python
recall_kills(character_id) -> str
    # "Throk has killed: 4 goblins, Grimfang the chieftain"

recall_moments(character_id?, location_id?, limit=5) -> str
    # "At the Crystal Bridge: Throk leapt the chasm to decapitate the golem"

get_faction_members(faction_id) -> str
    # "Darkwood Goblins: Grimfang (chieftain, dead), 12 unnamed goblins"

who_visited(location_id) -> str
    # "Caves of Chaos: Throk, Zara, Elena (rescued here)"
```

### Session Start Recap (Automatic)

When `DnDGame` initializes with existing campaign:

1. Query graph for last session's moments
2. Query ongoing plot threads (factions, NPCs)
3. Render compressed summary
4. Inject into DM system prompt

Format:
```
=== PREVIOUSLY (Session 3) ===
Party explored Darkwood Caves. Key moments:
- Throk killed Grimfang (crit, decapitation)
- Rescued Elena, learned of "unknown master"
- Quest accepted: find Millbrook children

Active threads:
- Darkwood Goblins: hostile, leaderless
- Unknown Master: ?identity, receiving tribute
```

### DCML Integration

`MemoryBuilder` gains `build_from_graph()` that pulls:
- Known entities → LEXICON
- Witnessed moments → MEMORY section
- Relationship summaries → compressed facts

### Access Control

No explicit ACLs needed. The UID system is self-limiting:
- If a PC wasn't present, their DCML has no UID for that entity
- They can't query for something they don't have the key to
- The lexicon *is* the access control

---

## Integration Points

### 1. Wire Neo4j (cli.py)

```python
neo4j_config = None
if os.getenv("NEO4J_URI"):
    neo4j_config = {
        "uri": os.getenv("NEO4J_URI"),
        "username": os.getenv("NEO4J_USER"),
        "password": os.getenv("NEO4J_PASSWORD"),
    }

campaign = Campaign(..., neo4j_config=neo4j_config)
```

### 2. Referee Recording Tools (referee_tools.py)

Add to existing tools:
```python
record_kill_tool(attacker_id, target_id, weapon, damage, narrative?)
record_moment_tool(actor_id, moment_type, description)
```

Hardcoded triggers fire inside existing mechanics:
- `roll_damage_tool` checks for kill → auto-records
- `roll_attack_tool` checks for crit → auto-records
- `roll_save_tool` checks for clutch → auto-records

### 3. DM Narrative Tools (game.py)

```python
introduce_npc_tool(name, description, faction?)
set_faction_tool(entity_id, faction_id, role)
enrich_moment_tool(moment_id, narrative)
recall_kills_tool(character_id)
recall_moments_tool(character_id?, location_id?)
```

### 4. Session Start Recap (game.py)

```python
if campaign and campaign.has_previous_session():
    recap = campaign.generate_session_recap()
    self.dm_prompt += f"\n\n=== PREVIOUSLY ===\n{recap}"
```

### 5. Graph-Based Memory (memory.py)

```python
def build_from_graph(self, pc_id: str, neo4j: Neo4jStore) -> str:
    kills = neo4j.get_relationships(pc_id, "KILLED")
    moments = neo4j.get_witnessed_moments(pc_id)
    # ... render to DCML
```

---

## Implementation Phases

| Phase | Description | Estimate |
|-------|-------------|----------|
| A | Wire Neo4j config in cli.py | 30 min |
| B | Referee records kills + hardcoded triggers | 2-3 hrs |
| C | Referee prompted moments | 1 hr |
| D | DM narrative + query tools | 2 hrs |
| E | Session start recap | 2 hrs |
| F | DCML from graph | 2 hrs |

**Total: ~10 hours**

### Phase A: Wire It Up
1. Pass `neo4j_config` from env vars in `cli.py`
2. Verify characters get created in Neo4j on game start
3. Test: run game, check Neo4j has character nodes

### Phase B: Referee Records Kills
1. Add `record_kill()` method to `Neo4jStore`
2. Add `Moment` node creation
3. Hook into `MechanicsEngine` - when HP → 0, auto-record
4. Add hardcoded triggers (crit, fumble, clutch save)
5. Test: combat creates graph entries

### Phase C: Referee Prompted Moments
1. Add `record_moment_tool` to referee tools
2. Update Referee prompt with guidance
3. Test: creative action gets recorded

### Phase D: DM Tools
1. Add `introduce_npc_tool`, `set_faction_tool`, `enrich_moment_tool`
2. Add query tools: `recall_kills_tool`, `recall_moments_tool`
3. Test: DM can query and enrich

### Phase E: Session Recap
1. Add `generate_session_recap()` to Campaign
2. Inject into DM prompt on session start
3. Test: restart game, DM knows what happened

### Phase F: DCML From Graph
1. Update `MemoryBuilder.build_from_graph()`
2. Wire into player agent prompt construction
3. Test: player memory reflects graph state

---

## Open Questions (Deferred)

- Location tracking: How/when do we update `LOCATED_AT`?
- Faction discovery: Auto-create factions or DM-only?
- Graph cleanup: Prune old/irrelevant nodes?

These can be addressed as we learn from usage.
