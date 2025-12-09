"""Tests for mechanics trigger detection."""

import pytest
from dndbots.mechanics import MechanicsEngine, CombatTrigger


class TestCombatTriggers:
    """Test detection of noteworthy combat events."""

    def test_detect_kill_trigger(self):
        """Damage reducing HP to 0 or below triggers kill."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant(
            id="pc_hero",
            name="Hero",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
        )
        engine.add_combatant(
            id="npc_goblin",
            name="Goblin",
            hp=4,
            hp_max=4,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Deal lethal damage
        triggers = engine.apply_damage("npc_goblin", 5, source="pc_hero")

        assert CombatTrigger.KILL in triggers
        assert triggers[CombatTrigger.KILL]["attacker"] == "pc_hero"
        assert triggers[CombatTrigger.KILL]["target"] == "npc_goblin"

    def test_detect_overkill_trigger(self):
        """Damage >= 2x remaining HP triggers overkill."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant(
            id="pc_hero",
            name="Hero",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
        )
        engine.add_combatant(
            id="npc_goblin",
            name="Goblin",
            hp=4,
            hp_max=4,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Deal massive damage (10 vs 4 HP = 2.5x)
        triggers = engine.apply_damage("npc_goblin", 10, source="pc_hero")

        assert CombatTrigger.KILL in triggers
        assert CombatTrigger.OVERKILL in triggers

    def test_detect_crit_hit(self):
        """Natural 20 on attack triggers crit_hit."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant(
            id="pc_hero",
            name="Hero",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
        )
        engine.add_combatant(
            id="npc_goblin",
            name="Goblin",
            hp=4,
            hp_max=4,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Check if roll was a natural 20
        triggers = engine.check_attack_triggers(roll=20, attacker="pc_hero", target="npc_goblin")

        assert CombatTrigger.CRIT_HIT in triggers

    def test_detect_crit_fail(self):
        """Natural 1 on attack triggers crit_fail."""
        engine = MechanicsEngine()
        engine.start_combat()
        engine.add_combatant(
            id="pc_hero",
            name="Hero",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
        )

        triggers = engine.check_attack_triggers(roll=1, attacker="pc_hero", target="npc_goblin")

        assert CombatTrigger.CRIT_FAIL in triggers

    def test_detect_clutch_save(self):
        """Save made by 1-2 points triggers clutch_save."""
        engine = MechanicsEngine()

        # Needed 14, rolled 15 = margin of 1
        triggers = engine.check_save_triggers(
            roll=15,
            needed=14,
            character="pc_hero",
            save_type="death",
        )

        assert CombatTrigger.CLUTCH_SAVE in triggers

    def test_no_trigger_on_normal_save(self):
        """Normal save (margin > 2) doesn't trigger clutch_save."""
        engine = MechanicsEngine()

        # Needed 14, rolled 18 = margin of 4
        triggers = engine.check_save_triggers(
            roll=18,
            needed=14,
            character="pc_hero",
            save_type="death",
        )

        assert CombatTrigger.CLUTCH_SAVE not in triggers
