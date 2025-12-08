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


class TestRollDamage:
    """Tests for damage roll and application."""

    def test_roll_damage_basic(self, monkeypatch):
        """Basic damage roll uses attacker's damage_dice."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Attacker with 1d6 damage
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

        # Target with 10 HP
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 4
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 4)

        result = engine.roll_damage("goblin_01", "pc_throk")

        assert result.damage == 4
        assert result.target_hp == 6  # 10 - 4
        assert result.target_hp_max == 10
        assert result.status == "healthy"  # 6/10 = 60% > 50%
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_damage_custom_damage_dice(self, monkeypatch):
        """Can override damage_dice parameter."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",  # Default
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d8 roll to 6
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 6)

        # Override with 1d8 instead of goblin's default 1d6
        result = engine.roll_damage("goblin_01", "pc_throk", damage_dice="1d8")

        assert result.damage == 6
        assert result.target_hp == 4  # 10 - 6

    def test_roll_damage_with_modifier(self, monkeypatch):
        """Damage modifier is applied."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 3
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 3)

        result = engine.roll_damage("goblin_01", "pc_throk", modifier=2)

        assert result.damage == 5  # 3 + 2
        assert result.target_hp == 5  # 10 - 5

    def test_roll_damage_minimum_one(self, monkeypatch):
        """Damage is minimum 1, even with negative modifier."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 1
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 1)

        # 1 - 5 = -4, but minimum is 1
        result = engine.roll_damage("goblin_01", "pc_throk", modifier=-5)

        assert result.damage == 1
        assert result.target_hp == 9  # 10 - 1

    def test_roll_damage_status_healthy(self, monkeypatch):
        """Status is 'healthy' when HP > 50%."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 1 (10 - 1 = 9, which is 90% > 50%)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 1)

        result = engine.roll_damage("goblin_01", "pc_throk")

        assert result.status == "healthy"
        assert result.target_hp == 9

    def test_roll_damage_status_wounded(self, monkeypatch):
        """Status is 'wounded' when 0 < HP <= 50%."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 5 (10 - 5 = 5, which is 50%)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 5)

        result = engine.roll_damage("goblin_01", "pc_throk")

        assert result.status == "wounded"
        assert result.target_hp == 5

    def test_roll_damage_status_critical(self, monkeypatch):
        """Status is 'critical' when HP = 1."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 6, with +3 modifier (10 - 9 = 1)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 6)

        result = engine.roll_damage("goblin_01", "pc_throk", modifier=3)

        assert result.status == "critical"
        assert result.target_hp == 1

    def test_roll_damage_status_dead(self, monkeypatch):
        """Status is 'dead' when HP <= 0."""
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
            hp=5,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 5 (5 - 5 = 0)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 5)

        result = engine.roll_damage("goblin_01", "pc_throk")

        assert result.status == "dead"
        assert result.target_hp == 0

    def test_roll_damage_can_go_negative(self, monkeypatch):
        """HP can go negative (for overkill damage)."""
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
            hp=2,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 6 (2 - 6 = -4)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 6)

        result = engine.roll_damage("goblin_01", "pc_throk")

        assert result.damage == 6
        assert result.target_hp == -4
        assert result.status == "dead"

    def test_roll_damage_modifies_combatant_hp(self, monkeypatch):
        """Damage is actually applied to the combatant's HP."""
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
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Mock d6 roll to 4
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 4)

        # Initial HP
        assert engine.get_combatant("pc_throk").hp == 10

        # Apply damage
        result = engine.roll_damage("goblin_01", "pc_throk")

        # HP should be reduced
        assert engine.get_combatant("pc_throk").hp == 6
        assert result.target_hp == 6

    def test_roll_damage_with_dice_notation_modifier(self, monkeypatch):
        """Damage dice with built-in modifier (e.g., '1d8+2')."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8+2",  # Built-in +2
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=10,
            hp_max=10,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
        )

        # Mock d8 roll to 5
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 5)

        # Should be 5 (roll) + 2 (built-in) = 7
        result = engine.roll_damage("pc_throk", "goblin_01")

        assert result.damage == 7  # 5 + 2
        assert result.target_hp == 3  # 10 - 7

    def test_roll_damage_raises_without_combat(self):
        """RuntimeError if no active combat."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot roll damage: no active combat"):
            engine.roll_damage("goblin_01", "pc_throk")

    def test_roll_damage_raises_on_invalid_attacker(self):
        """ValueError if attacker not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Attacker nonexistent not found in combat"):
            engine.roll_damage("nonexistent", "pc_throk")

    def test_roll_damage_raises_on_invalid_target(self):
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
            engine.roll_damage("goblin_01", "nonexistent")

    def test_roll_damage_raises_on_empty_damage_dice(self):
        """ValueError if damage_dice is empty or None."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add attacker with empty damage_dice
        engine.add_combatant(
            id="goblin_01",
            name="Goblin",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="",  # Empty damage dice
            char_class="goblin",
            level=1,
        )

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=18,
            damage_dice="1d8",
            char_class="fighter",
            level=2,
            is_pc=True,
        )

        # Should raise ValueError when trying to roll damage with empty damage_dice
        with pytest.raises(ValueError, match="No damage dice specified for goblin_01"):
            engine.roll_damage("goblin_01", "pc_throk")

        # Also test when passing None explicitly
        with pytest.raises(ValueError, match="No damage dice specified for goblin_01"):
            engine.roll_damage("goblin_01", "pc_throk", damage_dice=None)


