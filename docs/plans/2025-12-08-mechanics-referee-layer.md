# Mechanics + Referee Layer Design

**Date:** 2025-12-08
**Status:** Design Complete, Ready for Implementation

## Overview

Add a Referee agent and MechanicsEngine to handle D&D mechanical resolution. This separates concerns:
- **DM**: Narrative, world-building, NPC personalities, plot pacing
- **Referee**: Rules adjudication, dice rolls, state tracking, mechanical checks
- **Players**: Character roleplay and decision-making

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SelectorGroupChat                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│  │   DM    │    │ Player1 │    │ Player2 │    │ Referee │      │
│  │ (story) │    │ (Throk) │    │ (Zara)  │    │ (rules) │      │
│  └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘      │
│       │              │              │              │            │
│       └──────────────┴──────────────┴──────────────┘            │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  MechanicsEngine    │
                    │  ─────────────────  │
                    │  • CombatState      │
                    │  • roll_attack()    │
                    │  • roll_damage()    │
                    │  • roll_save()      │
                    │  • roll_check()     │
                    └─────────────────────┘
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Referee placement | Participant agent in group chat | Natural conversation flow, can interject with narrative |
| Tool access | Only Referee has mechanical tools | Single source of truth, no conflicting state updates |
| Monster stats | Referee proposes, DM confirms/adjusts | Referee does bookkeeping, DM retains authority |
| Combat structure | Configurable: "soft" (default) or "strict" | Start flexible, tighten if needed |
| Attack tracking | Single `damage_dice` per combatant | DM narrates attack type, Referee validates and sets dice |
| Saving throws | Store class/level, derive from tables | No data duplication, uses existing rules.py |
| Inventory/resources | Not tracked formally | Referee reminds narratively; add formal tracking later if needed |
| Referee style | Proactive helper | Catches mistakes, warns of risks, but doesn't usurp DM's world authority |
| Turn order | Micro-queries after each message | Lightweight "do you want to intervene?" checks |
| Visibility | Debug mode (all visible) initially | Transparency for development; clean mode later |

## Domain Boundaries

**Referee's domain (mechanical rules):**
- Attack resolution, damage, saving throws
- Ability checks (climbing, sneaking, etc.)
- Condition tracking and mechanical effects
- Morale checks
- Rule clarifications ("that's -4 while prone")
- Resource usage reminders

**DM's domain (world consequences):**
- What noise attracts
- NPC reactions and motivations
- Plot beats and pacing
- Environmental descriptions
- Whether something requires a check at all (can override Referee)

## Data Structures

### Combatant

```python
@dataclass
class Combatant:
    id: str                    # "pc_throk", "goblin_01"
    name: str                  # "Throk", "Goblin"
    hp: int                    # Current HP
    hp_max: int                # Maximum HP
    ac: int                    # Armor Class
    thac0: int                 # To Hit AC 0
    damage_dice: str           # Current attack: "1d8+2"
    char_class: str            # For save lookups: "fighter", "goblin"
    level: int                 # For save lookups
    conditions: set[str]       # {"prone", "poisoned"}
    is_pc: bool                # True for player characters
```

### CombatState

```python
@dataclass
class CombatState:
    combatants: dict[str, Combatant]  # All active combatants by ID
    initiative_order: list[str]        # Turn order (strict mode)
    current_turn: str | None           # Whose turn (strict mode)
    round_number: int                  # Current combat round
    combat_style: str                  # "soft" or "strict"
```

### MechanicsEngine

```python
class MechanicsEngine:
    combat: CombatState | None    # None when not in combat
    pcs: dict[str, Combatant]     # Persistent PC state across combats
    debug_mode: bool              # Show all micro-queries

    # Combat lifecycle
    def start_combat(self, style: str = "soft") -> None
    def add_combatant(self, name: str, stats: dict, is_pc: bool) -> Combatant
    def end_combat(self) -> dict  # Returns summary, persists PC HP

    # Attack resolution
    def roll_attack(self, attacker: str, target: str, modifier: int = 0) -> AttackResult
    def roll_damage(self, attacker: str, target: str, damage_dice: str = None, modifier: int = 0) -> DamageResult

    # Saving throws
    def roll_save(self, target: str, save_type: str, modifier: int = 0) -> SaveResult

    # Ability checks
    def roll_ability_check(self, target: str, ability: str, difficulty: int, modifier: int = 0) -> CheckResult

    # Conditions
    def add_condition(self, target: str, condition: str) -> None
    def remove_condition(self, target: str, condition: str) -> None
    def get_conditions(self, target: str) -> list[str]

    # Status
    def get_combat_status(self) -> dict
    def get_combatant(self, id: str) -> Combatant | None

    # Morale (BECMI rules)
    def roll_morale(self, target: str) -> MoraleResult
```

### Result Types

```python
@dataclass
class AttackResult:
    hit: bool
    roll: int
    needed: int
    modifier: int
    narrative: str  # "The blade finds its mark!"

@dataclass
class DamageResult:
    damage: int
    target_hp: int
    target_hp_max: int
    status: str  # "wounded", "critical", "dead"
    narrative: str  # "The goblin crumples!"

@dataclass
class SaveResult:
    success: bool
    roll: int
    needed: int
    modifier: int
    narrative: str

@dataclass
class CheckResult:
    success: bool
    roll: int
    needed: int
    modifier: int
    narrative: str

@dataclass
class MoraleResult:
    holds: bool
    roll: int
    needed: int
    narrative: str  # "The goblin's nerve breaks!"
```

## Referee Tools

Tools exposed to the Referee agent via AutoGen:

```python
REFEREE_TOOLS = [
    # Combat lifecycle
    start_combat,           # Initialize combat state
    add_combatant,          # Add PC or NPC to combat
    end_combat,             # Clear combat, persist PC HP

    # Resolution
    roll_attack,            # Attack roll with THAC0
    roll_damage,            # Damage roll, apply to target
    roll_save,              # Saving throw by category
    roll_ability_check,     # STR/DEX/CON/INT/WIS/CHA check
    roll_morale,            # BECMI morale check

    # Conditions
    add_condition,          # Apply condition (prone, poisoned, etc.)
    remove_condition,       # Remove condition

    # Status
    get_combat_status,      # All combatants, HP, conditions
    get_combatant,          # Single combatant details
]
```

## BECMI Conditions

Standard conditions with mechanical effects:

| Condition | Mechanical Effect |
|-----------|-------------------|
| prone | -4 to melee attacks, +4 to be hit by melee |
| poisoned | Per poison type (damage, penalties, or death) |
| paralyzed | Cannot act, auto-hit in melee |
| charmed | Cannot attack charmer, may follow suggestions |
| frightened | Must flee, -2 to attacks |
| blinded | -4 to attacks, +4 to be hit |
| slowed | Half movement, -2 initiative |
| hasted | Double movement, +2 initiative |

Situational modifiers (oil, darkness, flanking) are Referee judgment calls, not formal conditions.

## Turn Order: Micro-Query System

After each message, the selector runs lightweight queries:

```
1. [To Referee]: "Based on this action, any mechanics to resolve?"
   → "No" / "Yes: [brief description]"

2. [To DM]: "Anything to add or redirect?"
   → "Pass" / "Interject: [brief description]" / "Cut to [player]"
```

### Query Order
1. Referee first (mechanics trump narrative)
2. DM second (if Referee passed or after Referee speaks)
3. If both pass → next player (round-robin or contextual)

### Debug Mode
When `debug_mode=True`, micro-queries and responses are visible:
```
[Referee check]: Mechanics needed? → "Climbing check required"
[DM check]: Anything to add? → "Pass"
```

When `debug_mode=False`, only actual interventions are shown.

## Referee System Prompt

Key instructions for the Referee agent:

```markdown
You are the Rules Referee for this D&D game. Your role is mechanical adjudication.

## Your Domain
- Resolve attacks, damage, saving throws, ability checks
- Track HP, conditions, and combat state
- Apply BECMI rules accurately
- Make judgment calls on situational modifiers
- Remind players about resource usage ("mark off that potion")
- Flag risks proactively ("that torch near the oil is dangerous")

## Not Your Domain
- Narrative descriptions (that's the DM)
- World consequences (what noise attracts, NPC reactions)
- Plot decisions
- Whether something requires a check (DM can override you)

## When to Speak
- Attack or harmful action declared
- Saving throw situation
- Ability check needed (climbing, sneaking, etc.)
- Condition changes
- Status questions
- Resource usage (remind to track)

## When to Stay Silent
- Pure roleplay
- Exploration without risk
- Player planning/discussion
- DM narration

## Style
- State rulings briefly with rationale
- Roll and narrate results with flavor
- Confirm monster stats with DM before adding
- Don't lecture or over-explain
- Be helpful, not pedantic

## Monster Stats
When combat starts, propose stats from the rules index:
"Adding 4 goblins: HD 1-1, AC 6, HP 4 each, damage 1d6. Sound right?"
DM can adjust: "Make them 6 HP, they're well-fed."
```

## Implementation Tasks

### Phase 1: MechanicsEngine Core
1. Create `src/dndbots/mechanics.py`
2. Implement `Combatant` and `CombatState` dataclasses
3. Implement `MechanicsEngine` class with combat lifecycle
4. Add result dataclasses (`AttackResult`, etc.)
5. Write tests for state management

### Phase 2: Resolution Methods
1. Implement `roll_attack()` using existing THAC0 logic
2. Implement `roll_damage()` with HP tracking
3. Implement `roll_save()` using rules.py tables
4. Implement `roll_ability_check()`
5. Implement `roll_morale()`
6. Add condition modifiers to attack/save rolls
7. Write tests for each resolution method

### Phase 3: Referee Agent
1. Create Referee system prompt in `prompts.py`
2. Create tool wrappers for AutoGen
3. Add Referee agent to `game.py`
4. Wire tools to MechanicsEngine instance

### Phase 4: Selector Updates
1. Implement micro-query system
2. Add Referee-first check to selector
3. Add DM pass/interject/redirect logic
4. Add `debug_mode` toggle for visibility
5. Test turn order flows

### Phase 5: Integration
1. Wire Referee into existing game flow
2. Update Session Zero to introduce Referee role
3. Test full combat scenario
4. Test non-combat checks (climbing, sneaking)
5. Test mixed roleplay + mechanics flow

## Configuration

New settings in game config:

```python
@dataclass
class MechanicsConfig:
    combat_style: str = "soft"      # "soft" or "strict"
    debug_mode: bool = True         # Show micro-queries
    referee_model: str = "gpt-4o"   # Model for Referee agent
```

## Future Enhancements (Not This Phase)

- **Inventory tracking**: Formal consumable/ammo tracking
- **Spell slots**: Track spells per day
- **Initiative variants**: Group initiative, side initiative
- **Clean mode**: Hide micro-queries for smoother UX
- **Out-of-band queries**: DM/Referee checks not in main chat

## Testing Strategy

1. **Unit tests**: MechanicsEngine methods in isolation
2. **Integration tests**: Referee agent with mocked LLM
3. **Flow tests**: Full turn order with micro-queries
4. **Scenario tests**: Combat, ability checks, mixed roleplay
