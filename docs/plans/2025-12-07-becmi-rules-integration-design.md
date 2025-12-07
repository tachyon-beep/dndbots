# BECMI Rules Integration Design

**Date:** 2025-12-07
**Status:** Design Complete
**Phase:** 7 (Rules Integration)

## Overview

Integrate the BECMI Basic D&D rules (~950KB from Red Box PDFs) into the DnDBots system, giving the DM and players access to authoritative rules via structured tool calls while keeping context usage efficient.

### Goals

1. **Rules Accuracy** - Agents make decisions based on actual BECMI rules, not LLM training data approximations
2. **Authentic Flavor** - Capture the tone and style of the 1983 Red Box
3. **Token Efficiency** - ~300 line in-context summary, details fetched on demand
4. **Future Expansion** - Design supports Expert, Companion, Master, Immortals rulesets

### Non-Goals

- RAG-based retrieval (too fuzzy for D&D's deterministic needs)
- Real-time rules parsing (pre-index once, use many times)
- Modifying the original rules text

## Architecture

### Three-Level Hierarchy

```
Level 1: Category Summary (in-context)
├── One-line overview of each entry
├── Path for tool lookup
└── ~300 lines total

Level 2: Stats/Summary (tool call)
├── Stat block + 2-3 line summary
├── Metadata (tags, related entries)
└── Fast lookup

Level 3: Full Entry (tool call)
├── Complete rules text
├── All flavor text
└── Original source line references
```

### Access Pattern: Structured Tool Calls

```python
# Deterministic path lookup (preferred)
get_rules(path="monsters/goblin", detail="full")

# Category listing
list_rules(category="spells/cleric/1", ruleset="basic")

# Keyword search (when path unknown)
search_rules(query="undead drain levels", category="monsters")
```

## Data Model

### RulesEntry Schema

```python
@dataclass
class RulesEntry:
    """A single rules entry (monster, spell, treasure type, procedure)."""

    # Identity
    path: str                      # "monsters/goblin", "spells/cleric/1/cure_light_wounds"
    name: str                      # "Goblin", "Cure Light Wounds"
    category: str                  # "monster", "spell", "treasure", "procedure", "equipment"

    # BECMI set tracking
    ruleset: str                   # "basic", "expert", "companion", "master", "immortals"
    min_level: int | None          # Minimum character level relevance
    max_level: int | None          # Maximum character level relevance

    # Source tracking
    source_file: str               # "becmi_dm_rulebook.txt"
    source_lines: tuple[int, int]  # (2456, 2489) for verification

    # Searchability
    tags: list[str]                # ["humanoid", "tribal", "low-level", "chaotic"]
    related: list[str]             # ["monsters/hobgoblin", "monsters/bugbear"]

    # Content tiers
    summary: str                   # 1-2 line overview (always available)
    stat_block: str | None         # Compressed stats (level 2)
    full_text: str                 # Complete text (level 3)
```

### Monster Metadata Extension

```python
@dataclass
class MonsterEntry(RulesEntry):
    """Extended metadata for monster entries."""

    ac: int                        # Armor Class
    hd: str                        # Hit Dice ("1-1", "3+1", "6**")
    move: str                      # Movement ("90' (30')")
    attacks: str                   # Attack routine ("1 weapon", "2 claws/1 bite")
    damage: str                    # Damage ("By weapon", "1d6/1d6/2d6")
    no_appearing: str              # Number appearing ("2-8 (6-60)")
    save_as: str                   # Save as ("F3", "Normal Man")
    morale: int                    # Morale score
    treasure_type: str             # Treasure ("C", "(R) C")
    alignment: str                 # Alignment
    xp: int                        # XP value
    special_abilities: list[str]   # ["infravision 90'", "hates dwarves"]
```

### Spell Metadata Extension

```python
@dataclass
class SpellEntry(RulesEntry):
    """Extended metadata for spell entries."""

    spell_class: str               # "cleric", "magic-user", "elf"
    spell_level: int               # 1-5 for Basic
    range: str                     # "Touch", "120'", "0 (caster only)"
    duration: str                  # "Permanent", "2 turns", "1 round/level"
    reversible: bool               # Can be reversed
    reverse_name: str | None       # "Cause Light Wounds"
    components: str | None         # If tracked (Basic doesn't use V/S/M)
```

## Tool API

### get_rules()

```python
def get_rules(
    path: str,
    detail: Literal["summary", "stats", "full"] = "summary"
) -> RulesResult:
    """
    Fetch rules content by exact path.

    Args:
        path: Hierarchical path like "monsters/goblin" or "spells/cleric/1/cure_light_wounds"
        detail: Content level - "summary" (1-2 lines), "stats" (stat block), "full" (everything)

    Returns:
        RulesResult with content and metadata

    Examples:
        get_rules("monsters/goblin", detail="full")
        get_rules("spells/magic-user/1/sleep", detail="stats")
        get_rules("treasure/type_c")
    """
```

### list_rules()

```python
def list_rules(
    category: str,
    ruleset: str = "basic",
    min_level: int | None = None,
    max_level: int | None = None,
    tags: list[str] | None = None
) -> list[RulesIndex]:
    """
    List available entries in a category with filtering.

    Args:
        category: Category path like "monsters", "spells/cleric/1", "treasure"
        ruleset: BECMI set filter ("basic", "expert", etc.)
        min_level: Filter by minimum level appropriateness
        max_level: Filter by maximum level appropriateness
        tags: Filter by tags (AND logic)

    Returns:
        List of RulesIndex with path, name, summary, tags

    Examples:
        list_rules("monsters", tags=["undead"])
        list_rules("spells/cleric/1", ruleset="basic")
        list_rules("treasure", max_level=3)
    """
```

### search_rules()

```python
def search_rules(
    query: str,
    category: str | None = None,
    ruleset: str | None = None,
    limit: int = 5
) -> list[RulesMatch]:
    """
    Search rules by keywords when exact path unknown.

    Args:
        query: Natural language search query
        category: Optional category filter
        ruleset: Optional BECMI set filter
        limit: Maximum results to return

    Returns:
        List of RulesMatch with path, relevance score, matching snippet

    Examples:
        search_rules("creatures that turn to stone")
        search_rules("healing spells", category="spells")
        search_rules("paralysis", category="monsters")
    """
```

### Return Types

```python
@dataclass
class RulesResult:
    """Result from get_rules()."""
    path: str
    name: str
    category: str
    ruleset: str
    content: str              # Formatted based on detail level
    metadata: dict            # All entry fields as dict
    related: list[str]        # Suggested related paths
    source_reference: str     # "becmi_dm_rulebook.txt:2456-2489"

@dataclass
class RulesIndex:
    """Entry in list_rules() results."""
    path: str
    name: str
    summary: str
    tags: list[str]
    stat_preview: str | None  # One-line stat summary if applicable

@dataclass
class RulesMatch:
    """Search result from search_rules()."""
    path: str
    name: str
    category: str
    relevance: float          # 0.0-1.0 match score
    snippet: str              # Matching excerpt with highlights
```

## In-Context Summary (~300 lines)

The DM's system prompt includes a compressed rules reference:

```
BECMI BASIC RULES REFERENCE
===========================

## CORE MECHANICS (40 lines)

### Combat Sequence
1. Morale check (if applicable)
2. Movement
3. Missile fire (by DEX order)
4. Magic (spells go off)
5. Melee (simultaneous)

### THAC0 by Class/Level
       1-3   4-6   7-9  10-12
F/Elf   19    17    15    13
C/Thf   19    19    17    17
M-U     19    19    19    17
Dwf     19    17    17    15
Hflg    19    19    17    17

### Saving Throws (Fighter Progression)
       1-3   4-6   7-9
D/P     12    10     8
Wands   13    11     9
Para    14    12    10
Breath  15    13    11
Spells  16    14    12

### Morale
2 = Never flees | 12 = Never checks
Check when: first death, half dead
2d6 > morale = flee

### Reaction Rolls (2d6)
2-3: Hostile | 4-6: Unfriendly | 7-9: Neutral | 10-11: Friendly | 12: Helpful

## MONSTER QUICK REFERENCE (100 lines)

Format: Name: AC HD Mv Atk Dm ML XP [Special] → path

Basilisk: AC4 HD6+1 Mv60' 1bite+gaze 1d10+petrify ML9 XP950 → monsters/basilisk
Bear,Black: AC6 HD4 Mv120' 2claw/1bite 1d3/1d3/1d6 ML7 XP125 → monsters/bear_black
...
[All ~70 Basic monsters, one line each]

## SPELL QUICK REFERENCE (60 lines)

### Cleric Spells
C1 Cure Light Wounds: Touch, heal 1d6+1 hp [Rev: Cause] → spells/cleric/1/cure_light_wounds
C1 Detect Evil: 120', 6 turns duration → spells/cleric/1/detect_evil
C1 Detect Magic: 60', 2 turns duration → spells/cleric/1/detect_magic
C1 Light: 120' range, 15' radius, 12 turns [Rev: Darkness] → spells/cleric/1/light
C1 Protection from Evil: Touch, 12 turns, -1 to hit/+1 saves → spells/cleric/1/protection_from_evil
C1 Purify Food & Water: 10' range, makes safe → spells/cleric/1/purify_food_water
C1 Remove Fear: Touch, +2 save [Rev: Cause Fear] → spells/cleric/1/remove_fear
C1 Resist Cold: Touch, 6 turns, ignore normal cold → spells/cleric/1/resist_cold
...
[All Basic spells by class and level]

### Magic-User Spells
MU1 Charm Person: 120', humanoids, save neg → spells/magic_user/1/charm_person
MU1 Detect Magic: 60', 2 turns → spells/magic_user/1/detect_magic
MU1 Floating Disc: 6', 6 turns, 5000cn → spells/magic_user/1/floating_disc
MU1 Hold Portal: 10', 2d6 turns → spells/magic_user/1/hold_portal
MU1 Light: 120', 6 turns+level [Rev: Darkness] → spells/magic_user/1/light
MU1 Magic Missile: 150', auto-hit, 2d6+1 → spells/magic_user/1/magic_missile
MU1 Protection from Evil: Self, 6 turns → spells/magic_user/1/protection_from_evil
MU1 Read Languages: Self, 2 turns → spells/magic_user/1/read_languages
MU1 Read Magic: Self, 1 turn → spells/magic_user/1/read_magic
MU1 Shield: Self, 2 turns, AC2 vs missiles → spells/magic_user/1/shield
MU1 Sleep: 240', 2d8 HD affected → spells/magic_user/1/sleep
MU1 Ventriloquism: 60', 2 turns → spells/magic_user/1/ventriloquism
...

## TREASURE TYPES (30 lines)

Type A: 25%×1d6×1000cp, 30%×1d6×1000sp, 20%×2d6×1000ep, 35%×6d6×1000gp, 25%×1d2×1000pp, 50%×6d6gems, 50%×6d6jewelry, 30%×any3
Type B: 50%×1d8×1000cp, 25%×1d6×1000sp, 25%×1d4×1000ep, 25%×1d3×1000gp, 25%×1d6gems, 25%×1d6jewelry, 10%×sword/armor/weapon
...
[All treasure types with probabilities]

## DUNGEON PROCEDURES (40 lines)

### Wandering Monsters
Check every 2 turns: 1 on d6 = encounter
Dungeon level affects monster HD

### Detection
Secret doors: 1 on d6 (elves: 2 on d6)
Traps: 1-2 on d6 (dwarves find stone traps)
Listen at door: 1 on d6 (thieves/halflings: 2 on d6)
Open stuck door: STR or less on d6

### Light Sources
Torch: 30' radius, 6 turns (1 hour)
Lantern: 30' radius, 24 turns (4 hours)
Light spell: 15' radius, 12 turns (2 hours)
Infravision: 60', heat-based, ruined by light

### Rest & Healing
Natural: 1d3 HP per full day rest
Magical: immediate

### Encumbrance (cn)
Unarmored: 400cn max, full speed
Light load: 400-800cn, 3/4 speed
Heavy load: 800-1200cn, 1/2 speed
Maximum: 1600cn (very slow)

## TOOL USAGE (30 lines)

### Available Tools

get_rules(path, detail="summary|stats|full")
  - Fetch exact entry by path
  - path format: "category/name" or "category/subcategory/name"
  - Example: get_rules("monsters/goblin", detail="full")

list_rules(category, ruleset="basic", min_level=None, max_level=None, tags=None)
  - List entries in category with filters
  - Example: list_rules("spells/cleric/1")
  - Example: list_rules("monsters", tags=["undead"])

search_rules(query, category=None, limit=5)
  - Keyword search when path unknown
  - Example: search_rules("paralysis attack", category="monsters")

### Path Examples
monsters/goblin
monsters/dragon_red
spells/cleric/1/cure_light_wounds
spells/magic_user/2/invisibility
treasure/type_c
procedures/wandering_monsters
equipment/weapons/sword
```

## Storage Format

### Directory Structure

```
rules/
├── becmi_dm_rulebook.txt          # Original source (preserved)
├── becmi_players_manual.txt       # Original source (preserved)
└── indexed/
    ├── manifest.json              # Master index of all content
    ├── basic/
    │   ├── monsters.json          # All Basic monsters
    │   ├── spells_cleric.json     # Cleric spells by level
    │   ├── spells_magic_user.json # M-U spells by level
    │   ├── treasure.json          # Treasure types
    │   ├── procedures.json        # DM procedures
    │   └── equipment.json         # Weapons, armor, gear
    └── (future: expert/, companion/, master/, immortals/)
```

### manifest.json

```json
{
  "version": "1.0.0",
  "generated": "2025-12-07T12:00:00Z",
  "rulesets": {
    "basic": {
      "sources": [
        "becmi_dm_rulebook.txt",
        "becmi_players_manual.txt"
      ],
      "categories": {
        "monsters": {
          "file": "basic/monsters.json",
          "count": 72,
          "paths": ["monsters/ant_giant", "monsters/ape_white", ...]
        },
        "spells/cleric": {
          "file": "basic/spells_cleric.json",
          "count": 24,
          "paths": ["spells/cleric/1/cure_light_wounds", ...]
        }
      }
    }
  }
}
```

### monsters.json Example

```json
{
  "goblin": {
    "path": "monsters/goblin",
    "name": "Goblin",
    "category": "monster",
    "ruleset": "basic",
    "min_level": 1,
    "max_level": 3,
    "source_file": "becmi_dm_rulebook.txt",
    "source_lines": [2456, 2489],
    "tags": ["humanoid", "tribal", "chaotic", "low-level"],
    "related": ["monsters/hobgoblin", "monsters/bugbear", "monsters/kobold"],
    "summary": "Small chaotic humanoids, -1 to hit in daylight, hate dwarves",
    "stat_block": "AC6 HD1-1 Mv90'(30') Atk1wpn Dm(wpn) NA2-8(6-60) SvNM ML7(9) TT(R)C AL:C XP5",
    "ac": 6,
    "hd": "1-1",
    "move": "90' (30')",
    "attacks": "1 weapon",
    "damage": "By weapon",
    "no_appearing": "2-8 (6-60)",
    "save_as": "Normal Man",
    "morale": 7,
    "treasure_type": "(R) C",
    "alignment": "Chaotic",
    "xp": 5,
    "special_abilities": ["infravision 90'", "-1 to hit in daylight", "hate dwarves"],
    "full_text": "Goblins are small, evil humanoids that..."
  }
}
```

## Implementation Components

### New Files

```
src/dndbots/
├── rules_index.py      # RulesIndex class - loads and queries indexed rules
├── rules_tools.py      # Tool functions for agent use
└── rules_prompts.py    # In-context summary generation
```

### Integration Points

1. **DM Prompt** (`prompts.py`)
   - Replace RULES_SHORTHAND with expanded summary from `rules_prompts.py`
   - Add tool descriptions

2. **Agent Tools** (`game.py`)
   - Register rules tools with AutoGen agents
   - Handle tool calls during game loop

3. **Campaign** (`campaign.py`)
   - Load rules index on initialization
   - Optional: track which rules were referenced per session

## Pre-processing Workflow

### One-Time Extraction

```python
# scripts/index_rules.py
async def extract_rules():
    """
    Extract structured rules from source files.
    Uses LLM to parse format, then human review.
    """
    # 1. Parse monster stat blocks (regex + LLM for special abilities)
    # 2. Parse spell entries (structured format)
    # 3. Parse treasure tables (regex)
    # 4. Parse procedures (LLM extraction)
    # 5. Generate manifest.json
    # 6. Output for human review
```

### Review Process

1. Run extraction script
2. Review generated JSON for accuracy
3. Spot-check against source PDFs
4. Commit indexed files to repo

## Testing Strategy

### Unit Tests

- `test_rules_index.py` - Loading and querying indexed content
- `test_rules_tools.py` - Tool function behavior
- `test_rules_prompts.py` - Summary generation

### Integration Tests

- Agent can call rules tools during game
- Tool results formatted correctly for context
- Fallback behavior when entry not found

### Validation Tests

- Monster stat blocks match source
- Spell descriptions complete
- All paths resolve correctly

## Future Expansion

### Expert Set Integration

```python
# When adding Expert:
# 1. Add source: rules/becmi_expert_rulebook.txt
# 2. Create indexed/expert/*.json
# 3. Update manifest.json
# 4. Expand in-context summary for level 4-14 content
```

### Additional Metadata

Consider for future:
- `prerequisite_spells` - For higher level spells
- `habitat` - Where monsters are found
- `behavior_notes` - How monsters typically act
- `dm_tips` - Suggestions from the DM guide

## Success Criteria

1. **Accuracy**: Tool lookups return correct BECMI rules
2. **Completeness**: All Basic monsters, spells, treasure types indexed
3. **Performance**: Tool calls return in <100ms
4. **Usability**: DM naturally uses tools during play
5. **Maintainability**: Easy to add Expert/Companion/Master/Immortals
