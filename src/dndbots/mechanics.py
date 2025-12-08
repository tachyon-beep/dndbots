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
        morale: Morale score for BECMI morale checks (typically 7-12)
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
    morale: int = 7
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
        morale: int = 7,
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
            morale: Morale score for BECMI morale checks (default 7)
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
            morale=morale,
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
            RuntimeError: If combat is not active
            ValueError: If attacker or target not found
        """
        from .dice import roll, parse_roll

        # Validate combat is active
        if self.combat is None:
            raise RuntimeError("Cannot roll damage: no active combat")

        # Validate combatants exist
        attacker_combatant = self.combat.combatants.get(attacker)
        if attacker_combatant is None:
            raise ValueError(f"Attacker {attacker} not found in combat")

        target_combatant = self.combat.combatants.get(target)
        if target_combatant is None:
            raise ValueError(f"Target {target} not found in combat")

        # Get damage dice (use provided or attacker's default)
        dice_notation = damage_dice if damage_dice is not None else attacker_combatant.damage_dice

        if not dice_notation:
            raise ValueError(f"No damage dice specified for {attacker}")

        # Parse dice notation
        parsed = parse_roll(dice_notation)

        # Roll damage
        base_damage = roll(parsed["dice"], parsed["sides"], parsed["modifier"])

        # Apply additional modifier
        total_damage = base_damage + modifier

        # Minimum damage is 1
        if total_damage < 1:
            total_damage = 1

        # Apply damage to target's HP
        target_combatant.hp -= total_damage

        # Determine status based on HP
        if target_combatant.hp <= 0:
            status = "dead"
            narrative = f"{target_combatant.name} collapses!"
        elif target_combatant.hp == 1:
            status = "critical"
            narrative = f"{target_combatant.name} is barely standing!"
        elif target_combatant.hp > target_combatant.hp_max * 0.5:
            status = "healthy"
            narrative = f"A glancing blow against {target_combatant.name}!"
        else:
            status = "wounded"
            narrative = f"A solid hit against {target_combatant.name}!"

        return DamageResult(
            damage=total_damage,
            target_hp=target_combatant.hp,
            target_hp_max=target_combatant.hp_max,
            status=status,
            narrative=narrative,
        )

    def roll_save(
        self, target: str, save_type: str, modifier: int = 0
    ) -> SaveResult:
        """Resolve a saving throw.

        Args:
            target: ID of combatant making save
            save_type: Type of save ("death_ray", "wands", "paralysis", "breath", "spells")
            modifier: Additional modifier to save roll

        Returns:
            SaveResult with outcome

        Raises:
            RuntimeError: If combat is not active
            ValueError: If target not found or save_type invalid
        """
        from .dice import roll
        from .rules import get_saving_throw

        # Validate combat is active
        if self.combat is None:
            raise RuntimeError("Cannot roll save: no active combat")

        # Validate combatant exists
        target_combatant = self.combat.combatants.get(target)
        if target_combatant is None:
            raise ValueError(f"Target {target} not found in combat")

        # Validate save_type (will raise ValueError if invalid)
        # Valid types: "death_ray", "wands", "paralysis", "breath", "spells"
        valid_save_types = ["death_ray", "wands", "paralysis", "breath", "spells"]
        if save_type not in valid_save_types:
            raise ValueError(
                f"Invalid save_type: {save_type}. Must be one of: {', '.join(valid_save_types)}"
            )

        # Get save target number from rules
        needed = get_saving_throw(
            target_combatant.char_class, target_combatant.level, save_type
        )

        # Roll d20 (without modifier initially)
        raw_roll = roll(1, 20, 0)

        # Natural 1 always fails (check raw roll before modifier)
        if raw_roll == 1:
            return SaveResult(
                success=False,
                roll=raw_roll + modifier,
                needed=needed,
                modifier=modifier,
                narrative=f"{target_combatant.name} succumbs to the effect!",
            )

        # Natural 20 always succeeds (check raw roll before modifier)
        if raw_roll == 20:
            return SaveResult(
                success=True,
                roll=raw_roll + modifier,
                needed=needed,
                modifier=modifier,
                narrative=f"{target_combatant.name} shrugs off the effect!",
            )

        # Normal roll: apply modifier to save calculation
        final_roll = raw_roll + modifier
        success = final_roll >= needed

        # Generate narrative based on result
        if success:
            narrative = f"{target_combatant.name} resists the effect!"
        else:
            narrative = f"{target_combatant.name} fails to resist!"

        return SaveResult(
            success=success,
            roll=final_roll,
            needed=needed,
            modifier=modifier,
            narrative=narrative,
        )

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
            RuntimeError: If combat is not active
            ValueError: If target not found or ability invalid
        """
        from .dice import roll

        # Validate combat is active
        if self.combat is None:
            raise RuntimeError("Cannot roll ability check: no active combat")

        # Validate combatant exists
        target_combatant = self.combat.combatants.get(target)
        if target_combatant is None:
            raise ValueError(f"Target {target} not found in combat")

        # Validate ability (Basic D&D six abilities)
        valid_abilities = ["str", "dex", "con", "int", "wis", "cha"]
        if ability not in valid_abilities:
            raise ValueError(
                f"Invalid ability: {ability}. Must be one of: {', '.join(valid_abilities)}"
            )

        # Roll d20 (without modifier initially)
        raw_roll = roll(1, 20, 0)

        # Natural 1 always fails (check raw roll before modifier)
        if raw_roll == 1:
            return CheckResult(
                success=False,
                roll=raw_roll + modifier,
                needed=difficulty,
                modifier=modifier,
                narrative=f"{target_combatant.name} fumbles the {ability} check!",
            )

        # Natural 20 always succeeds (check raw roll before modifier)
        if raw_roll == 20:
            return CheckResult(
                success=True,
                roll=raw_roll + modifier,
                needed=difficulty,
                modifier=modifier,
                narrative=f"{target_combatant.name} succeeds brilliantly at the {ability} check!",
            )

        # Normal roll: apply modifier to check calculation
        final_roll = raw_roll + modifier
        success = final_roll >= difficulty

        # Generate narrative based on result
        if success:
            narrative = f"{target_combatant.name} succeeds at the {ability} check!"
        else:
            narrative = f"{target_combatant.name} fails the {ability} check!"

        return CheckResult(
            success=success,
            roll=final_roll,
            needed=difficulty,
            modifier=modifier,
            narrative=narrative,
        )

    def roll_morale(self, target: str) -> MoraleResult:
        """Resolve a morale check (BECMI rules).

        Args:
            target: ID of combatant making morale check

        Returns:
            MoraleResult with outcome

        Raises:
            RuntimeError: If combat is not active
            ValueError: If target not found
        """
        from .dice import roll

        # Validate combat is active
        if self.combat is None:
            raise RuntimeError("Cannot roll morale: no active combat")

        # Validate combatant exists
        target_combatant = self.combat.combatants.get(target)
        if target_combatant is None:
            raise ValueError(f"Target {target} not found in combat")

        # Get morale score
        morale_score = target_combatant.morale

        # Roll 2d6 (BECMI morale uses 2d6, not d20)
        morale_roll = roll(2, 6, 0)

        # Morale holds if roll <= morale score
        holds = morale_roll <= morale_score

        # Generate narrative based on result
        if holds:
            narrative = f"{target_combatant.name} stands firm!"
        else:
            narrative = f"{target_combatant.name}'s nerve breaks!"

        return MoraleResult(
            holds=holds,
            roll=morale_roll,
            needed=morale_score,
            narrative=narrative,
        )

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
