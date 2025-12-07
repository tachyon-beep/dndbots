"""Tests for MechanicsEngine state management."""

import pytest

from dndbots.mechanics import MechanicsEngine, Combatant, CombatState


class TestCombatLifecycle:
    """Tests for starting, ending, and managing combat state."""

    def test_start_combat_creates_state(self):
        """Verify combat state is initialized correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        assert engine.combat is not None
        assert isinstance(engine.combat, CombatState)
        assert engine.combat.combat_style == "soft"
        assert engine.combat.round_number == 1
        assert engine.combat.combatants == {}
        assert engine.combat.initiative_order == []
        assert engine.combat.current_turn is None

    def test_start_combat_raises_if_already_active(self):
        """Can't start combat twice without ending first."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        with pytest.raises(ValueError, match="Combat already in progress"):
            engine.start_combat(style="soft")

    def test_start_combat_strict_mode(self):
        """Verify strict mode sets combat_style to 'strict'."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="strict")

        assert engine.combat is not None
        assert engine.combat.combat_style == "strict"


class TestAddCombatant:
    """Tests for adding combatants to combat."""

    def test_add_combatant_success(self):
        """Adds combatant correctly with all attributes."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        combatant = engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
            is_pc=False,
        )

        assert isinstance(combatant, Combatant)
        assert combatant.id == "goblin_01"
        assert combatant.name == "Goblin"
        assert combatant.hp == 5
        assert combatant.hp_max == 5
        assert combatant.ac == 6
        assert combatant.thac0 == 19
        assert combatant.damage_dice == "1d6"
        assert combatant.char_class == "goblin"
        assert combatant.level == 1
        assert combatant.is_pc is False
        assert combatant.conditions == set()

        # Verify it's in combat state
        assert "goblin_01" in engine.combat.combatants
        assert engine.combat.combatants["goblin_01"] is combatant

    def test_add_combatant_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot add combatant: combat not started"):
            engine.add_combatant(
                id="goblin_01",
                name="Goblin",
                hp=5,
                hp_max=5,
                ac=6,
                thac0=19,
                damage_dice="1d6",
                char_class="goblin",
                level=1,
            )

    def test_add_combatant_raises_on_duplicate_id(self):
        """ValueError on duplicate combatant ID."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add first goblin
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Try to add another with same ID
        with pytest.raises(ValueError, match="Combatant goblin_01 already exists in combat"):
            engine.add_combatant(
                id="goblin_01",
                name="Another Goblin",
                hp=5,
                hp_max=5,
                ac=6,
                thac0=19,
                damage_dice="1d6",
                char_class="goblin",
                level=1,
            )

    def test_add_combatant_persists_pc_state(self):
        """PC is added to self.pcs for persistence across combats."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        combatant = engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+2",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Verify PC is in persistent state
        assert "pc_throk" in engine.pcs
        assert engine.pcs["pc_throk"] is combatant