class TestRollSave:
    """Tests for saving throw resolution."""

    def test_roll_save_basic_success(self, monkeypatch):
        """Successful save when roll meets target number."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add a level 1 fighter (needs 12 for death_ray saves)
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 12 (exactly what's needed)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 12)

        result = engine.roll_save("pc_throk", "death_ray")

        assert result.success is True
        assert result.roll == 12
        assert result.needed == 12  # Level 1 Fighter death_ray save
        assert result.modifier == 0
        assert isinstance(result.narrative, str)
        assert "resists" in result.narrative.lower()

    def test_roll_save_basic_failure(self, monkeypatch):
        """Failed save when roll below target number."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add a level 1 fighter (needs 12 for death_ray saves)
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 11 (one below needed)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 11)

        result = engine.roll_save("pc_throk", "death_ray")

        assert result.success is False
        assert result.roll == 11
        assert result.needed == 12
        assert result.modifier == 0
        assert isinstance(result.narrative, str)
        assert "fails" in result.narrative.lower()

    def test_roll_save_natural_1_always_fails(self, monkeypatch):
        """Natural 1 always fails, even with positive modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 1
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 1)

        # Even with +20 modifier, natural 1 fails
        result = engine.roll_save("pc_throk", "death_ray", modifier=20)

        assert result.success is False
        assert result.roll == 21  # 1 + 20 modifier
        assert result.modifier == 20
        assert "succumbs" in result.narrative.lower()

    def test_roll_save_natural_20_always_succeeds(self, monkeypatch):
        """Natural 20 always succeeds, even with negative modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 20
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 20)

        # Even with -10 modifier, natural 20 succeeds
        result = engine.roll_save("pc_throk", "death_ray", modifier=-10)

        assert result.success is True
        assert result.roll == 10  # 20 - 10 modifier
        assert result.modifier == -10
        assert "shrugs off" in result.narrative.lower()

    def test_roll_save_modifier_affects_roll(self, monkeypatch):
        """Modifier is applied to the roll for success calculation."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Level 1 fighter needs 12 for death_ray
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 10
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 10)

        # Without modifier: 10 vs 12 = fail
        result_no_mod = engine.roll_save("pc_throk", "death_ray", modifier=0)
        assert result_no_mod.success is False
        assert result_no_mod.roll == 10

        # With +2 modifier: 10 + 2 = 12 vs 12 = success
        result_with_mod = engine.roll_save("pc_throk", "death_ray", modifier=2)
        assert result_with_mod.success is True
        assert result_with_mod.roll == 12  # 10 + 2
        assert result_with_mod.modifier == 2

    def test_roll_save_invalid_save_type_raises_error(self):
        """ValueError raised for invalid save_type."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Invalid save_type: invalid_type"):
            engine.roll_save("pc_throk", "invalid_type")

    def test_roll_save_invalid_target_raises_error(self):
        """ValueError raised when target not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Target nonexistent not found in combat"):
            engine.roll_save("nonexistent", "death_ray")

    def test_roll_save_no_active_combat_raises_error(self):
        """RuntimeError raised when combat is not active."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot roll save: no active combat"):
            engine.roll_save("pc_throk", "death_ray")

    def test_roll_save_all_save_types_work(self, monkeypatch):
        """All 5 save types are valid and work correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add a level 1 fighter
        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to always succeed (20)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 20)

        save_types = ["death_ray", "wands", "paralysis", "breath", "spells"]

        for save_type in save_types:
            result = engine.roll_save("pc_throk", save_type)

            # All should succeed with natural 20
            assert result.success is True, f"Failed for save_type: {save_type}"
            assert result.roll == 20
            assert isinstance(result.needed, int)
            assert result.needed > 0, f"Invalid target for {save_type}"

    def test_roll_save_death_ray_save_type(self, monkeypatch):
        """Death ray save type works correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 12
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 12)

        result = engine.roll_save("pc_throk", "death_ray")

        assert result.success is True
        assert result.needed == 12  # Level 1 Fighter death_ray

    def test_roll_save_wands_save_type(self, monkeypatch):
        """Wands save type works correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 13
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 13)

        result = engine.roll_save("pc_throk", "wands")

        assert result.success is True
        assert result.needed == 13  # Level 1 Fighter wands

    def test_roll_save_paralysis_save_type(self, monkeypatch):
        """Paralysis save type works correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 14
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 14)

        result = engine.roll_save("pc_throk", "paralysis")

        assert result.success is True
        assert result.needed == 14  # Level 1 Fighter paralysis

    def test_roll_save_breath_save_type(self, monkeypatch):
        """Breath save type works correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 15
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 15)

        result = engine.roll_save("pc_throk", "breath")

        assert result.success is True
        assert result.needed == 15  # Level 1 Fighter breath

    def test_roll_save_spells_save_type(self, monkeypatch):
        """Spells save type works correctly."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 16
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 16)

        result = engine.roll_save("pc_throk", "spells")

        assert result.success is True
        assert result.needed == 16  # Level 1 Fighter spells


