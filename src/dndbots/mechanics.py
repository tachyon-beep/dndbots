"""Mechanics and combat state dataclasses for the Referee agent."""

from dataclasses import dataclass, field


@dataclass
class Combatant:
    """Tracks a single combatant (PC or NPC) in combat.

    Attributes:
        id: Unique identifier (e.g., "pc_throk", "goblin_01")
        name: Display name (e.g., "Throk", "Goblin")
        hp: Current hit points
        hp_max: Maximum hit points
        ac: Armor Class
        thac0: To Hit AC 0 value
        damage_dice: Current attack damage (e.g., "1d8+2")
        char_class: Character class for save lookups (e.g., "fighter", "goblin")
        level: Level for save lookups
        conditions: Set of active conditions (e.g., {"prone", "poisoned"})
        is_pc: True for player characters, False for NPCs
    """

    id: str
    name: str
    hp: int
    hp_max: int
    ac: int
    thac0: int
    damage_dice: str
    char_class: str
    level: int
    conditions: set[str] = field(default_factory=set)
    is_pc: bool = False


@dataclass
class CombatState:
    """Tracks the current state of combat.

    Attributes:
        combatants: Dictionary of all active combatants by ID
        initiative_order: List of combatant IDs in turn order (strict mode)
        current_turn: ID of combatant whose turn it is (strict mode, None if soft)
        round_number: Current combat round (starts at 1)
        combat_style: "soft" (flexible) or "strict" (enforced turn order)
    """

    combatants: dict[str, Combatant] = field(default_factory=dict)
    initiative_order: list[str] = field(default_factory=list)
    current_turn: str | None = None
    round_number: int = 1
    combat_style: str = "soft"


@dataclass
class AttackResult:
    """Result of an attack roll.

    Attributes:
        hit: True if attack hit, False if missed
        roll: The d20 roll result
        needed: The target number needed to hit
        modifier: Any modifier applied to the roll
        narrative: Flavor text describing the result
    """

    hit: bool
    roll: int
    needed: int
    modifier: int
    narrative: str


@dataclass
class DamageResult:
    """Result of damage application.

    Attributes:
        damage: Amount of damage dealt
        target_hp: Target's hit points after damage
        target_hp_max: Target's maximum hit points
        status: Current status (e.g., "wounded", "critical", "dead")
        narrative: Flavor text describing the result
    """

    damage: int
    target_hp: int
    target_hp_max: int
    status: str
    narrative: str


@dataclass
class SaveResult:
    """Result of a saving throw.

    Attributes:
        success: True if save succeeded, False if failed
        roll: The d20 roll result
        needed: The target number needed to save
        modifier: Any modifier applied to the roll
        narrative: Flavor text describing the result
    """

    success: bool
    roll: int
    needed: int
    modifier: int
    narrative: str


@dataclass
class CheckResult:
    """Result of an ability check.

    Attributes:
        success: True if check succeeded, False if failed
        roll: The d20 roll result
        needed: The target number needed to succeed
        modifier: Any modifier applied to the roll
        narrative: Flavor text describing the result
    """

    success: bool
    roll: int
    needed: int
    modifier: int
    narrative: str


@dataclass
class MoraleResult:
    """Result of a morale check (BECMI rules).

    Attributes:
        holds: True if morale holds, False if breaks
        roll: The 2d6 roll result
        needed: The target number needed for morale to hold
        narrative: Flavor text describing the result
    """

    holds: bool
    roll: int
    needed: int
    narrative: str
