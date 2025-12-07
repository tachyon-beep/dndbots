# BECMI Content Extraction Plan

## Overview

This document outlines the complete extraction of BECMI Basic Set rules from raw OCR text files into structured JSON for the `RulesIndex` system.

## Source Material Inventory

### DM Rulebook (`becmi_dm_rulebook.txt`)
**4,109 lines, ~485KB**

| Section | Lines (approx) | Content Type | Extraction Complexity |
|---------|---------------|--------------|----------------------|
| Introduction & Terms | 1-200 | Reference | Low - prose, definitions |
| Procedures | 200-600 | Reference | Medium - mixed prose/tables |
| Special Attacks | 600-700 | Reference | Low - definitions |
| Monster Descriptions Format | 700-800 | Reference | Low - stat block key |
| **Monster List A-Z** | 800-3100 | Structured | **High** - ~60 entries with stat blocks |
| Treasure Tables | 3100-3300 | Structured | Medium - tables |
| **Magic Items** | 3300-3700 | Structured | **High** - ~50+ items with descriptions |
| Creating Dungeons | 3700-4000 | Reference | Low - guidance prose |
| Reference Charts | 4000-4109 | Structured | Medium - tables |

### Players Manual (`becmi_players_manual.txt`)
**4,520 lines, ~466KB**

| Section | Lines (approx) | Content Type | Extraction Complexity |
|---------|---------------|--------------|----------------------|
| Solo Adventure | 1-800 | Narrative | Skip - not rules |
| Character Creation | 800-1500 | Reference | Medium - tables + prose |
| Equipment Lists | 1500-1700 | Structured | Medium - price tables |
| Combat Rules | 1700-2000 | Reference | Medium - procedures |
| **Class Descriptions** | 2000-3200 | Structured | Medium - 7 classes |
| **Spell Descriptions** | 3200-4200 | Structured | **High** - ~35 spells |
| Reference Charts | 4200-4520 | Structured | Medium - tables |

## Content Categories for Extraction

### 1. MONSTERS (Priority: Critical)
**Source**: DM Rulebook lines ~800-3100
**Count**: ~60 creatures
**Structure**: Highly consistent stat block format

```
Name
Armor Class: X
Hit Dice: X
Move: X' (X')
Attacks: X
Damage: X
No. Appearing: X (X)
Save As: X
Morale: X
Treasure Type: X
Alignment: X
XP value: X

[Description paragraph(s)]
```

**Extraction approach**: Pattern matching on stat block keywords + description capture

**Challenges**:
- Some monsters presented in comparison tables (Bear types, Bat types)
- OCR artifacts in some entries
- Variable description lengths

### 2. SPELLS (Priority: Critical)
**Source**: Players Manual lines ~3200-4200
**Count**: ~35 spells (12 first-level MU, 12 second-level MU, ~8 Cleric, etc.)
**Structure**: Consistent format

```
Spell Name

Range: X
Duration: X
Effect: X

[Description paragraph(s)]
```

**Extraction approach**: Pattern matching on Range/Duration/Effect headers

**Challenges**:
- Some spells have examples embedded in description
- Reversible spells need special handling
- Class restrictions need inference from section headers

### 3. MAGIC ITEMS (Priority: High)
**Source**: DM Rulebook lines ~3300-3700
**Count**: ~50+ items
**Structure**: Mixed - some in tables, some with descriptions

**Categories**:
- Swords (with bonuses and special abilities)
- Other Weapons
- Armor & Shields
- Potions
- Scrolls
- Rings
- Wands/Staves/Rods
- Miscellaneous

**Extraction approach**:
- Parse roll tables for item names
- Match item names to descriptions below tables

**Challenges**:
- Descriptions not adjacent to tables
- Cursed item rules interspersed
- Variable detail levels

### 4. PROCEDURES (Priority: Medium)
**Source**: DM Rulebook lines ~200-600
**Topics**:
- Alignment Changes
- Charm Person effects
- Doors (opening, stuck, secret)
- Evasion & Pursuit
- Languages
- Morale
- Retainers
- Turning Undead

**Structure**: Prose with occasional tables

**Extraction approach**: Section-by-section manual review with LLM summarization