class TestEndCombat:
    """Tests for ending combat and persisting state."""

    def test_end_combat_returns_summary(self):
        """Returns dict with rounds, survivors, casualties."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add some combatants
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+2",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=0,  # Dead
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
            is_pc=False,
        )
        engine.add_combatant(
            id="goblin_02",
            name="Goblin",
            hp=3,  # Alive
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
            is_pc=False,
        )

        # Simulate a few rounds
        engine.combat.round_number = 5

        summary = engine.end_combat()

        assert summary["rounds"] == 5
        assert summary["combatants"] == 3
        assert summary["survivors"] == 2  # Throk and goblin_02
        assert summary["casualties"] == 1  # goblin_01

    def test_end_combat_persists_pc_hp(self):
        """PC HP is copied to self.pcs after combat."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add PC
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+2",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Modify HP during combat
        engine.combat.combatants["pc_throk"].hp = 3

        # End combat
        engine.end_combat()

        # Verify persistent state has updated HP
        assert engine.pcs["pc_throk"].hp == 3

    def test_end_combat_clears_combat_state(self):
        """combat becomes None after ending."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.end_combat()

        assert engine.combat is None

    def test_end_combat_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot end combat: no active combat"):
            engine.end_combat()


class TestGetStatus:
    """Tests for querying combat and combatant status."""

    def test_get_combat_status_returns_dict(self):
        """Returns combatants and round info."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+2",
            char_class="fighter",
            level=2,
            is_pc=True,
        )
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
            is_pc=False,
        )

        engine.combat.round_number = 3
        engine.combat.current_turn = "pc_throk"

        status = engine.get_combat_status()

        assert status is not None
        assert status["round"] == 3
        assert status["style"] == "soft"
        assert status["current_turn"] == "pc_throk"
        assert "pc_throk" in status["combatants"]
        assert "goblin_01" in status["combatants"]

        throk = status["combatants"]["pc_throk"]
        assert throk["name"] == "Throk"
        assert throk["hp"] == 10
        assert throk["hp_max"] == 10
        assert throk["ac"] == 5
        assert throk["conditions"] == []
        assert throk["is_pc"] is True

        goblin = status["combatants"]["goblin_01"]
        assert goblin["name"] == "Goblin"
        assert goblin["is_pc"] is False

    def test_get_combat_status_returns_none_when_no_combat(self):
        """Returns None if not in combat."""
        engine = MechanicsEngine(debug_mode=False)
        status = engine.get_combat_status()
        assert status is None

    def test_get_combatant_returns_combatant(self):
        """Finds combatant by ID."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        combatant = engine.get_combatant("goblin_01")

        assert combatant is not None
        assert isinstance(combatant, Combatant)
        assert combatant.id == "goblin_01"
        assert combatant.name == "Goblin"

    def test_get_combatant_returns_none_when_not_found(self):
        """Returns None when combatant doesn't exist."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        combatant = engine.get_combatant("nonexistent")
        assert combatant is None

    def test_get_combatant_returns_none_when_no_combat(self):
        """Returns None when not in combat."""
        engine = MechanicsEngine(debug_mode=False)
        combatant = engine.get_combatant("goblin_01")
        assert combatant is None


