"""Tool wrappers for Referee agent access to MechanicsEngine.

This module provides AutoGen FunctionTool wrappers around MechanicsEngine
methods, enabling the Referee agent to manage combat state and resolve
mechanical actions through the tool interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autogen_core.tools import FunctionTool

from .mechanics import CombatTrigger, MechanicsEngine

if TYPE_CHECKING:
    from .storage.neo4j_store import Neo4jStore


def create_referee_tools(
    engine: MechanicsEngine,
    neo4j: Neo4jStore | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> list[FunctionTool]:
    """Create tool functions bound to a MechanicsEngine instance.

    Returns tools suitable for AutoGen AssistantAgent(tools=[...]).

    Args:
        engine: The MechanicsEngine instance to operate on
        neo4j: Optional Neo4jStore for recording moments
        campaign_id: Campaign ID for recording
        session_id: Session ID for recording

    Returns:
        List of FunctionTool instances for combat management and resolution

    Example:
        engine = MechanicsEngine()
        tools = create_referee_tools(engine)
        referee = AssistantAgent(name="referee", tools=tools)
    """

    # Combat lifecycle tools

    def start_combat_tool(style: str = "soft") -> str:
        """Initialize combat state.

        Call this when combat begins. Creates a new combat state that tracks
        all combatants, their HP, conditions, and turn order.

        Args:
            style: "soft" (flexible turn order) or "strict" (enforced initiative order)

        Returns:
            Confirmation message
        """
        engine.start_combat(style=style)
        return f"Combat started in {style} mode. Add combatants with add_combatant_tool."

    def add_combatant_tool(
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
    ) -> str:
        """Add a combatant to the current combat.

        Use this to register PCs and NPCs participating in combat. Each combatant
        needs combat statistics (AC, THAC0, HP) and save parameters (class, level).

        Args:
            id: Unique identifier (e.g., "pc_throk", "goblin_01")
            name: Display name (e.g., "Throk", "Goblin #1")
            hp: Current hit points
            hp_max: Maximum hit points
            ac: Armor Class (lower is better in BECMI)
            thac0: To Hit AC 0 value (lower is better)
            damage_dice: Damage dice notation (e.g., "1d8+2", "1d6")
            char_class: Character class for save lookups (e.g., "fighter", "goblin")
            level: Level for save lookups and THAC0
            morale: Morale score for BECMI morale checks (default 7, range 2-12)
            is_pc: True if this is a player character (persists HP across combats)

        Returns:
            Confirmation message with combatant details
        """
        combatant = engine.add_combatant(
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
        pc_status = " (PC)" if is_pc else ""
        return (
            f"Added {combatant.name}{pc_status} to combat: "
            f"HP {combatant.hp}/{combatant.hp_max}, AC {combatant.ac}, "
            f"THAC0 {combatant.thac0}, damage {combatant.damage_dice}"
        )

    def end_combat_tool() -> str:
        """End combat and persist PC hit points.

        Call this when combat is over. PC hit points are saved to persistent
        state and carried into the next combat. NPC state is discarded.

        Returns:
            Combat summary with rounds, survivors, and casualties
        """
        summary = engine.end_combat()
        return (
            f"Combat ended after {summary['rounds']} rounds. "
            f"Survivors: {summary['survivors']}, Casualties: {summary['casualties']}"
        )

    # Resolution tools

    async def roll_attack_tool(attacker: str, target: str, modifier: int = 0) -> str:
        """Resolve an attack roll using BECMI THAC0 rules.

        Rolls d20, applies modifiers, compares to target AC. Considers conditions
        like prone, blinded, frightened, and paralyzed.

        Args:
            attacker: ID of attacking combatant (e.g., "pc_throk")
            target: ID of target combatant (e.g., "goblin_01")
            modifier: Additional modifier to attack roll (e.g., +2 for magic weapon)

        Returns:
            Attack result with hit/miss, roll details, and narrative flavor
        """
        result = engine.roll_attack(attacker, target, modifier)
        hit_status = "HIT" if result.hit else "MISS"

        # Check for crit triggers (use raw roll from result)
        # Note: result.roll includes modifier, we need to detect natural 20/1
        raw_roll = result.roll - result.modifier
        triggers = engine.check_attack_triggers(raw_roll, attacker, target)

        # Record crits to Neo4j
        if neo4j and campaign_id and CombatTrigger.CRIT_HIT in triggers:
            turn = engine.current_turn if hasattr(engine, "current_turn") else 0
            await neo4j.record_moment(
                campaign_id=campaign_id,
                actor_id=attacker,
                moment_type="crit_hit",
                description=f"Natural 20 against {target}",
                session=session_id or "unknown",
                turn=turn,
                target_id=target,
            )

        if neo4j and campaign_id and CombatTrigger.CRIT_FAIL in triggers:
            turn = engine.current_turn if hasattr(engine, "current_turn") else 0
            await neo4j.record_moment(
                campaign_id=campaign_id,
                actor_id=attacker,
                moment_type="crit_fail",
                description="Natural 1 - fumble!",
                session=session_id or "unknown",
                turn=turn,
            )

        return (
            f"Attack roll: {result.roll} vs needed {result.needed} = {hit_status}\n"
            f"(d20 roll with modifier {result.modifier:+d})\n"
            f"{result.narrative}"
        )

    async def roll_damage_tool(
        attacker: str, target: str, damage_dice: str | None = None, modifier: int = 0, weapon: str = "weapon"
    ) -> str:
        """Roll damage and apply it to the target.

        Rolls damage dice, applies modifiers, subtracts from target HP. Updates
        target status (healthy/wounded/critical/dead) and generates narrative.

        Args:
            attacker: ID of attacking combatant
            target: ID of target combatant
            damage_dice: Override damage dice (uses attacker's default if None)
            modifier: Additional damage modifier (e.g., +3 for STR bonus)
            weapon: Weapon name for kill recording (default: "weapon")

        Returns:
            Damage result with amount dealt, target HP, status, and narrative
        """
        result = engine.roll_damage(attacker, target, damage_dice, modifier)

        # Check for kill trigger (target HP went to 0 or below)
        if result.status == "dead" and neo4j and campaign_id:
            turn = engine.current_turn if hasattr(engine, "current_turn") else 0
            await neo4j.record_kill(
                campaign_id=campaign_id,
                attacker_id=attacker,
                target_id=target,
                weapon=weapon,
                damage=result.damage,
                session=session_id or "unknown",
                turn=turn,
            )

        return (
            f"Damage: {result.damage} points dealt\n"
            f"Target HP: {result.target_hp}/{result.target_hp_max} ({result.status})\n"
            f"{result.narrative}"
        )

    def roll_save_tool(target: str, save_type: str, modifier: int = 0) -> str:
        """Resolve a saving throw using BECMI save tables.

        Rolls d20 vs target number from BECMI save tables based on character
        class and level. Natural 1 always fails, natural 20 always succeeds.

        Args:
            target: ID of combatant making the save
            save_type: Type of save (one of: "death_ray", "wands", "paralysis", "breath", "spells")
            modifier: Additional modifier to save roll (e.g., +2 for magic item)

        Returns:
            Save result with success/failure, roll details, and narrative
        """
        result = engine.roll_save(target, save_type, modifier)
        save_status = "SUCCESS" if result.success else "FAILURE"
        return (
            f"Saving throw ({save_type}): {result.roll} vs needed {result.needed} = {save_status}\n"
            f"(d20 roll with modifier {result.modifier:+d})\n"
            f"{result.narrative}"
        )

    def roll_ability_check_tool(
        target: str, ability: str, difficulty: int, modifier: int = 0
    ) -> str:
        """Resolve an ability check.

        Rolls d20 vs difficulty target. Natural 1 always fails, natural 20
        always succeeds. Used for STR/DEX/CON/INT/WIS/CHA checks.

        Args:
            target: ID of combatant making the check
            ability: Ability to check (one of: "str", "dex", "con", "int", "wis", "cha")
            difficulty: Target number to beat (typically 10-20)
            modifier: Additional modifier to check roll

        Returns:
            Check result with success/failure, roll details, and narrative
        """
        result = engine.roll_ability_check(target, ability, difficulty, modifier)
        check_status = "SUCCESS" if result.success else "FAILURE"
        return (
            f"Ability check ({ability.upper()}): {result.roll} vs needed {result.needed} = {check_status}\n"
            f"(d20 roll with modifier {result.modifier:+d})\n"
            f"{result.narrative}"
        )

    def roll_morale_tool(target: str) -> str:
        """Resolve a BECMI morale check.

        Rolls 2d6 vs combatant's morale score. If roll <= morale, creature
        continues fighting. If roll > morale, creature flees or surrenders.

        Args:
            target: ID of combatant making the morale check

        Returns:
            Morale result with holds/breaks, roll details, and narrative
        """
        result = engine.roll_morale(target)
        morale_status = "HOLDS" if result.holds else "BREAKS"
        return (
            f"Morale check: {result.roll} vs needed {result.needed} = {morale_status}\n"
            f"(2d6 roll)\n"
            f"{result.narrative}"
        )

    # Condition management tools

    def add_condition_tool(target: str, condition: str) -> str:
        """Apply a condition to a combatant.

        Conditions affect combat mechanics (prone gives -4 to attacks, blinded
        gives -4 to attacks and +4 to be hit, etc.). Multiple conditions stack.

        Common conditions: prone, poisoned, paralyzed, charmed, frightened,
        blinded, slowed, hasted.

        Args:
            target: ID of combatant to affect
            condition: Condition to apply (e.g., "prone", "blinded")

        Returns:
            Confirmation message
        """
        engine.add_condition(target, condition)
        conditions = engine.get_conditions(target)
        return f"Applied '{condition}' to {target}. Active conditions: {', '.join(conditions)}"

    def remove_condition_tool(target: str, condition: str) -> str:
        """Remove a condition from a combatant.

        Removes a previously applied condition. Safe to call even if the
        condition is not currently active.

        Args:
            target: ID of combatant
            condition: Condition to remove (e.g., "prone")

        Returns:
            Confirmation message
        """
        engine.remove_condition(target, condition)
        conditions = engine.get_conditions(target)
        condition_text = ", ".join(conditions) if conditions else "none"
        return f"Removed '{condition}' from {target}. Active conditions: {condition_text}"

    # Status query tools

    def get_combat_status_tool() -> str:
        """Get current combat status with all combatants.

        Returns a formatted summary of all combatants in combat, including
        their HP, AC, conditions, and PC/NPC status. Use this to check
        current combat state.

        Returns:
            Formatted combat status or "No active combat" message
        """
        status = engine.get_combat_status()
        if status is None:
            return "No active combat"

        lines = [
            f"Combat Status - Round {status['round']} ({status['style']} mode)",
            "",
        ]

        if status["current_turn"]:
            lines.append(f"Current turn: {status['current_turn']}")
            lines.append("")

        lines.append("Combatants:")
        for id, info in status["combatants"].items():
            pc_marker = " [PC]" if info["is_pc"] else ""
            conditions = f" [{', '.join(info['conditions'])}]" if info["conditions"] else ""
            lines.append(
                f"  {id}: {info['name']}{pc_marker} - "
                f"HP {info['hp']}/{info['hp_max']}, AC {info['ac']}{conditions}"
            )

        return "\n".join(lines)

    def get_combatant_tool(id: str) -> str:
        """Get detailed information about a single combatant.

        Use this to check specific combatant details during combat, including
        their current HP, conditions, and combat statistics.

        Args:
            id: Combatant identifier (e.g., "pc_throk", "goblin_01")

        Returns:
            Formatted combatant details or "not found" message
        """
        combatant = engine.get_combatant(id)
        if combatant is None:
            return f"Combatant {id} not found (combat may not be active)"

        pc_marker = " [PC]" if combatant.is_pc else ""
        conditions = f"[{', '.join(combatant.conditions)}]" if combatant.conditions else "[none]"

        return (
            f"{combatant.name}{pc_marker} ({id})\n"
            f"  HP: {combatant.hp}/{combatant.hp_max}\n"
            f"  AC: {combatant.ac}, THAC0: {combatant.thac0}\n"
            f"  Damage: {combatant.damage_dice}\n"
            f"  Class: {combatant.char_class}, Level: {combatant.level}\n"
            f"  Morale: {combatant.morale}\n"
            f"  Conditions: {conditions}"
        )

    # Generic dice rolling tool

    def roll_dice_tool(notation: str, purpose: str = "") -> str:
        """Roll dice using standard notation.

        Use this for any dice roll not covered by specific tools:
        - Initiative rolls (1d6 per side in BECMI)
        - Random encounters
        - Treasure determination
        - Any ad-hoc rolls

        Args:
            notation: Dice notation like "1d6", "2d6", "1d20", "3d6+2"
            purpose: Optional description of what the roll is for

        Returns:
            Roll result with breakdown

        Examples:
            roll_dice_tool("1d6", "Throk's initiative")
            roll_dice_tool("2d6", "Goblin morale check")
            roll_dice_tool("1d100", "Random encounter")
        """
        from .dice import roll, parse_roll

        try:
            parsed = parse_roll(notation)
            result = roll(parsed["dice"], parsed["sides"], parsed["modifier"])

            purpose_text = f" for {purpose}" if purpose else ""
            modifier_text = f" + {parsed['modifier']}" if parsed["modifier"] > 0 else ""
            modifier_text = f" - {abs(parsed['modifier'])}" if parsed["modifier"] < 0 else modifier_text

            return (
                f"Rolled {notation}{purpose_text}: {result}\n"
                f"({parsed['dice']}d{parsed['sides']}{modifier_text})"
            )
        except Exception as e:
            return f"Invalid dice notation '{notation}': {e}"

    # Build and return tool list
    return [
        FunctionTool(start_combat_tool, description=start_combat_tool.__doc__),
        FunctionTool(add_combatant_tool, description=add_combatant_tool.__doc__),
        FunctionTool(end_combat_tool, description=end_combat_tool.__doc__),
        FunctionTool(roll_attack_tool, description=roll_attack_tool.__doc__),
        FunctionTool(roll_damage_tool, description=roll_damage_tool.__doc__),
        FunctionTool(roll_save_tool, description=roll_save_tool.__doc__),
        FunctionTool(roll_ability_check_tool, description=roll_ability_check_tool.__doc__),
        FunctionTool(roll_morale_tool, description=roll_morale_tool.__doc__),
        FunctionTool(roll_dice_tool, description=roll_dice_tool.__doc__),
        FunctionTool(add_condition_tool, description=add_condition_tool.__doc__),
        FunctionTool(remove_condition_tool, description=remove_condition_tool.__doc__),
        FunctionTool(get_combat_status_tool, description=get_combat_status_tool.__doc__),
        FunctionTool(get_combatant_tool, description=get_combatant_tool.__doc__),
    ]