### 5. CHARACTER CLASSES (Priority: Medium)
**Source**: Players Manual lines ~2000-3200
**Count**: 7 classes (Fighter, Cleric, Magic-User, Thief, Dwarf, Elf, Halfling)
**Structure**: Consistent per-class format

**Content per class**:
- Prime Requisite
- Hit Dice
- Armor/Weapons allowed
- Special abilities
- Saving throw table
- Experience table

**Extraction approach**: Pattern match on class name headers

### 6. EQUIPMENT & TREASURE (Priority: Low)
**Source**:
- Players Manual: Equipment lists
- DM Rulebook: Treasure types, gem/jewelry values

**Structure**: Primarily tables

**Extraction approach**: Table parsing

### 7. REFERENCE CHARTS (Priority: Low)
**Source**: Both books' back matter
**Content**:
- Saving Throw charts
- Hit Roll charts (THAC0)
- Encounter tables
- Wandering monster tables

**Extraction approach**: Direct table capture

## Extraction Methodology

### Phase 1: LLM-Assisted Extraction
Use Claude subagents to:
1. Read raw text sections
2. Identify entry boundaries
3. Extract structured data
4. Generate JSON in target schema

**Prompt template for monsters**:
```
Extract all monster entries from this text section.
For each monster, output JSON matching this schema:
{
  "name": "Monster Name",
  "path": "monsters/monster-name",
  "category": "monster",
  "ruleset": "basic",
  ...
}

Rules:
- Preserve exact stat values from source
- Include source_lines for traceability
- Generate summary from first sentence of description
- Extract special_abilities as list
- Infer related monsters from description mentions
```

### Phase 2: Human Review
After extraction:
1. Spot-check random entries against source
2. Fix OCR errors (e.g., "I" vs "1", "O" vs "0")
3. Validate stat block completeness
4. Add missing cross-references

### Phase 3: Integration Testing
1. Load extracted JSON via RulesIndex
2. Verify all entries accessible via get_rules()
3. Test search functionality
4. Validate summary generation produces reasonable output

## Extraction Task Breakdown

### Batch 1: Monsters (Highest Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 1.1 | Extract monsters A-D | ~15 |
| 1.2 | Extract monsters E-H | ~12 |
| 1.3 | Extract monsters I-O | ~15 |
| 1.4 | Extract monsters P-S | ~12 |
| 1.5 | Extract monsters T-Z | ~10 |
| 1.6 | Review & fix all monsters | - |

### Batch 2: Spells (High Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 2.1 | Extract 1st level Magic-User spells | 12 |
| 2.2 | Extract 2nd level Magic-User spells | 12 |
| 2.3 | Extract Cleric spells | 8 |
| 2.4 | Review & fix all spells | - |

### Batch 3: Magic Items (High Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 3.1 | Extract Swords | ~10 |
| 3.2 | Extract Other Weapons | ~10 |
| 3.3 | Extract Armor & Shields | ~8 |
| 3.4 | Extract Potions | ~10 |
| 3.5 | Extract Rings, Wands, Misc | ~15 |
| 3.6 | Review & fix all items | - |

### Batch 4: Procedures (Medium Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 4.1 | Extract combat procedures | ~5 |
| 4.2 | Extract exploration procedures | ~5 |
| 4.3 | Extract NPC/reaction procedures | ~5 |
| 4.4 | Review & fix all procedures | - |

### Batch 5: Classes & Equipment (Lower Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 5.1 | Extract class descriptions | 7 |
| 5.2 | Extract equipment tables | ~20 |
| 5.3 | Review & fix all | - |

### Batch 6: Reference Charts (Lowest Value)
| Task | Description | Est. Entries |
|------|-------------|--------------|
| 6.1 | Extract saving throw tables | 4 |
| 6.2 | Extract hit roll tables | 2 |
| 6.3 | Extract treasure type tables | 2 |
| 6.4 | Review & fix all | - |

## Priority Recommendation

**Execute in this order**:

1. **Monsters** - Highest ROI. DM needs creature stats for every encounter. ~60 entries with consistent structure makes this tractable.

2. **Spells** - High ROI. Players and DM reference spell effects constantly during play.

3. **Magic Items** - High ROI. Treasure generation and item identification are common DM tasks.