class TestConditions:
    """Tests for managing combatant conditions."""

    def test_add_condition(self):
        """Adds condition to combatant."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_condition("goblin_01", "prone")

        combatant = engine.get_combatant("goblin_01")
        assert "prone" in combatant.conditions

    def test_add_multiple_conditions(self):
        """Can add multiple conditions to same combatant."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_condition("goblin_01", "prone")
        engine.add_condition("goblin_01", "poisoned")

        combatant = engine.get_combatant("goblin_01")
        assert "prone" in combatant.conditions
        assert "poisoned" in combatant.conditions

    def test_add_condition_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot add condition: no active combat"):
            engine.add_condition("goblin_01", "prone")

    def test_add_condition_raises_on_invalid_combatant(self):
        """ValueError if combatant not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        with pytest.raises(ValueError, match="Combatant nonexistent not found"):
            engine.add_condition("nonexistent", "prone")

    def test_remove_condition(self):
        """Removes condition from combatant."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_condition("goblin_01", "prone")
        engine.remove_condition("goblin_01", "prone")

        combatant = engine.get_combatant("goblin_01")
        assert "prone" not in combatant.conditions

    def test_remove_condition_nonexistent_is_safe(self):
        """discard() doesn't error on missing condition."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Should not raise
        engine.remove_condition("goblin_01", "nonexistent_condition")

        combatant = engine.get_combatant("goblin_01")
        assert "nonexistent_condition" not in combatant.conditions

    def test_remove_condition_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot remove condition: no active combat"):
            engine.remove_condition("goblin_01", "prone")

    def test_remove_condition_raises_on_invalid_combatant(self):
        """ValueError if combatant not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        with pytest.raises(ValueError, match="Combatant nonexistent not found"):
            engine.remove_condition("nonexistent", "prone")

    def test_get_conditions(self):
        """Returns list of conditions."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_condition("goblin_01", "prone")
        engine.add_condition("goblin_01", "poisoned")

        conditions = engine.get_conditions("goblin_01")

        assert isinstance(conditions, list)
        assert len(conditions) == 2
        assert "prone" in conditions
        assert "poisoned" in conditions

    def test_get_conditions_returns_empty_list(self):
        """Returns empty list when no conditions."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        conditions = engine.get_conditions("goblin_01")

        assert conditions == []

    def test_get_conditions_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot get conditions: no active combat"):
            engine.get_conditions("goblin_01")

    def test_get_conditions_raises_on_invalid_combatant(self):
        """ValueError if combatant not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        with pytest.raises(ValueError, match="Combatant nonexistent not found"):
            engine.get_conditions("nonexistent")


class TestRollAttack:
    """Tests for attack roll resolution."""

    def test_roll_attack_basic_hit(self):
        """Attack roll returns AttackResult with hit/miss."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add attacker (THAC0 19, needs 10+ to hit AC 9)
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Add target (AC 9)
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=9,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Roll attack (multiple times to test randomness)
        result = engine.roll_attack("goblin_01", "pc_throk")

        assert hasattr(result, "hit")
        assert hasattr(result, "roll")
        assert hasattr(result, "needed")
        assert hasattr(result, "modifier")
        assert hasattr(result, "narrative")
        assert result.needed == 10  # THAC0 19 - AC 9 = 10
        assert result.modifier == 0
        assert isinstance(result.hit, bool)
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_attack_with_modifier(self):
        """Attack modifier is applied to roll."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=9,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        result = engine.roll_attack("goblin_01", "pc_throk", modifier=2)

        assert result.modifier == 2
        # Roll should include modifier (roll is final d20 + modifier)
        assert result.roll >= 3  # Min d20 (1) + modifier (2)
        assert result.roll <= 22  # Max d20 (20) + modifier (2)

    def test_roll_attack_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot roll attack: no active combat"):
            engine.roll_attack("goblin_01", "pc_throk")

    def test_roll_attack_raises_on_invalid_attacker(self):
        """ValueError if attacker not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=9,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Attacker nonexistent not found in combat"):
            engine.roll_attack("nonexistent", "pc_throk")

    def test_roll_attack_raises_on_invalid_target(self):
        """ValueError if target not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        with pytest.raises(ValueError, match="Target nonexistent not found in combat"):
            engine.roll_attack("goblin_01", "nonexistent")

    def test_roll_attack_modifier_affects_hit(self, monkeypatch):
        """Modifier should affect whether attack hits."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Setup: THAC0 20, AC 10, need 10 to hit
        # If we roll 9 without modifier: miss
        # If we roll 9 with +2 modifier: 11 should hit
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=20,  # Need 10 to hit AC 10 (20 - 10 = 10)
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=10,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock random to always roll 9 on d20
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 9)

        # Without modifier: roll 9 vs needed 10 = miss
        result_no_mod = engine.roll_attack("goblin_01", "pc_throk", modifier=0)
        assert result_no_mod.hit is False
        assert result_no_mod.roll == 9
        assert result_no_mod.needed == 10

        # With +2 modifier: roll 9 + 2 = 11 vs needed 10 = hit
        result_with_mod = engine.roll_attack("goblin_01", "pc_throk", modifier=2)
        assert result_with_mod.hit is True
        assert result_with_mod.roll == 11  # 9 + 2
        assert result_with_mod.needed == 10
        assert result_with_mod.modifier == 2

    def test_roll_attack_natural_1_always_misses(self, monkeypatch):
        """Natural 1 should always miss, even with positive modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=20,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=20,  # Very high AC, but natural 1 misses anyway
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock random to always roll 1
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 1)

        # Natural 1 with +10 modifier still misses
        result = engine.roll_attack("goblin_01", "pc_throk", modifier=10)
        assert result.hit is False
        assert result.roll == 11  # 1 + 10, but still miss
        assert "Critical miss" in result.narrative

    def test_roll_attack_natural_20_always_hits(self, monkeypatch):
        """Natural 20 should always hit, even with negative modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=20,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=-10,  # Impossible AC, but natural 20 hits anyway
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock random to always roll 20
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 20)

        # Natural 20 with -10 modifier still hits
        result = engine.roll_attack("goblin_01", "pc_throk", modifier=-10)
        assert result.hit is True
        assert result.roll == 10  # 20 - 10
        assert "Critical hit" in result.narrative