class TestRollAbilityCheck:
    """Tests for ability check resolution."""

    def test_roll_ability_check_basic_success(self, monkeypatch):
        """Successful check when roll meets difficulty."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 15 (meets difficulty 15)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 15)

        result = engine.roll_ability_check("pc_throk", "str", difficulty=15)

        assert result.success is True
        assert result.roll == 15
        assert result.needed == 15
        assert result.modifier == 0
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_ability_check_basic_failure(self, monkeypatch):
        """Failed check when roll below difficulty."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 14 (below difficulty 15)
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 14)

        result = engine.roll_ability_check("pc_throk", "dex", difficulty=15)

        assert result.success is False
        assert result.roll == 14
        assert result.needed == 15
        assert result.modifier == 0
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_ability_check_with_modifier(self, monkeypatch):
        """Modifier is applied to the roll."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 12
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 12)

        # Without modifier: 12 vs 15 = fail
        result_no_mod = engine.roll_ability_check("pc_throk", "con", difficulty=15, modifier=0)
        assert result_no_mod.success is False
        assert result_no_mod.roll == 12

        # With +3 modifier: 12 + 3 = 15 vs 15 = success
        result_with_mod = engine.roll_ability_check("pc_throk", "con", difficulty=15, modifier=3)
        assert result_with_mod.success is True
        assert result_with_mod.roll == 15  # 12 + 3
        assert result_with_mod.modifier == 3

    def test_roll_ability_check_natural_1_always_fails(self, monkeypatch):
        """Natural 1 always fails, even with positive modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 1
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 1)

        # Even with +20 modifier, natural 1 fails
        result = engine.roll_ability_check("pc_throk", "int", difficulty=5, modifier=20)

        assert result.success is False
        assert result.roll == 21  # 1 + 20, but still fails
        assert result.modifier == 20
        assert "fumble" in result.narrative.lower() or "fail" in result.narrative.lower()

    def test_roll_ability_check_natural_20_always_succeeds(self, monkeypatch):
        """Natural 20 always succeeds, even with negative modifier."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 20
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 20)

        # Even with -10 modifier, natural 20 succeeds
        result = engine.roll_ability_check("pc_throk", "wis", difficulty=25, modifier=-10)

        assert result.success is True
        assert result.roll == 10  # 20 - 10
        assert result.modifier == -10
        # Check narrative indicates success (flexible match)
        narrative_lower = result.narrative.lower()
        assert "succeed" in narrative_lower or "manages" in narrative_lower or "brilliant" in narrative_lower

    def test_roll_ability_check_all_abilities_valid(self, monkeypatch):
        """All six ability scores are valid."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 15
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 15)

        abilities = ["str", "dex", "con", "int", "wis", "cha"]

        for ability in abilities:
            result = engine.roll_ability_check("pc_throk", ability, difficulty=15)

            assert result.success is True, f"Failed for ability: {ability}"
            assert result.roll == 15
            assert result.needed == 15
            assert isinstance(result.narrative, str)

    def test_roll_ability_check_invalid_ability_raises_error(self):
        """ValueError raised for invalid ability."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Invalid ability: invalid_ability"):
            engine.roll_ability_check("pc_throk", "invalid_ability", difficulty=15)

    def test_roll_ability_check_invalid_target_raises_error(self):
        """ValueError raised when target not found."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        with pytest.raises(ValueError, match="Target nonexistent not found in combat"):
            engine.roll_ability_check("nonexistent", "str", difficulty=15)

    def test_roll_ability_check_no_active_combat_raises_error(self):
        """RuntimeError raised when combat is not active."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot roll ability check: no active combat"):
            engine.roll_ability_check("pc_throk", "str", difficulty=15)

    def test_roll_ability_check_modifier_affects_success(self, monkeypatch):
        """Positive and negative modifiers affect success."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="pc_throk",
            name="Throk",
            hp=10,
            hp_max=10,
            ac=5,
            thac0=19,
            damage_dice="1d8",
            char_class="fighter",
            level=1,
            is_pc=True,
        )

        # Mock d20 roll to 10
        import random
        monkeypatch.setattr(random, "randint", lambda a, b: 10)

        # Base: 10 vs 15 = fail
        result_base = engine.roll_ability_check("pc_throk", "cha", difficulty=15, modifier=0)
        assert result_base.success is False
        assert result_base.roll == 10

        # With +5: 10 + 5 = 15 vs 15 = success
        result_pos = engine.roll_ability_check("pc_throk", "cha", difficulty=15, modifier=5)
        assert result_pos.success is True
        assert result_pos.roll == 15

        # With -3: 10 - 3 = 7 vs 15 = fail
        result_neg = engine.roll_ability_check("pc_throk", "cha", difficulty=15, modifier=-3)
        assert result_neg.success is False
        assert result_neg.roll == 7