4. **Procedures** - Medium ROI. These are "look up when needed" rules, not constant reference.

5. **Classes** - Lower ROI. LLMs generally know D&D class basics; extraction is for completeness.

6. **Equipment/Charts** - Lowest ROI. Tables are easily referenced manually; charts are already in RULES_SHORTHAND.

## Execution Strategy

**Approach**: Parallel subagents (5 at a time)

Each subagent receives:
- A line range from the source file
- The target JSON schema
- Instructions to fix OCR errors and layout issues
- The existing sample entries as reference

Subagents write directly to JSON files, which are merged after each wave.

---

## Wave Structure (5 Subagents per Wave)

### WAVE 1: Monsters A-F (5 agents)
| Agent | Source Lines | Monsters | Output |
|-------|-------------|----------|--------|
| 1.1 | 2014-2100 | Ant, Ape, Baboon, Bandit, Bat | monsters_01.json |
| 1.2 | 2069-2180 | Bear (4 types), Beetle (3 types), Bee | monsters_02.json |
| 1.3 | 2145-2260 | Bugbear, Caecilia, Carrion Crawler, Cat (4 types) | monsters_03.json |
| 1.4 | 2220-2340 | Centipede, Cockatrice, Crab, Dragon (5 colors) | monsters_04.json |
| 1.5 | 2340-2430 | Doppelganger, Driver Ant, Dwarf, Ferret, Gargoyle, Gelatinous Cube | monsters_05.json |

### WAVE 2: Monsters G-N (5 agents)
| Agent | Source Lines | Monsters | Output |
|-------|-------------|----------|--------|
| 2.1 | 2406-2500 | Ghoul, Gnoll, Gnome, Goblin, Gray Ooze, Green Slime | monsters_06.json |
| 2.2 | 2470-2560 | Halfling, Harpy, Hobgoblin, Insect Swarm, Killer Bee | monsters_07.json |
| 2.3 | 2540-2660 | Kobold, Leech, Living Statue (3 types), Lizard (2 types), Lizard Man | monsters_08.json |
| 2.4 | 2630-2750 | Lycanthrope (5 types), Medusa, Minotaur, Mule | monsters_09.json |
| 2.5 | 2718-2830 | Neanderthal, Nixie, NPC, Ochre Jelly, Ogre, Orc | monsters_10.json |

### WAVE 3: Monsters O-Z (5 agents)
| Agent | Source Lines | Monsters | Output |
|-------|-------------|----------|--------|
| 3.1 | 2780-2900 | Owl Bear, Pixie, Rat, Robber Fly, Rock Baboon, Rust Monster | monsters_11.json |
| 3.2 | 2857-2970 | Shadow, Shrew, Skeleton, Snake (4 types) | monsters_12.json |
| 3.3 | 2962-3070 | Spider (3 types), Sprite, Stirge, Thoul, Troglodyte | monsters_13.json |
| 3.4 | 3046-3150 | Troll, Unicorn, Wight, Wolf (2 types), Yellow Mold, Zombie | monsters_14.json |
| 3.5 | - | MERGE & VALIDATE: Combine all monster files, fix duplicates, add cross-references | monsters.json |

### WAVE 4: Spells (5 agents)
| Agent | Source Lines (Players Manual) | Spells | Output |
|-------|------------------------------|--------|--------|
| 4.1 | 1820-1950 | Cleric spells (1st & 2nd level, ~12 spells) | spells_cleric.json |
| 4.2 | 2630-2740 | Magic-User 1st level (12 spells: Charm Person → Ventriloquism) | spells_mu1.json |
| 4.3 | 2740-2860 | Magic-User 2nd level (12 spells: Continual Light → Wizard Lock) | spells_mu2.json |
| 4.4 | - | MERGE: Combine spell files, add class tags, verify reversible spells | spells.json |
| 4.5 | - | REVIEW: Cross-check all spells against spell lists, fix any missing | spells.json |

