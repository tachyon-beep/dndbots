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


class MechanicsEngine:
    """Core mechanics engine for D&D rules adjudication.

    This class manages combat state, tracks combatants, and resolves
    mechanical actions (attacks, saves, checks, etc.). It serves as the
    backend for the Referee agent.

    Attributes:
        combat: Current combat state (None when not in combat)
        pcs: Persistent PC state across combats
        debug_mode: If True, show micro-queries and internal state
    """

    def __init__(self, debug_mode: bool = True):
        """Initialize the mechanics engine.

        Args:
            debug_mode: If True, show micro-queries and internal operations
        """
        self.combat: CombatState | None = None
        self.pcs: dict[str, Combatant] = {}
        self.debug_mode = debug_mode

    # Combat lifecycle methods

    def start_combat(self, style: str = "soft") -> None:
        """Initialize combat state.

        Args:
            style: "soft" (flexible turn order) or "strict" (enforced initiative)

        Raises:
            ValueError: If combat is already active
        """
        if self.combat is not None:
            raise ValueError("Combat already in progress")

        self.combat = CombatState(combat_style=style)

    def add_combatant(
        self,
        id: str,
        name: str,
        hp: int,
        hp_max: int,
        ac: int,
        thac0: int,
        damage_dice: str,
        char_class: str,
        level: int,
        is_pc: bool = False,
    ) -> Combatant:
        """Add a combatant to the current combat.

        Args:
            id: Unique identifier (e.g., "pc_throk", "goblin_01")
            name: Display name
            hp: Current hit points
            hp_max: Maximum hit points
            ac: Armor Class
            thac0: To Hit AC 0 value
            damage_dice: Damage dice notation (e.g., "1d8+2")
            char_class: Class for save lookups (e.g., "fighter", "goblin")
            level: Level for save lookups
            is_pc: True if this is a player character

        Returns:
            The created Combatant

        Raises:
            RuntimeError: If combat is not active
            ValueError: If combatant ID already exists in combat
        """
        if self.combat is None:
            raise RuntimeError("Cannot add combatant: combat not started")

        if id in self.combat.combatants:
            raise ValueError(f"Combatant {id} already exists in combat")

        combatant = Combatant(
            id=id,
            name=name,
            hp=hp,
            hp_max=hp_max,
            ac=ac,
            thac0=thac0,
            damage_dice=damage_dice,
            char_class=char_class,
            level=level,
            is_pc=is_pc,
        )

        self.combat.combatants[id] = combatant

        # Update persistent PC state
        if is_pc:
            self.pcs[id] = combatant

        return combatant

    def end_combat(self) -> dict:
        """End combat, persist PC HP, and return summary.

        Returns:
            Summary dict with combat statistics and final state

        Raises:
            RuntimeError: If combat is not active
        """
        if self.combat is None:
            raise RuntimeError("Cannot end combat: no active combat")

        # Build summary
        summary = {
            "rounds": self.combat.round_number,
            "combatants": len(self.combat.combatants),
            "survivors": sum(1 for c in self.combat.combatants.values() if c.hp > 0),
            "casualties": sum(1 for c in self.combat.combatants.values() if c.hp <= 0),
        }

        # Persist PC HP to permanent state
        for id, combatant in self.combat.combatants.items():
            if combatant.is_pc:
                self.pcs[id] = combatant

        # Clear combat state
        self.combat = None

        return summary

    def get_combat_status(self) -> dict | None:
        """Get current combat status with all combatants.

        Returns:
            Dict with combat state, or None if not in combat
        """
        if self.combat is None:
            return None

        return {
            "round": self.combat.round_number,
            "style": self.combat.combat_style,
            "current_turn": self.combat.current_turn,
            "combatants": {
                id: {
                    "name": c.name,
                    "hp": c.hp,
                    "hp_max": c.hp_max,
                    "ac": c.ac,
                    "conditions": list(c.conditions),
                    "is_pc": c.is_pc,
                }
                for id, c in self.combat.combatants.items()
            },
        }

    def get_combatant(self, id: str) -> Combatant | None:
        """Get a single combatant by ID.

        Args:
            id: Combatant identifier

        Returns:
            Combatant if found, None otherwise
        """
        if self.combat is None:
            return None
        return self.combat.combatants.get(id)

    # Resolution methods (stubbed for later implementation)

    def roll_attack(
        self, attacker: str, target: str, modifier: int = 0
    ) -> AttackResult:
        """Resolve an attack roll.

        Args:
            attacker: ID of attacking combatant
            target: ID of target combatant
            modifier: Additional modifier to attack roll

        Returns:
            AttackResult with outcome

        Raises:
            RuntimeError: If combat is not active
            ValueError: If attacker or target not found
        """
        from .dice import roll
        from .rules import check_hit

        # Validate combat is active
        if self.combat is None:
            raise RuntimeError("Cannot roll attack: no active combat")

        # Validate combatants exist
        attacker_combatant = self.combat.combatants.get(attacker)
        if attacker_combatant is None:
            raise ValueError(f"Attacker {attacker} not found in combat")

        target_combatant = self.combat.combatants.get(target)
        if target_combatant is None:
            raise ValueError(f"Target {target} not found in combat")

        # Get attack parameters
        attacker_thac0 = attacker_combatant.thac0
        target_ac = target_combatant.ac

        # Calculate to-hit number
        needed = attacker_thac0 - target_ac

        # Roll d20 (without modifier initially)
        raw_roll = roll(1, 20, 0)

        # Natural 1 always misses (check raw roll before modifier)
        if raw_roll == 1:
            return AttackResult(
                hit=False,
                roll=raw_roll + modifier,
                needed=needed,
                modifier=modifier,
                narrative="Critical miss! The attack goes wide!",
            )

        # Natural 20 always hits (check raw roll before modifier)
        if raw_roll == 20:
            return AttackResult(
                hit=True,
                roll=raw_roll + modifier,
                needed=needed,
                modifier=modifier,
                narrative="Critical hit! The strike finds its mark!",
            )

        # Normal roll: apply modifier to hit calculation
        final_roll = raw_roll + modifier
        hit = final_roll >= needed
        narrative = "The attack strikes true!" if hit else "The attack misses its target."

        return AttackResult(
            hit=hit, roll=final_roll, needed=needed, modifier=modifier, narrative=narrative
        )

    def roll_damage(
        self,
        attacker: str,
        target: str,
        damage_dice: str | None = None,
        modifier: int = 0,
    ) -> DamageResult:
        """Roll and apply damage.

        Args:
            attacker: ID of attacking combatant
            target: ID of target combatant
            damage_dice: Override damage dice (uses attacker's default if None)
            modifier: Additional damage modifier

        Returns:
            DamageResult with damage dealt and target status

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("roll_damage not yet implemented")

    def roll_save(
        self, target: str, save_type: str, modifier: int = 0
    ) -> SaveResult:
        """Resolve a saving throw.

        Args:
            target: ID of combatant making save
            save_type: Type of save (e.g., "Death", "Wands", "Paralysis")
            modifier: Additional modifier to save roll

        Returns:
            SaveResult with outcome

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("roll_save not yet implemented")

    def roll_ability_check(
        self, target: str, ability: str, difficulty: int, modifier: int = 0
    ) -> CheckResult:
        """Resolve an ability check.

        Args:
            target: ID of combatant making check
            ability: Ability to check (e.g., "str", "dex", "wis")
            difficulty: Target number to beat
            modifier: Additional modifier to check roll

        Returns:
            CheckResult with outcome

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("roll_ability_check not yet implemented")

    def roll_morale(self, target: str) -> MoraleResult:
        """Resolve a morale check (BECMI rules).

        Args:
            target: ID of combatant making morale check

        Returns:
            MoraleResult with outcome

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError("roll_morale not yet implemented")

    def add_condition(self, target: str, condition: str) -> None:
        """Apply a condition to a combatant.

        Args:
            target: ID of combatant
            condition: Condition to add (e.g., "prone", "poisoned")

        Raises:
            RuntimeError: If no active combat
            ValueError: If combatant not found
        """
        if self.combat is None:
            raise RuntimeError("Cannot add condition: no active combat")
        combatant = self.combat.combatants.get(target)
        if combatant is None:
            raise ValueError(f"Combatant {target} not found")
        combatant.conditions.add(condition)

    def remove_condition(self, target: str, condition: str) -> None:
        """Remove a condition from a combatant.

        Args:
            target: ID of combatant
            condition: Condition to remove

        Raises:
            RuntimeError: If no active combat
            ValueError: If combatant not found
        """
        if self.combat is None:
            raise RuntimeError("Cannot remove condition: no active combat")
        combatant = self.combat.combatants.get(target)
        if combatant is None:
            raise ValueError(f"Combatant {target} not found")
        combatant.conditions.discard(condition)  # discard doesn't raise if not present

    def get_conditions(self, target: str) -> list[str]:
        """Get all conditions on a combatant.

        Args:
            target: ID of combatant

        Returns:
            List of active conditions

        Raises:
            RuntimeError: If no active combat
            ValueError: If combatant not found
        """
        if self.combat is None:
            raise RuntimeError("Cannot get conditions: no active combat")
        combatant = self.combat.combatants.get(target)
        if combatant is None:
            raise ValueError(f"Combatant {target} not found")
        return list(combatant.conditions)