class TestRollMorale:
    """Tests for morale check resolution (BECMI rules)."""

    def test_roll_morale_basic_holds(self, monkeypatch):
        """Morale holds when 2d6 roll <= morale score."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add goblin with morale 7 (default)
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
            morale=7,
        )

        # Mock 2d6 roll to 7 (3+4 = 7)
        import random
        rolls = iter([3, 4])  # Two die rolls that sum to 7
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is True
        assert result.roll == 7
        assert result.needed == 7
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_morale_basic_breaks(self, monkeypatch):
        """Morale breaks when 2d6 roll > morale score."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add goblin with morale 7
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
            morale=7,
        )

        # Mock 2d6 roll to 8 (4+4 = 8, one above morale score)
        import random
        rolls = iter([4, 4])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is False
        assert result.roll == 8
        assert result.needed == 7
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 0

    def test_roll_morale_minimum_roll(self, monkeypatch):
        """Minimum 2d6 roll is 2, always holds if morale >= 2."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add goblin with morale 7
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
            morale=7,
        )

        # Mock 2d6 roll to 2 (1+1 = 2, minimum possible)
        import random
        rolls = iter([1, 1])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is True
        assert result.roll == 2
        assert result.needed == 7

    def test_roll_morale_maximum_roll(self, monkeypatch):
        """Maximum 2d6 roll is 12, always breaks if morale < 12."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add goblin with morale 7
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
            morale=7,
        )

        # Mock 2d6 roll to 12 (6+6 = 12, maximum possible)
        import random
        rolls = iter([6, 6])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is False
        assert result.roll == 12
        assert result.needed == 7

    def test_roll_morale_high_morale(self, monkeypatch):
        """High morale (12) holds on roll of 12."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add elite unit with morale 12
        engine.add_combatant(
            id="veteran_01",
            name="Veteran",
            hp=10,
            hp_max=10,
            ac=4,
            thac0=17,
            damage_dice="1d8",
            char_class="fighter",
            level=3,
            morale=12,
        )

        # Mock 2d6 roll to 12 (6+6 = 12, maximum possible)
        import random
        rolls = iter([6, 6])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("veteran_01")

        assert result.holds is True
        assert result.roll == 12
        assert result.needed == 12

    def test_roll_morale_low_morale(self, monkeypatch):
        """Low morale (2) breaks easily."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add cowardly creature with morale 2
        engine.add_combatant(
            id="coward_01",
            name="Coward",
            hp=3,
            hp_max=3,
            ac=8,
            thac0=20,
            damage_dice="1d4",
            char_class="commoner",
            level=1,
            morale=2,
        )

        # Mock 2d6 roll to 3 (2+1 = 3)
        import random
        rolls = iter([2, 1])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("coward_01")

        assert result.holds is False
        assert result.roll == 3
        assert result.needed == 2

    def test_roll_morale_boundary_case(self, monkeypatch):
        """Test exact morale boundary (roll = morale)."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add combatant with morale 9
        engine.add_combatant(
            id="orc_01",
            name="Orc",
            hp=8,
            hp_max=8,
            ac=6,
            thac0=19,
            damage_dice="1d8",
            char_class="orc",
            level=1,
            morale=9,
        )

        # Mock 2d6 roll to exactly 9 (5+4 = 9)
        import random
        rolls = iter([5, 4])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("orc_01")

        assert result.holds is True  # Roll <= morale = holds
        assert result.roll == 9
        assert result.needed == 9

    def test_roll_morale_different_morale_values(self, monkeypatch):
        """Test various morale values."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        # Add multiple combatants with different morale
        morale_values = [7, 8, 9, 10, 11, 12]

        for i, morale in enumerate(morale_values):
            engine.add_combatant(
                id=f"creature_{i:02d}",
                name=f"Creature {i}",
                hp=5,
                hp_max=5,
                ac=6,
                thac0=19,
                damage_dice="1d6",
                char_class="monster",
                level=1,
                morale=morale,
            )

        # Mock 2d6 roll to 8 (4+4 = 8) for each morale check
        import random
        # We need 6 rolls total (2 per check, 3 checks)
        rolls = iter([4, 4, 4, 4, 4, 4])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        # Morale 7: breaks (8 > 7)
        result_7 = engine.roll_morale("creature_00")
        assert result_7.holds is False
        assert result_7.needed == 7

        # Morale 8: holds (8 <= 8)
        result_8 = engine.roll_morale("creature_01")
        assert result_8.holds is True
        assert result_8.needed == 8

        # Morale 9+: holds (8 <= 9+)
        result_9 = engine.roll_morale("creature_02")
        assert result_9.holds is True
        assert result_9.needed == 9

    def test_roll_morale_uses_2d6_not_d20(self):
        """Verify 2d6 is used (roll range 2-12), not d20."""
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
            morale=7,
        )

        # Roll multiple times and verify range is 2-12
        rolls = []
        for _ in range(50):
            result = engine.roll_morale("goblin_01")
            rolls.append(result.roll)

        # All rolls should be in 2d6 range (2-12)
        assert all(2 <= roll <= 12 for roll in rolls), f"Invalid roll found: {rolls}"

        # Should never see values outside 2d6 range
        assert min(rolls) >= 2
        assert max(rolls) <= 12

    def test_roll_morale_no_active_combat_raises_error(self):
        """RuntimeError raised when combat is not active."""
        engine = MechanicsEngine(debug_mode=False)

        with pytest.raises(RuntimeError, match="Cannot roll morale: no active combat"):
            engine.roll_morale("goblin_01")

    def test_roll_morale_invalid_target_raises_error(self):
        """ValueError raised when target not found."""
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
            morale=7,
        )

        with pytest.raises(ValueError, match="Target nonexistent not found in combat"):
            engine.roll_morale("nonexistent")

    def test_roll_morale_narrative_holds(self, monkeypatch):
        """Narrative reflects morale holding."""
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
            morale=7,
        )

        # Mock roll to 5 (2+3 = 5, holds since 5 <= 7)
        import random
        rolls = iter([2, 3])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is True
        # Narrative should indicate holding/fighting/standing firm
        narrative_lower = result.narrative.lower()
        assert any(word in narrative_lower for word in ["hold", "fight", "stand", "resolute", "steady", "firm"])

    def test_roll_morale_narrative_breaks(self, monkeypatch):
        """Narrative reflects morale breaking."""
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
            morale=7,
        )

        # Mock roll to 10 (5+5 = 10, breaks since 10 > 7)
        import random
        rolls = iter([5, 5])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        assert result.holds is False
        # Narrative should indicate breaking/fleeing/running
        narrative_lower = result.narrative.lower()
        assert any(word in narrative_lower for word in ["break", "flee", "run", "retreat", "panic", "rout", "nerve"])

    def test_roll_morale_uses_combatant_name_in_narrative(self, monkeypatch):
        """Narrative includes the combatant's name."""
        engine = MechanicsEngine(debug_mode=False)
        engine.start_combat(style="soft")

        engine.add_combatant(
            id="goblin_01",
            name="Grimfang",
            hp=5,
            hp_max=5,
            ac=6,
            thac0=19,
            damage_dice="1d6",
            char_class="goblin",
            level=1,
            morale=7,
        )

        # Mock roll to 10 (5+5 = 10, breaks since 10 > 7)
        import random
        rolls = iter([5, 5])
        monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))

        result = engine.roll_morale("goblin_01")

        # Narrative should include the name "Grimfang"
        assert "Grimfang" in result.narrative