### WAVE 5: Magic Items (5 agents)
| Agent | Source Lines (DM Rulebook) | Items | Output |
|-------|---------------------------|-------|--------|
| 5.1 | 3320-3380 | Swords (10 types + cursed rules) | items_swords.json |
| 5.2 | 3340-3400 | Other Weapons, Armor & Shields (~18 items) | items_weapons_armor.json |
| 5.3 | 3370-3450 | Potions (10 types) | items_potions.json |
| 5.4 | 3385-3500 | Scrolls, Rings, Wands/Staves/Rods (~20 items) | items_scrolls_rings_wands.json |
| 5.5 | 3350-3600 | Miscellaneous Items (8 items) + descriptions for all | items_misc.json |

### WAVE 6: Procedures & Classes (5 agents)
| Agent | Source | Content | Output |
|-------|--------|---------|--------|
| 6.1 | DM 200-400 | Procedures: Alignment, Charm, Doors, Evasion | procedures_exploration.json |
| 6.2 | DM 400-600 | Procedures: Languages, Morale, Retainers, Turning | procedures_social.json |
| 6.3 | PM 1950-2200 | Classes: Fighter, Cleric, Magic-User, Thief | classes_human.json |
| 6.4 | PM 3050-3200 | Classes: Dwarf, Elf, Halfling | classes_demihuman.json |
| 6.5 | - | MERGE: Combine procedures and classes | procedures.json, classes.json |

### WAVE 7: Equipment & Final Integration (5 agents)
| Agent | Source | Content | Output |
|-------|--------|---------|--------|
| 7.1 | PM 1500-1700 | Equipment lists: Weapons, Armor, Gear, Costs | equipment.json |
| 7.2 | DM 3200-3320 | Treasure: Coin conversion, Gems, Jewelry tables | treasure.json |
| 7.3 | DM 3700-3900 | Reference: Saving throws, Hit tables, Encounter tables | charts.json |
| 7.4 | - | FINAL MERGE: Combine all category files into final indexed structure | ALL |
| 7.5 | - | INTEGRATION TEST: Run full test suite, verify all paths work | - |

---

## Subagent Prompt Template

```
You are extracting BECMI Basic D&D rules from OCR'd text into structured JSON.

SOURCE FILE: {file_path}
LINE RANGE: {start_line} to {end_line}
CATEGORY: {category}

OUTPUT SCHEMA:
{schema}

REFERENCE EXAMPLE:
{sample_entry}

INSTRUCTIONS:
1. Read the source text carefully
2. Fix OCR errors (common: "I" vs "1", "O" vs "0", garbled ligatures)
3. Fix layout issues (multi-column text may have broken lines)
4. Extract each entry into the schema format
5. Generate concise summaries from the first sentence of descriptions
6. Infer related entries from description mentions
7. Include source_lines for traceability

Write the extracted entries as valid JSON to: {output_file}
```

## Success Criteria

- [ ] All ~60 monsters extracted with complete stat blocks
- [ ] All ~35 spells extracted with effects and durations
- [ ] All ~50 magic items extracted with descriptions
- [ ] All major procedures documented
- [ ] Integration tests pass
- [ ] get_rules() returns accurate content for any path
- [ ] search_rules() finds relevant entries
- [ ] build_rules_summary() produces usable in-context summary

## Estimated Effort

| Batch | Tasks | Subagent Calls | Review Time |
|-------|-------|----------------|-------------|
| Monsters | 6 | ~10 | 30 min |
| Spells | 4 | ~5 | 15 min |
| Magic Items | 6 | ~8 | 20 min |
| Procedures | 4 | ~5 | 15 min |
| Classes/Equipment | 3 | ~4 | 10 min |
| Charts | 4 | ~3 | 5 min |
| **Total** | **27** | **~35** | **~95 min** |

## Files to Create/Modify

### New Files
- `scripts/extract_rules.py` - Extraction script
- `rules/indexed/basic/monsters.json` - Extended with all monsters
- `rules/indexed/basic/spells.json` - Extended with all spells
- `rules/indexed/basic/items.json` - Magic items
- `rules/indexed/basic/procedures.json` - DM procedures
- `rules/indexed/basic/classes.json` - Class descriptions
- `rules/indexed/basic/equipment.json` - Equipment tables

### Modified Files
- `src/dndbots/rules_index.py` - May need adjustments for new categories
- `src/dndbots/rules_prompts.py` - Update summary generation for new content
- `tests/test_rules_integration.py` - Add tests for new content
